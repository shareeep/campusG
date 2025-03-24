from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
from app import db
from app.models.saga_state import CreateOrderSagaState, SagaStatus, SagaStep
from app.services.service_clients import (
    UserServiceClient, OrderServiceClient, PaymentServiceClient,
    EscrowServiceClient, SchedulerServiceClient, NotificationServiceClient
)

saga_bp = Blueprint('saga', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@saga_bp.route('/orders', methods=['POST'])
def create_order():
    """Endpoint to start the create order saga"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    customer_id = data.get('customer_id')
    order_details = data.get('order_details')
    
    if not customer_id:
        return jsonify({'success': False, 'error': 'customer_id is required'}), 400
    if not order_details:
        return jsonify({'success': False, 'error': 'order_details is required'}), 400
    
    # Calculate payment amount
    try:
        payment_amount = calculate_total(order_details)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error calculating total: {str(e)}'}), 400
    
    # Create saga state
    saga_state = CreateOrderSagaState(
        customer_id=customer_id,
        status=SagaStatus.STARTED,
        current_step=SagaStep.GET_USER_DATA,
        order_details=order_details,
        payment_amount=float(payment_amount)
    )
    db.session.add(saga_state)
    db.session.commit()
    
    # Start saga execution
    logger.info(f"Starting create order saga for customer {customer_id}")
    result = execute_saga(saga_state.id)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


def execute_saga(saga_id):
    """Execute the create order saga flow"""
    try:
        saga_state = CreateOrderSagaState.query.get(saga_id)
        if not saga_state:
            return {'success': False, 'error': 'Saga state not found'}
        
        # Step 1: Get user data
        logger.info(f"Saga {saga_id}: Getting user data")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.GET_USER_DATA)
        db.session.commit()
        
        user_client = UserServiceClient()
        user_result = user_client.get_user(saga_state.customer_id)
        
        if not user_result['success']:
            logger.error(f"Saga {saga_id}: Failed to get user data - {user_result['error']}")
            saga_state.update_status(SagaStatus.FAILED, error=user_result['error'])
            db.session.commit()
            return {'success': False, 'error': f"Failed to get user data: {user_result['error']}"}
        
        # Step 2: Create order
        logger.info(f"Saga {saga_id}: Creating order")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.CREATE_ORDER)
        db.session.commit()
        
        order_client = OrderServiceClient()
        order_result = order_client.create_order(saga_state.customer_id, saga_state.order_details)
        
        if not order_result['success']:
            logger.error(f"Saga {saga_id}: Failed to create order - {order_result['error']}")
            saga_state.update_status(SagaStatus.FAILED, error=order_result['error'])
            db.session.commit()
            return {'success': False, 'error': f"Failed to create order: {order_result['error']}"}
        
        # Save order ID
        order_id = order_result['data']['order_id']
        saga_state.order_id = order_id
        db.session.commit()
        
        # Notify about pending payment
        notification_client = NotificationServiceClient()
        notification_client.send_notification(
            'PENDING_PAYMENT',
            saga_state.customer_id,
            {
                'orderId': saga_state.order_id,
                'status': 'pendingPayment'
            }
        )
        
        # Step 3: Authorize payment
        logger.info(f"Saga {saga_id}: Authorizing payment")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.AUTHORIZE_PAYMENT)
        db.session.commit()
        
        payment_client = PaymentServiceClient()
        payment_result = payment_client.authorize_payment(
            saga_state.order_id,
            saga_state.customer_id,
            saga_state.payment_amount
        )
        
        if not payment_result['success']:
            logger.error(f"Saga {saga_id}: Payment authorization failed - {payment_result['error']}")
            # Compensating transaction: update order status to failed
            order_client.update_order_status(saga_state.order_id, 'CANCELLED')
            
            saga_state.update_status(SagaStatus.FAILED, error=payment_result['error'])
            db.session.commit()
            return {'success': False, 'error': f"Payment authorization failed: {payment_result['error']}"}
        
        # Notify about payment authorization
        notification_client.send_notification(
            'PAYMENT_AUTHORIZED',
            saga_state.customer_id,
            {
                'orderId': saga_state.order_id,
                'amount': saga_state.payment_amount
            }
        )
        
        # Step 4: Hold funds in escrow
        logger.info(f"Saga {saga_id}: Holding funds in escrow")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.HOLD_FUNDS)
        db.session.commit()
        
        # Get food and delivery fees from order details
        food_fee = calculate_food_total(saga_state.order_details.get('foodItems', []))
        delivery_fee = calculate_delivery_fee(saga_state.order_details.get('deliveryLocation', ''))
        
        escrow_client = EscrowServiceClient()
        escrow_result = escrow_client.hold_funds(
            saga_state.order_id,
            saga_state.customer_id,
            saga_state.payment_amount,
            float(food_fee),
            float(delivery_fee)
        )
        
        if not escrow_result['success']:
            logger.error(f"Saga {saga_id}: Escrow hold failed - {escrow_result['error']}")
            # Compensating transaction: release payment authorization
            payment_client.release_payment(saga_state.order_id)
            order_client.update_order_status(saga_state.order_id, 'CANCELLED')
            
            saga_state.update_status(SagaStatus.FAILED, error=escrow_result['error'])
            db.session.commit()
            return {'success': False, 'error': f"Failed to hold funds in escrow: {escrow_result['error']}"}
        
        # Notify about escrow placement
        notification_client.send_notification(
            'ESCROW_PLACED',
            saga_state.customer_id,
            {
                'orderId': saga_state.order_id,
                'amount': saga_state.payment_amount
            }
        )
        
        # Step 5: Update order status to created
        logger.info(f"Saga {saga_id}: Updating order status to CREATED")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.UPDATE_ORDER_STATUS)
        db.session.commit()
        
        status_result = order_client.update_order_status(saga_state.order_id, 'CREATED')
        if not status_result['success']:
            logger.error(f"Saga {saga_id}: Failed to update order status - {status_result['error']}")
            # This is not critical - we can still proceed but log the error
            logger.warning(f"Failed to update order status but continuing: {status_result['error']}")
        
        # Notify about order created
        notification_client.send_notification(
            'ORDER_CREATED',
            saga_state.customer_id,
            {
                'orderId': saga_state.order_id,
                'status': 'created'
            }
        )
        
        # Step 6: Start order timeout timer
        logger.info(f"Saga {saga_id}: Starting order timeout timer")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.START_TIMER)
        db.session.commit()
        
        # Schedule an event 30 minutes in the future
        timeout_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        
        scheduler_client = SchedulerServiceClient()
        timer_result = scheduler_client.schedule_timeout(
            saga_state.order_id,
            saga_state.customer_id,
            timeout_at
        )
        
        if not timer_result['success']:
            logger.error(f"Saga {saga_id}: Failed to start timer - {timer_result['error']}")
            # This is not critical - we can still proceed but log the error
            logger.warning(f"Failed to start order timeout timer but continuing: {timer_result['error']}")
        
        # Step 7: Final notification to user
        logger.info(f"Saga {saga_id}: Sending final notification")
        saga_state.update_status(SagaStatus.STARTED, SagaStep.NOTIFY_USER)
        db.session.commit()
        
        notification_client.send_notification(
            'ORDER_READY_FOR_RUNNER',
            saga_state.customer_id,
            {
                'orderId': saga_state.order_id,
                'message': 'Your order is now available for runners to accept.'
            }
        )
        
        # Saga completed successfully
        logger.info(f"Saga {saga_id}: Completed successfully")
        saga_state.update_status(SagaStatus.COMPLETED)
        db.session.commit()
        
        return {
            'success': True,
            'order_id': saga_state.order_id,
            'message': 'Order created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error executing saga {saga_id}: {str(e)}")
        
        try:
            # Attempt to update saga state
            saga_state = CreateOrderSagaState.query.get(saga_id)
            if saga_state:
                saga_state.update_status(SagaStatus.FAILED, error=str(e))
                db.session.commit()
                
                # Attempt to clean up if possible
                if saga_state.order_id:
                    try:
                        OrderServiceClient().update_order_status(saga_state.order_id, 'CANCELLED')
                        PaymentServiceClient().release_payment(saga_state.order_id)
                    except Exception as cleanup_error:
                        logger.error(f"Error during cleanup: {str(cleanup_error)}")
        except Exception as state_error:
            logger.error(f"Error updating saga state: {str(state_error)}")
            
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


@saga_bp.route('/sagas/<saga_id>', methods=['GET'])
def get_saga_state(saga_id):
    """Get the current state of a saga"""
    saga_state = CreateOrderSagaState.query.get(saga_id)
    if not saga_state:
        return jsonify({'success': False, 'error': 'Saga not found'}), 404
    
    return jsonify({
        'id': saga_state.id,
        'customer_id': saga_state.customer_id,
        'order_id': saga_state.order_id,
        'status': saga_state.status.name,
        'current_step': saga_state.current_step.name if saga_state.current_step else None,
        'error': saga_state.error,
        'created_at': saga_state.created_at.isoformat(),
        'updated_at': saga_state.updated_at.isoformat(),
        'completed_at': saga_state.completed_at.isoformat() if saga_state.completed_at else None
    }), 200


@saga_bp.route('/sagas', methods=['GET'])
def list_sagas():
    """List all sagas with optional filtering"""
    status = request.args.get('status')
    
    query = CreateOrderSagaState.query
    
    if status:
        try:
            query = query.filter_by(status=SagaStatus[status])
        except KeyError:
            return jsonify({'success': False, 'error': f'Invalid status: {status}'}), 400
    
    sagas = query.order_by(CreateOrderSagaState.created_at.desc()).limit(100).all()
    
    result = [{
        'id': saga.id,
        'customer_id': saga.customer_id,
        'order_id': saga.order_id,
        'status': saga.status.name,
        'current_step': saga.current_step.name if saga.current_step else None,
        'created_at': saga.created_at.isoformat(),
        'updated_at': saga.updated_at.isoformat()
    } for saga in sagas]
    
    return jsonify(result), 200


def calculate_total(order_details):
    """Calculate the total amount for the order"""
    food_total = calculate_food_total(order_details.get('foodItems', []))
    delivery_fee = calculate_delivery_fee(order_details.get('deliveryLocation', ''))
    return food_total + delivery_fee


def calculate_food_total(food_items):
    """Calculate the food total"""
    total = Decimal('0.00')
    for item in food_items:
        price = Decimal(str(item.get('price', 0)))
        quantity = Decimal(str(item.get('quantity', 0)))
        total += price * quantity
    return total


def calculate_delivery_fee(location):
    """Calculate delivery fee based on location"""
    # In a real implementation, this would use distance or zones
    return Decimal('3.99')

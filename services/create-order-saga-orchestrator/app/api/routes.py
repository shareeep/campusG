from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from decimal import Decimal
import json
import logging
import uuid
from app import db
from app.models.saga_state import CreateOrderSagaState, SagaStatus, SagaStep
# Remove url_prefix to register at root
saga_bp = Blueprint('saga', __name__) 
logger = logging.getLogger(__name__)

# Removed redundant /health route (it's defined in __init__.py)

@saga_bp.route('/orders', methods=['POST'])
def create_order():
    """Endpoint to start the create order saga"""
    # Access services from the current app context
    orchestrator = current_app.orchestrator
    
    if not orchestrator:
        return jsonify({'success': False, 'error': 'Orchestrator service not initialized'}), 500
        
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
    
    # The orchestrator's start_saga method now has internal checks for Kafka
    # and will return appropriate error messages if initialization failed
    try:
        logger.info(f"Starting create order saga for customer {customer_id}")
            
        # Start the saga (will lazy-initialize if needed)
        success, message, saga_state = orchestrator.start_saga(
            customer_id, 
            order_details, 
            payment_amount
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'saga_id': saga_state.id,
                'status': saga_state.status.name
            }), 202  # Accepted, will process asynchronously
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        logger.error(f"Error starting saga: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error starting saga: {str(e)}"
        }), 500



@saga_bp.route('/sagas/<saga_id>', methods=['GET'])
def get_saga_state(saga_id):
    """Get the current state of a saga"""
    saga_state = CreateOrderSagaState.query.get(saga_id)
    if not saga_state:
        return jsonify({'success': False, 'error': 'Saga not found'}), 404
    
    response = {
        'id': saga_state.id,
        'customer_id': saga_state.customer_id,
        'order_id': saga_state.order_id,
        'status': saga_state.status.name,
        'current_step': saga_state.current_step.name if saga_state.current_step else None,
        'error': saga_state.error,
        'created_at': saga_state.created_at.isoformat(),
        'updated_at': saga_state.updated_at.isoformat(),
        'completed_at': saga_state.completed_at.isoformat() if saga_state.completed_at else None
    }
    
    return jsonify(response), 200


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


@saga_bp.route('/sagas/<string:saga_id>/cancel', methods=['POST'])
def cancel_saga(saga_id):
    """
    Endpoint to manually request cancellation of a specific saga.
    """
    logger = current_app.logger
    orchestrator = current_app.orchestrator
    
    if not orchestrator:
        logger.error("Orchestrator not initialized, cannot cancel saga.")
        return jsonify({'error': 'Service unavailable'}), 503

    logger.info(f"Received request to cancel saga {saga_id}")

    try:
        saga_state = CreateOrderSagaState.query.get(saga_id)
        if not saga_state:
            logger.warning(f"Saga {saga_id} not found for cancellation request.")
            return jsonify({'error': 'Saga not found'}), 404

        # Check if saga is in a state where manual cancellation might be attempted.
        # Allow attempts if STARTED, COMPENSATING, or COMPLETED (as the underlying order might still be cancellable).
        # Prevent attempts if already CANCELLING, CANCELLED, FAILED, or COMPENSATED.
        allowed_states_for_attempt = [SagaStatus.STARTED, SagaStatus.COMPENSATING, SagaStatus.COMPLETED]
        if saga_state.status not in allowed_states_for_attempt:
             logger.warning(f"Cannot initiate cancellation for saga {saga_id} in state {saga_state.status.name}")
             # Return 409 Conflict as the saga is in a final or already processing cancellation state.
             return jsonify({'error': f'Saga cannot be cancelled in its current state: {saga_state.status.name}'}), 409

        # Initiate cancellation via the orchestrator's internal method
        # Use a specific reason for manual cancellation
        success = orchestrator._initiate_cancellation(saga_state, reason="Manual cancellation requested by user")

        if success:
            logger.info(f"Cancellation initiated successfully for saga {saga_id}")
            # Return 202 Accepted as cancellation is asynchronous
            return jsonify({'message': 'Saga cancellation initiated'}), 202
        else:
            # _initiate_cancellation logs the specific error
            logger.error(f"Failed to initiate cancellation for saga {saga_id}")
            # Return 500 as it indicates an internal issue during cancellation command publishing
            return jsonify({'error': 'Failed to initiate saga cancellation'}), 500

    except Exception as e:
        logger.error(f"Unexpected error during saga cancellation request for {saga_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def calculate_total(order_details):
    """Calculate the total amount for the order using fees from order_details"""
    food_total = calculate_food_total(order_details.get('foodItems', []))
    # Extract delivery fee directly from order_details
    input_delivery_fee = order_details.get('deliveryFee', None)
    try:
        # Use Decimal for precision, default to 0 if conversion fails or input is None/invalid
        delivery_fee = Decimal(str(input_delivery_fee)) if input_delivery_fee is not None else Decimal('0.00')
    except (TypeError, ValueError):
        logger.warning(f"Invalid deliveryFee '{input_delivery_fee}' in order_details. Defaulting to 0 for total calculation.")
        delivery_fee = Decimal('0.00')
        
    logger.info(f"Calculating total: Food={food_total}, Delivery={delivery_fee}")
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

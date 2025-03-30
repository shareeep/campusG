from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from decimal import Decimal
import json
import logging
import uuid
from app import db
from app.models.saga_state import CreateOrderSagaState, SagaStatus, SagaStep
saga_bp = Blueprint('saga', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

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

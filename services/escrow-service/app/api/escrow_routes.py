from flask import Blueprint, request, jsonify, current_app
import uuid
from decimal import Decimal
from datetime import datetime
from app.models.models import Escrow, EscrowStatus
from app import db
from app.services.kafka_service import kafka_client

api = Blueprint('api', __name__)

@api.route('/escrow/hold', methods=['POST'])
def hold_funds():
    """
    Hold funds in escrow for an order
    
    Request body should contain:
    {
        "orderId": "order-123",
        "customerId": "customer-456",
        "runnerId": "runner-789" (optional, may be null at this stage),
        "amount": 29.99,
        "foodFee": 24.99,
        "deliveryFee": 5.00
    }
    
    This endpoint creates an escrow record and marks funds as held.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['orderId', 'customerId', 'amount', 'foodFee', 'deliveryFee']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f"Missing required field: {field}"}), 400
        
        order_id = data['orderId']
        customer_id = data['customerId']
        runner_id = data.get('runnerId')  # May be null at this stage
        amount = Decimal(str(data['amount']))
        food_fee = Decimal(str(data['foodFee']))
        delivery_fee = Decimal(str(data['deliveryFee']))
        
        # Check if escrow already exists for this order
        existing_escrow = Escrow.query.filter_by(order_id=order_id).first()
        if existing_escrow:
            return jsonify({
                'success': False, 
                'message': f'Escrow already exists for order {order_id} with status {existing_escrow.status.name}'
            }), 400
        
        # Create new escrow record
        escrow = Escrow(
            escrow_id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            runner_id=runner_id,
            amount=amount,
            food_fee=food_fee,
            delivery_fee=delivery_fee,
            status=EscrowStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(escrow)
        db.session.commit()
        
        # In a real implementation, this would interact with a payment system
        # to hold the funds. For now, we'll simulate success.
        
        # Update escrow status to HELD
        escrow.status = EscrowStatus.HELD
        escrow.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Publish escrow event to Kafka
        kafka_client.publish('escrow-events', {
            'type': 'FUNDS_HELD',
            'payload': {
                'escrowId': escrow.escrow_id,
                'orderId': order_id,
                'customerId': customer_id,
                'amount': float(amount)
            }
        })
        
        current_app.logger.info(f"Funds held for order {order_id}: ${amount}")
        
        return jsonify({
            'success': True,
            'message': 'Funds held successfully',
            'escrow': escrow.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error holding funds: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to hold funds: {str(e)}"}), 500

@api.route('/escrow/release', methods=['POST'])
def release_funds():
    """
    Release funds from escrow to the runner
    
    Request body should contain:
    {
        "orderId": "order-123",
        "runnerId": "runner-789" (required for release)
    }
    
    This endpoint releases funds from escrow to the runner upon delivery completion.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        runner_id = data.get('runnerId')
        
        if not order_id or not runner_id:
            return jsonify({'success': False, 'message': 'Missing orderId or runnerId'}), 400
        
        # Find the escrow for this order
        escrow = Escrow.query.filter_by(order_id=order_id).first()
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found for order'}), 404
            
        if escrow.status != EscrowStatus.HELD:
            return jsonify({
                'success': False, 
                'message': f'Cannot release funds in status: {escrow.status.name}'
            }), 400
            
        # Update runner ID if it was null before
        if not escrow.runner_id:
            escrow.runner_id = runner_id
        
        # In a real implementation, this would release funds to the runner through a payment system
        
        # Update escrow status to RELEASED
        escrow.status = EscrowStatus.RELEASED
        escrow.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Publish escrow event to Kafka
        kafka_client.publish('escrow-events', {
            'type': 'FUNDS_RELEASED',
            'payload': {
                'escrowId': escrow.escrow_id,
                'orderId': order_id,
                'customerId': escrow.customer_id,
                'runnerId': runner_id,
                'amount': float(escrow.amount)
            }
        })
        
        current_app.logger.info(f"Funds released for order {order_id} to runner {runner_id}: ${escrow.amount}")
        
        return jsonify({
            'success': True,
            'message': 'Funds released successfully',
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error releasing funds: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to release funds: {str(e)}"}), 500

@api.route('/escrow/refund', methods=['POST'])
def refund_funds():
    """
    Refund funds from escrow back to the customer
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This endpoint refunds funds back to the customer, used in order cancellations.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing orderId'}), 400
        
        # Find the escrow for this order
        escrow = Escrow.query.filter_by(order_id=order_id).first()
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found for order'}), 404
            
        if escrow.status != EscrowStatus.HELD:
            return jsonify({
                'success': False, 
                'message': f'Cannot refund funds in status: {escrow.status.name}'
            }), 400
        
        # In a real implementation, this would refund funds to the customer through a payment system
        
        # Update escrow status to REFUNDED
        escrow.status = EscrowStatus.REFUNDED
        escrow.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Publish escrow event to Kafka
        kafka_client.publish('escrow-events', {
            'type': 'FUNDS_REFUNDED',
            'payload': {
                'escrowId': escrow.escrow_id,
                'orderId': order_id,
                'customerId': escrow.customer_id,
                'amount': float(escrow.amount)
            }
        })
        
        current_app.logger.info(f"Funds refunded for order {order_id} to customer {escrow.customer_id}: ${escrow.amount}")
        
        return jsonify({
            'success': True,
            'message': 'Funds refunded successfully',
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error refunding funds: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to refund funds: {str(e)}"}), 500

@api.route('/escrow/<escrow_id>', methods=['GET'])
def get_escrow(escrow_id):
    """Get a specific escrow by ID"""
    try:
        escrow = Escrow.query.get(escrow_id)
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found'}), 404
            
        return jsonify({
            'success': True,
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting escrow {escrow_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get escrow: {str(e)}"}), 500

@api.route('/escrow/order/<order_id>', methods=['GET'])
def get_escrow_by_order(order_id):
    """Get the escrow for a specific order"""
    try:
        escrow = Escrow.query.filter_by(order_id=order_id).first()
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found for order'}), 404
            
        return jsonify({
            'success': True,
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting escrow for order {order_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get escrow: {str(e)}"}), 500

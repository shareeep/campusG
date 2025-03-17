from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
import requests
from app.models.models import EscrowTransaction, TransactionStatus, TransactionType
from app import db

api = Blueprint('api', __name__)

@api.route('/escrow/hold', methods=['POST'])
async def hold_funds():
    """
    Hold funds in escrow
    
    Request body should contain:
    {
        "orderId": "order-123",
        "customerId": "customer-456",
        "amount": 29.99,
        "foodFee": 24.99,
        "deliveryFee": 5.00
    }
    
    This endpoint will place the specified amount in escrow for the order.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        customer_id = data.get('customerId')
        amount = data.get('amount')
        food_fee = data.get('foodFee')
        delivery_fee = data.get('deliveryFee')
        
        if not order_id or not customer_id or amount is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Check if escrow already exists for this order
        existing_escrow = EscrowTransaction.query.filter_by(
            order_id=order_id,
            transaction_type=TransactionType.HOLD
        ).first()
        
        if existing_escrow:
            return jsonify({
                'success': False, 
                'message': 'Escrow already exists for this order'
            }), 400
            
        # Create a new escrow transaction
        escrow = EscrowTransaction(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            amount=amount,
            food_fee=food_fee or 0,
            delivery_fee=delivery_fee or 0,
            transaction_type=TransactionType.HOLD,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(escrow)
        db.session.commit()
        
        # Update escrow status to HELD
        escrow.status = TransactionStatus.HELD
        escrow.updated_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f"Funds held in escrow for order {order_id}")
        
        return jsonify({
            'success': True,
            'message': 'Funds held in escrow successfully',
            'escrowId': escrow.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error holding funds in escrow: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to hold funds in escrow: {str(e)}"}), 500

@api.route('/escrow/release', methods=['POST'])
async def release_funds():
    """
    Release funds from escrow
    
    Request body should contain:
    {
        "orderId": "order-123",
        "recipientType": "RESTAURANT" | "RUNNER"
    }
    
    This endpoint will release the appropriate portion of the funds from escrow.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        recipient_type = data.get('recipientType')
        
        if not order_id or not recipient_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        if recipient_type not in ['RESTAURANT', 'RUNNER']:
            return jsonify({'success': False, 'message': 'Invalid recipient type'}), 400
            
        # Find the escrow transaction for this order
        escrow = EscrowTransaction.query.filter_by(
            order_id=order_id,
            transaction_type=TransactionType.HOLD,
            status=TransactionStatus.HELD
        ).first()
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found or not in HELD status'}), 404
            
        # Determine the amount to release
        release_amount = escrow.food_fee if recipient_type == 'RESTAURANT' else escrow.delivery_fee
        
        # Create a release transaction
        release = EscrowTransaction(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=escrow.customer_id,
            amount=release_amount,
            food_fee=escrow.food_fee if recipient_type == 'RESTAURANT' else 0,
            delivery_fee=escrow.delivery_fee if recipient_type == 'RUNNER' else 0,
            transaction_type=TransactionType.RELEASE,
            status=TransactionStatus.PENDING,
            recipient_type=recipient_type,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(release)
        db.session.commit()
        
        # Make payment service call to capture funds
        try:
            # In a real implementation, make a call to payment service to capture funds
            # For now, we'll just simulate it
            
            # Update release status to RELEASED
            release.status = TransactionStatus.RELEASED
            release.updated_at = datetime.utcnow()
            db.session.commit()
            
            # If both restaurant and runner have been paid, mark escrow as COMPLETED
            if recipient_type == 'RUNNER':
                restaurant_paid = EscrowTransaction.query.filter_by(
                    order_id=order_id,
                    transaction_type=TransactionType.RELEASE,
                    recipient_type='RESTAURANT',
                    status=TransactionStatus.RELEASED
                ).first()
                
                if restaurant_paid:
                    escrow.status = TransactionStatus.COMPLETED
                    escrow.updated_at = datetime.utcnow()
                    db.session.commit()
            
            elif recipient_type == 'RESTAURANT':
                runner_paid = EscrowTransaction.query.filter_by(
                    order_id=order_id,
                    transaction_type=TransactionType.RELEASE,
                    recipient_type='RUNNER',
                    status=TransactionStatus.RELEASED
                ).first()
                
                if runner_paid:
                    escrow.status = TransactionStatus.COMPLETED
                    escrow.updated_at = datetime.utcnow()
                    db.session.commit()
            
            current_app.logger.info(f"Funds released from escrow for order {order_id} to {recipient_type}")
            
            return jsonify({
                'success': True,
                'message': f'Funds released from escrow successfully to {recipient_type}',
                'releaseId': release.id
            }), 200
            
        except Exception as e:
            release.status = TransactionStatus.FAILED
            release.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.error(f"Error processing payment capture: {str(e)}")
            return jsonify({'success': False, 'message': f"Failed to capture payment: {str(e)}"}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error releasing funds from escrow: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to release funds: {str(e)}"}), 500

@api.route('/escrow/cancel', methods=['POST'])
async def cancel_escrow():
    """
    Cancel escrow hold
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This endpoint will cancel an escrow hold for a given order.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing order ID'}), 400
            
        # Find the escrow transaction for this order
        escrow = EscrowTransaction.query.filter_by(
            order_id=order_id,
            transaction_type=TransactionType.HOLD
        ).first()
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow not found'}), 404
            
        if escrow.status not in [TransactionStatus.PENDING, TransactionStatus.HELD]:
            return jsonify({'success': False, 'message': f"Escrow cannot be cancelled in status: {escrow.status.value}"}), 400
            
        # Update escrow status to CANCELLED
        escrow.status = TransactionStatus.CANCELLED
        escrow.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Make payment service call to release authorization
        try:
            response = requests.post(
                f"{current_app.config['PAYMENT_SERVICE_URL']}/api/payments/release",
                json={'orderId': order_id}
            )
            
            if response.status_code != 200:
                current_app.logger.error(f"Failed to release payment: {response.text}")
                # We continue despite payment release failure
            
            current_app.logger.info(f"Escrow cancelled for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Escrow cancelled successfully'
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error releasing payment: {str(e)}")
            return jsonify({'success': True, 'message': 'Escrow cancelled but payment release failed'}), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling escrow: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to cancel escrow: {str(e)}"}), 500

@api.route('/escrow/<escrow_id>', methods=['GET'])
async def get_escrow(escrow_id):
    """Get a specific escrow transaction by ID"""
    try:
        escrow = EscrowTransaction.query.get(escrow_id)
        
        if not escrow:
            return jsonify({'success': False, 'message': 'Escrow transaction not found'}), 404
            
        return jsonify({
            'success': True,
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting escrow {escrow_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get escrow: {str(e)}"}), 500

@api.route('/escrow', methods=['GET'])
async def get_escrow_transactions():
    """Get escrow transactions with optional filtering by order"""
    try:
        # Query parameters
        order_id = request.args.get('orderId')
        status = request.args.get('status')
        transaction_type = request.args.get('type')
        
        # Build query
        query = EscrowTransaction.query
        
        if order_id:
            query = query.filter_by(order_id=order_id)
            
        if status:
            query = query.filter_by(status=status)
            
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
            
        # Get transactions
        transactions = query.all()
        
        return jsonify({
            'success': True,
            'transactions': [transaction.to_dict() for transaction in transactions]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting escrow transactions: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get transactions: {str(e)}"}), 500

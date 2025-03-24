from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
# Import our stripe placeholder instead of the real stripe package
from app.utils import stripe_placeholder as stripe
from app.models.models import Payment, PaymentStatus
from app import db
from app.services.kafka_service import kafka_client

api = Blueprint('api', __name__)

# We'll configure Stripe in each route instead of at module level
# to avoid the "Working outside of application context" error

@api.route('/payments/authorize', methods=['POST'])
def authorize_payment():
    """
    Authorize a payment with Stripe
    
    Request body should contain:
    {
        "orderId": "order-123",
        "customerId": "customer-456",
        "amount": 29.99
    }
    
    This endpoint will authorize (but not capture) a payment with Stripe.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        customer_id = data.get('customerId')
        amount = data.get('amount')
        
        if not order_id or not customer_id or amount is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Check if there's already a payment for this order
        existing_payment = Payment.query.filter_by(order_id=order_id).first()
        if existing_payment:
            return jsonify({
                'success': False, 
                'message': f'Payment already exists for order {order_id} with status {existing_payment.status.name}'
            }), 400
            
        # Create a new payment record with INITIATING status
        payment = Payment(
            payment_id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            amount=amount,
            status=PaymentStatus.INITIATING
        )
        
        # Save to database
        db.session.add(payment)
        db.session.commit()
        
        # Get customer's payment method from user service
        # In a real implementation, you would call the User Service
        
        try:
            # MOCK IMPLEMENTATION - ACTIVE
            # Simulate a successful authorization
            stripe_payment_id = f"pi_{uuid.uuid4().hex}"
            customer_stripe_card = "mock_card_1234"
            
            """
            # REAL STRIPE IMPLEMENTATION - COMMENTED OUT
            import stripe
            stripe.api_key = current_app.config.get('STRIPE_API_KEY')
            
            # Get customer's payment method from user service
            response = requests.get(
                f"{current_app.config['USER_SERVICE_URL']}/api/users/{customer_id}/payment-info"
            )
            
            if response.status_code != 200:
                payment.status = PaymentStatus.FAILED
                db.session.commit()
                return jsonify({'success': False, 'message': 'Failed to retrieve payment information'}), 400
                
            payment_info = response.json()
            
            # Create payment intent with Stripe
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                payment_method=payment_info.get('payment_method_id'),
                customer=payment_info.get('stripe_customer_id'),
                capture_method='manual',  # Just authorize, don't capture yet
                description=f'Order {order_id}'
            )
            
            stripe_payment_id = payment_intent.id
            customer_stripe_card = payment_info.get('last4', 'unknown')
            """
            
            # Update payment record with successful authorization
            payment.stripe_payment_id = stripe_payment_id
            payment.customer_stripe_card = customer_stripe_card
            payment.status = PaymentStatus.AUTHORIZED
            payment.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Publish payment authorized event
            kafka_client.publish('payment-events', {
                'type': 'PAYMENT_AUTHORIZED',
                'payload': {
                    'orderId': order_id,
                    'customerId': customer_id,
                    'paymentId': payment.payment_id,
                    'amount': float(payment.amount)
                }
            })
            
            current_app.logger.info(f"Payment authorized for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment authorized successfully',
                'paymentId': payment.payment_id,
                'stripePaymentId': stripe_payment_id
            }), 200
            
        except Exception as e:
            # Update payment status to failed
            payment.status = PaymentStatus.FAILED
            db.session.commit()
            
            current_app.logger.error(f"Payment authorization error: {str(e)}")
            
            # Publish payment failed event
            kafka_client.publish('payment-events', {
                'type': 'PAYMENT_FAILED',
                'payload': {
                    'orderId': order_id,
                    'customerId': customer_id,
                    'reason': str(e)
                }
            })
            
            return jsonify({'success': False, 'message': f"Payment authorization failed: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error authorizing payment: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to authorize payment: {str(e)}"}), 500

@api.route('/payments/revert', methods=['POST'])
def revert_payment():
    """
    Revert a previously authorized payment
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This endpoint will cancel a payment authorization.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing order ID'}), 400
            
        # Find the payment for this order
        payment = Payment.query.filter_by(order_id=order_id).first()
        
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
            
        if payment.status != PaymentStatus.AUTHORIZED:
            return jsonify({'success': False, 'message': f"Payment cannot be reverted in status: {payment.status.name}"}), 400
            
        try:
            # MOCK IMPLEMENTATION - ACTIVE
            # Just update the payment status
            
            """
            # REAL STRIPE IMPLEMENTATION - COMMENTED OUT
            import stripe
            stripe.api_key = current_app.config.get('STRIPE_API_KEY')
            
            # Cancel the payment intent with Stripe
            if payment.stripe_payment_id:
                stripe.PaymentIntent.cancel(payment.stripe_payment_id)
            """
            
            # Update payment status
            payment.status = PaymentStatus.FAILED
            payment.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Publish payment reverted event
            kafka_client.publish('payment-events', {
                'type': 'PAYMENT_REVERTED',
                'payload': {
                    'orderId': order_id,
                    'paymentId': payment.payment_id
                }
            })
            
            current_app.logger.info(f"Payment authorization reverted for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment authorization reverted successfully'
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error reverting payment: {str(e)}")
            return jsonify({'success': False, 'message': f"Failed to revert payment: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reverting payment: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to revert payment: {str(e)}"}), 500

@api.route('/payments/move-to-escrow', methods=['POST'])
def move_to_escrow():
    """
    Move a previously authorized payment to escrow
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This endpoint will mark funds as being held in escrow.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing order ID'}), 400
            
        # Find the payment for this order
        payment = Payment.query.filter_by(order_id=order_id).first()
        
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
            
        if payment.status != PaymentStatus.AUTHORIZED:
            return jsonify({'success': False, 'message': f"Payment cannot be moved to escrow in status: {payment.status.name}"}), 400
            
        try:
            # MOCK IMPLEMENTATION - ACTIVE
            # Just update the payment status
            
            """
            # REAL STRIPE IMPLEMENTATION - COMMENTED OUT
            # In a real implementation, this might involve:
            # 1. Capturing the payment with Stripe
            # 2. Moving the funds to a holding account
            import stripe
            stripe.api_key = current_app.config.get('STRIPE_API_KEY')
            
            # Capture the payment intent with Stripe
            if payment.stripe_payment_id:
                stripe.PaymentIntent.capture(payment.stripe_payment_id)
            """
            
            # Update payment status
            payment.status = PaymentStatus.INESCROW
            payment.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Publish payment in escrow event
            kafka_client.publish('payment-events', {
                'type': 'PAYMENT_IN_ESCROW',
                'payload': {
                    'orderId': order_id,
                    'paymentId': payment.payment_id,
                    'amount': float(payment.amount)
                }
            })
            
            current_app.logger.info(f"Payment moved to escrow for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment moved to escrow successfully'
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error moving payment to escrow: {str(e)}")
            return jsonify({'success': False, 'message': f"Failed to move payment to escrow: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error moving payment to escrow: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to move payment to escrow: {str(e)}"}), 500

@api.route('/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    """Get a specific payment by ID"""
    try:
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
            
        return jsonify({
            'success': True,
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment {payment_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get payment: {str(e)}"}), 500

@api.route('/payments', methods=['GET'])
def get_payments():
    """Get payments with optional filtering by order or customer"""
    try:
        # Query parameters
        order_id = request.args.get('orderId')
        customer_id = request.args.get('customerId')
        status = request.args.get('status')
        
        # Build query
        query = Payment.query
        
        if order_id:
            query = query.filter_by(order_id=order_id)
            
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
            
        if status and hasattr(PaymentStatus, status):
            query = query.filter_by(status=getattr(PaymentStatus, status))
            
        # Get payments
        payments = query.all()
        
        return jsonify({
            'success': True,
            'payments': [payment.to_dict() for payment in payments]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting payments: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get payments: {str(e)}"}), 500

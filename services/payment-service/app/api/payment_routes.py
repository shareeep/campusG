from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
import stripe
from app.models.models import Payment, PaymentStatus
from app import db

api = Blueprint('api', __name__)

# Configure Stripe
stripe.api_key = current_app.config.get('STRIPE_API_KEY')

@api.route('/payments/authorize', methods=['POST'])
async def authorize_payment():
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
            
        # Get customer's payment method from database or user service
        # For now, we'll simulate this
        # In a real implementation, you would:
        # 1. Get the customer's stored payment method ID from user service
        # 2. Use that payment method ID with Stripe
        
        try:
            # In production, replace with actual Stripe API call
            # Something like:
            # payment_intent = stripe.PaymentIntent.create(
            #     amount=int(amount * 100),  # Convert to cents
            #     currency='usd',
            #     customer=customer_id,  # Stripe customer ID
            #     payment_method='pm_...',  # Payment method ID
            #     capture_method='manual',  # Just authorize, don't capture yet
            #     description=f'Order {order_id}'
            # )
            
            # For now, simulate a successful authorization
            stripe_payment_intent_id = f"pi_{uuid.uuid4().hex}"
            
            # Create a payment record
            payment = Payment(
                id=str(uuid.uuid4()),
                order_id=order_id,
                customer_id=customer_id,
                amount=amount,
                stripe_payment_intent_id=stripe_payment_intent_id,
                status=PaymentStatus.AUTHORIZED,
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(payment)
            db.session.commit()
            
            current_app.logger.info(f"Payment authorized for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment authorized successfully',
                'paymentId': payment.id,
                'stripePaymentIntentId': stripe_payment_intent_id
            }), 200
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return jsonify({'success': False, 'message': f"Stripe error: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error authorizing payment: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to authorize payment: {str(e)}"}), 500

@api.route('/payments/release', methods=['POST'])
async def release_payment():
    """
    Release a previously authorized payment
    
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
            return jsonify({'success': False, 'message': f"Payment cannot be released in status: {payment.status.name}"}), 400
            
        try:
            # In production, cancel the payment intent with Stripe
            # stripe.PaymentIntent.cancel(payment.stripe_payment_intent_id)
            
            # Update payment status
            payment.status = PaymentStatus.CANCELLED
            payment.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"Payment released for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment authorization released successfully'
            }), 200
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return jsonify({'success': False, 'message': f"Stripe error: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error releasing payment: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to release payment: {str(e)}"}), 500

@api.route('/payments/capture', methods=['POST'])
async def capture_payment():
    """
    Capture a previously authorized payment
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This endpoint will capture funds from a previously authorized payment.
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
            return jsonify({'success': False, 'message': f"Payment cannot be captured in status: {payment.status.name}"}), 400
            
        try:
            # In production, capture the payment intent with Stripe
            # stripe.PaymentIntent.capture(payment.stripe_payment_intent_id)
            
            # Update payment status
            payment.status = PaymentStatus.CAPTURED
            payment.captured_at = datetime.utcnow()
            payment.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"Payment captured for order {order_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment captured successfully'
            }), 200
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return jsonify({'success': False, 'message': f"Stripe error: {str(e)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error capturing payment: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to capture payment: {str(e)}"}), 500

@api.route('/payments/<payment_id>', methods=['GET'])
async def get_payment(payment_id):
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
async def get_payments():
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
            
        if status:
            query = query.filter_by(status=status)
            
        # Get payments
        payments = query.all()
        
        return jsonify({
            'success': True,
            'payments': [payment.to_dict() for payment in payments]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting payments: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get payments: {str(e)}"}), 500

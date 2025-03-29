from flask import Blueprint, request, jsonify, current_app
import stripe
import os
from app import db
from app.models.models import Payment
from sqlalchemy.exc import SQLAlchemyError

webhook = Blueprint('webhook', __name__)

@webhook.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Log the event
        current_app.logger.info(f"Received Stripe event: {event['type']}")
        
        # Handle different webhook events
        if event['type'] == 'payment_intent.succeeded':
            handle_payment_succeeded(event['data']['object'])
            
        elif event['type'] == 'payment_intent.canceled':
            handle_payment_canceled(event['data']['object'])
            
        elif event['type'] == 'payment_intent.payment_failed':
            handle_payment_failed(event['data']['object'])
            
        # Return success to acknowledge receipt
        return '', 200
        
    except (stripe.error.SignatureVerificationError, ValueError) as e:
        current_app.logger.error(f"Invalid signature: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        current_app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def handle_payment_succeeded(payment_intent):
    """Handle successful payment"""
    try:
        # Find the payment record by payment intent ID
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = payment_intent['status']
                db.session.commit()
                current_app.logger.info(f"Updated payment {payment_id} to status {payment_intent['status']}")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error handling payment success: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"Error handling payment success: {str(e)}")

def handle_payment_canceled(payment_intent):
    """Handle canceled payment"""
    try:
        # Find the payment record by payment intent ID
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = payment_intent['status']
                db.session.commit()
                current_app.logger.info(f"Updated payment {payment_id} to status {payment_intent['status']}")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error handling payment cancellation: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"Error handling payment cancellation: {str(e)}")

def handle_payment_failed(payment_intent):
    """Handle failed payment"""
    try:
        # Find the payment record by payment intent ID
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = payment_intent['status']
                error_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
                # You could store the error message in a separate column if needed
                db.session.commit()
                current_app.logger.info(f"Updated payment {payment_id} to failed status. Error: {error_message}")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error handling payment failure: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"Error handling payment failure: {str(e)}")

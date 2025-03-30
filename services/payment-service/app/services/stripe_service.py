import stripe
import os
import uuid
from datetime import datetime, timezone
from app import db
from app.models.models import Payment
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

# Initialize Stripe with API key from config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    @staticmethod
    def create_payment_intent(customer_id, order_id, amount, payment_method_id, description, return_url=None, stripe_customer_id=None):
        """
        Creates and confirms a payment intent with Stripe
        """
        try:
            # Ensure minimum amount is at least 50 cents
            if amount < 50:
                return {
                    "success": False,
                    "error": "invalid_amount",
                    "message": "Amount must be at least 50 cents (SGD 0.50)"
                }
                
            current_app.logger.info(f"Creating payment intent for order {order_id}, amount {amount} cents")
            
            # Create payment intent parameters
            payment_intent_params = {
                'amount': amount,
                'currency': 'sgd',
                'payment_method': payment_method_id,
                'description': description,
                'capture_method': 'manual',  # This enables the escrow functionality
                'confirm': True,
                'return_url': return_url,
                'use_stripe_sdk': True,
                'off_session': False
            }
            
            # Add customer if provided (should be handled by user service)
            if stripe_customer_id:
                payment_intent_params['customer'] = stripe_customer_id
                current_app.logger.info(f"Using existing Stripe customer: {stripe_customer_id}")
            
            # Create and confirm the payment intent
            payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
            current_app.logger.info(f"Payment intent created: {payment_intent.id}, status: {payment_intent.status}")
            
            # Create a record in our database
            payment_id = str(uuid.uuid4())
            payment = Payment(
                payment_id=payment_id,
                payment_intent_id=payment_intent.id,
                order_id=order_id,
                customer_id=customer_id,
                amount=amount / 100.0,  # Convert cents to dollars
                status="INITIATING",
                description=description,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(payment)
            db.session.commit()
            
            # Check if authentication is required
            if payment_intent.status == 'requires_action':
                # Return the client_secret and next_action for the frontend to handle
                return {
                    "success": True,
                    "requires_action": True,
                    "payment_id": payment_id,
                    "payment_intent_id": payment_intent.id,
                    "client_secret": payment_intent.client_secret,
                    "next_action": payment_intent.next_action
                }
            elif payment_intent.status == 'requires_capture':
                # Payment succeeded and is ready for capture (escrow)
                payment.status = "AUTHORIZED"
                db.session.commit()
                
                return {
                    "success": True,
                    "requires_action": False,
                    "payment_id": payment_id,
                    "payment_intent_id": payment_intent.id,
                    "status": "AUTHORIZED"
                }
            else:
                # Other status (likely an error)
                return {
                    "success": False,
                    "error": "payment_failed",
                    "message": f"Payment failed with status: {payment_intent.status}"
                }
                    
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error creating payment intent: {str(e)}")
            return {
                "success": False,
                "error": "stripe_error",
                "message": str(e)
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error creating payment intent: {str(e)}")
            return {
                "success": False,
                "error": "server_error",
                "message": str(e)
            }
    
    @staticmethod
    def release_funds(payment_id, runner_id):
        """
        Release funds from escrow to complete the payment
        """
        try:
            # Find the payment record
            payment = Payment.query.get(payment_id)
            if not payment:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": "Payment record not found"
                }
            
            # Verify payment is in correct state
            payment_intent = stripe.PaymentIntent.retrieve(payment.payment_intent_id)
            if payment_intent.status != "requires_capture":
                return {
                    "success": False,
                    "error": "invalid_state",
                    "message": f"Payment cannot be captured in state: {payment_intent.status}"
                }
            
            # Capture the payment to release funds
            captured_intent = stripe.PaymentIntent.capture(payment.payment_intent_id)
            
            # Update our record
            payment.status = captured_intent.status
            payment.runner_id = runner_id
            payment.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {
                "success": True,
                "payment_id": payment_id,
                "status": captured_intent.status
            }
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return {
                "success": False,
                "error": "stripe_error",
                "message": str(e)
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {str(e)}")
            return {
                "success": False,
                "error": "database_error",
                "message": "Failed to update payment record"
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": str(e)
            }
    
    @staticmethod
    def revert_payment(payment_id, reason=None):
        """
        Cancel a payment or issue a refund
        """
        try:
            # Find the payment record
            payment = Payment.query.get(payment_id)
            if not payment:
                return {
                    "success": False,
                    "error": "not_found",
                    "message": "Payment record not found"
                }
            
            # Get current state from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(payment.payment_intent_id)
            
            # Handle based on current status
            if payment_intent.status == "requires_capture":
                # Cancel the payment intent (no money moved)
                canceled_intent = stripe.PaymentIntent.cancel(
                    payment.payment_intent_id,
                    cancellation_reason=reason or "requested_by_customer"
                )
                payment.status = canceled_intent.status
                
            elif payment_intent.status == "succeeded":
                # Create a refund
                refund = stripe.Refund.create(
                    payment_intent=payment.payment_intent_id,
                    reason=reason or "requested_by_customer"
                )
                payment.status = "refunded"
                
            else:
                return {
                    "success": False,
                    "error": "invalid_state",
                    "message": f"Payment cannot be reverted in state: {payment_intent.status}"
                }
            
            # Update our record
            payment.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {
                "success": True,
                "payment_id": payment_id,
                "status": payment.status
            }
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return {
                "success": False,
                "error": "stripe_error",
                "message": str(e)
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {str(e)}")
            return {
                "success": False,
                "error": "database_error",
                "message": "Failed to update payment record"
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": str(e)
            }
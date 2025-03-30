import stripe
import os
import uuid
from datetime import datetime
from app import db
from app.models.models import Payment
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

# Initialize Stripe with API key from config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    @staticmethod
    def create_payment_intent(customer_id, order_id, amount, payment_method_id, description=None):
        """
        Create a payment intent with manual capture for escrow functionality
        """
        try:
            # Generate a unique ID for tracking this payment
            payment_id = f"payment_{uuid.uuid4()}"
            
            # Create payment intent in Stripe
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="usd",
                payment_method=payment_method_id,
                capture_method="manual",  # This enables the escrow functionality
                confirm=True,  # Confirm immediately
                description=description or f"Order {order_id}",
                metadata={
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "payment_id": payment_id
                }
            )
            
            # Create a record in our database
            payment = Payment(
                id=payment_id,
                payment_intent_id=payment_intent.id,
                order_id=order_id,
                customer_id=customer_id,
                amount=amount,
                status=payment_intent.status,
                description=description or f"Order {order_id}"
            )
            
            db.session.add(payment)
            db.session.commit()
            
            return {
                "success": True,
                "payment_id": payment_id,
                "payment_intent_id": payment_intent.id,
                "status": payment_intent.status
            }
            
        except stripe.error.CardError as e:
            current_app.logger.error(f"Card error: {str(e)}")
            return {
                "success": False,
                "error": "card_error",
                "message": e.error.message
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
                "message": "Failed to record payment"
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": "unexpected_error",
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
            captured_intent = stripe.PaymentIntent.capture(
                payment.payment_intent_id,
                metadata={
                    "runner_id": runner_id,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
            # Update our record
            payment.status = captured_intent.status
            payment.runner_id = runner_id
            payment.updated_at = datetime.utcnow()
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
            payment.updated_at = datetime.utcnow()
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

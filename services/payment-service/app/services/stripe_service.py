import logging
import os
import uuid
from datetime import datetime, timezone

import stripe
from app import db
from app.models.models import Payment, PaymentStatus
from app.services.kafka_service import (kafka_client,
                                        publish_payment_authorized_event,
                                        publish_payment_failed_event)
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Initialize Stripe with API key from config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe.api_key:
    logger.error("STRIPE_SECRET_KEY environment variable not set!")

# --- Kafka Command Handler ---

def handle_authorize_payment_command(correlation_id, payload):
    """
    Handles the 'authorize_payment' command received from Kafka.
    Attempts to create and confirm a Stripe Payment Intent.
    Publishes 'payment.authorized' or 'payment.failed' event back to Kafka.
    """
    logger.info(f"Handling authorize_payment command for correlation_id: {correlation_id}")
    global kafka_client # Use the global Kafka client instance

    # --- 1. Extract data from payload ---
    try:
        order_id = payload.get('order_id')
        # Use clerk_user_id from payload as our internal customer_id
        customer_id = payload.get('customer', {}).get('clerkUserId')
        stripe_customer_id = payload.get('customer', {}).get('stripeCustomerId')
        # Assuming payment_info contains payment_method_id under userStripeCard
        payment_method_id = payload.get('customer', {}).get('userStripeCard', {}).get('payment_method_id')
        # Amount is expected in cents from saga orchestrator/frontend
        amount_cents = payload.get('order', {}).get('amount')
        description = payload.get('order', {}).get('description', f"Payment for order {order_id}")
        return_url = payload.get('return_url') # Optional, for 3DS redirects

        # --- Validation ---
        if not all([order_id, customer_id, stripe_customer_id, payment_method_id, amount_cents]):
            error_msg = "Missing required fields in authorize_payment command payload"
            logger.error(f"{error_msg} for correlation_id: {correlation_id}. Payload: {payload}")
            publish_payment_failed_event(kafka_client, correlation_id, {'error': 'INVALID_PAYLOAD', 'message': error_msg})
            return

        if not isinstance(amount_cents, int) or amount_cents < 50: # Stripe minimum is typically 50 cents
             error_msg = f"Invalid amount: {amount_cents}. Must be an integer >= 50 cents."
             logger.error(f"{error_msg} for correlation_id: {correlation_id}")
             publish_payment_failed_event(kafka_client, correlation_id, {'error': 'INVALID_AMOUNT', 'message': error_msg})
             return

    except Exception as e:
        error_msg = f"Error parsing authorize_payment payload: {str(e)}"
        logger.error(f"{error_msg} for correlation_id: {correlation_id}. Payload: {payload}", exc_info=True)
        publish_payment_failed_event(kafka_client, correlation_id, {'error': 'PAYLOAD_PARSE_ERROR', 'message': error_msg})
        return

    # --- 2. Create/Update Payment Record in DB ---
    payment = None
    try:
        # Check if a payment record already exists for this order_id (e.g., retry scenario)
        payment = Payment.query.filter_by(order_id=order_id).first()
        payment_id = None

        if payment:
            logger.warning(f"Existing payment record found for order_id {order_id}. Updating status to INITIATING.")
            payment.status = PaymentStatus.INITIATING
            payment.customer_id = customer_id # Update just in case
            payment.amount = amount_cents / 100.0
            payment.description = description
            payment.updated_at = datetime.now(timezone.utc)
            payment_id = payment.payment_id # Use existing ID
        else:
            payment_id = str(uuid.uuid4())
            payment = Payment(
                payment_id=payment_id,
                order_id=order_id,
                customer_id=customer_id, # Using clerk_user_id
                amount=amount_cents / 100.0, # Store as dollars/euros etc.
                status=PaymentStatus.INITIATING,
                description=description,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
                # payment_intent_id will be added after successful Stripe call
            )
            db.session.add(payment)

        db.session.commit()
        logger.info(f"Payment record {payment_id} created/updated for order {order_id}, status: INITIATING")

    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = f"Database error preparing payment record for order {order_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        publish_payment_failed_event(kafka_client, correlation_id, {'error': 'DATABASE_ERROR', 'message': error_msg})
        return
    except Exception as e: # Catch broader exceptions during DB interaction
        db.session.rollback()
        error_msg = f"Unexpected error preparing payment record for order {order_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        publish_payment_failed_event(kafka_client, correlation_id, {'error': 'DB_UNEXPECTED_ERROR', 'message': error_msg})
        return


    # --- 3. Interact with Stripe API ---
    try:
        logger.info(f"Attempting to create Stripe PaymentIntent for order {order_id}, amount {amount_cents} cents, customer {stripe_customer_id}")
        payment_intent_params = {
            'amount': amount_cents,
            'currency': 'sgd', # Assuming SGD, make configurable if needed
            'payment_method': payment_method_id,
            'customer': stripe_customer_id, # Use the Stripe Customer ID
            'description': description,
            'capture_method': 'manual', # For escrow
            'confirm': True, # Attempt to confirm immediately
            'metadata': { # Add useful metadata
                'order_id': order_id,
                'customer_id': customer_id, # Internal customer ID (clerk)
                'correlation_id': correlation_id,
                'payment_record_id': payment.payment_id
            },
            # Explicitly disable redirect-based payment methods for this call
            'automatic_payment_methods': {'enabled': True, 'allow_redirects': 'never'}
        }
        # Add return_url only if provided, needed for 3DS redirects
        # Note: return_url is not needed if allow_redirects is 'never'
        # if return_url:
        #     payment_intent_params['return_url'] = return_url
            # 'off_session': False, # Default is false, means customer is present
            # 'use_stripe_sdk': True, # Needed if frontend uses stripe.handleCardAction

        payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
        logger.info(f"Stripe PaymentIntent {payment_intent.id} created for order {order_id}, status: {payment_intent.status}")

        # --- 4. Update DB with Stripe Intent ID ---
        try:
            payment.payment_intent_id = payment_intent.id
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            # Log error, but proceed to handle Stripe status; PI was created.
            logger.error(f"Database error updating payment_intent_id for payment {payment.payment_id}: {str(e)}", exc_info=True)
            # Consider how to handle this inconsistency - maybe a retry mechanism later


        # --- 5. Handle Stripe Response and Publish Kafka Event ---
        if payment_intent.status == 'requires_capture':
            # Successfully authorized, ready for manual capture (escrow)
            update_payment_status(payment.payment_id, PaymentStatus.AUTHORIZED)
            logger.info(f"Payment {payment.payment_id} authorized (requires capture) for order {order_id}.")
            publish_payment_authorized_event(
                kafka_client,
                correlation_id,
                {
                    'payment_id': payment.payment_id,
                    'order_id': order_id,
                    'payment_intent_id': payment_intent.id,
                    'status': PaymentStatus.AUTHORIZED.value # Send enum value
                }
            )
        elif payment_intent.status == 'requires_action':
            # Requires customer action (e.g., 3DS) - Frontend needs client_secret
            # The saga currently waits for 'payment.authorized' or 'payment.failed'.
            # It doesn't handle 'requires_action' directly. The webhook will eventually send 'succeeded' or 'failed'.
            # We update our internal status but don't send a Kafka event *yet*.
            update_payment_status(payment.payment_id, PaymentStatus.REQUIRES_ACTION)
            logger.info(f"Payment {payment.payment_id} requires action for order {order_id}. Client secret: {payment_intent.client_secret}")
            # NOTE: No Kafka event published here. Success/failure comes via webhook.

        elif payment_intent.status == 'succeeded':
             # This can happen if capture_method wasn't 'manual' or for certain payment methods.
             # Treat as authorized for the saga.
             update_payment_status(payment.payment_id, PaymentStatus.SUCCEEDED) # Or maybe AUTHORIZED? Let's use SUCCEEDED for clarity.
             logger.warning(f"PaymentIntent {payment_intent.id} succeeded immediately (status: {payment_intent.status}). Publishing payment.authorized.")
             publish_payment_authorized_event(
                 kafka_client,
                 correlation_id,
                 {
                     'payment_id': payment.payment_id,
                     'order_id': order_id,
                     'payment_intent_id': payment_intent.id,
                     'status': PaymentStatus.SUCCEEDED.value # Send enum value
                 }
             )
        else:
            # Any other status is considered a failure for the saga flow
            error_msg = f"PaymentIntent creation resulted in unexpected status: {payment_intent.status}"
            logger.error(f"{error_msg} for payment {payment.payment_id}, order {order_id}.")
            update_payment_status(payment.payment_id, PaymentStatus.FAILED)
            publish_payment_failed_event(
                kafka_client,
                correlation_id,
                {'error': 'STRIPE_UNEXPECTED_STATUS', 'message': error_msg, 'stripe_status': payment_intent.status}
            )

    except stripe.error.CardError as e:
        # Specific card error (e.g., insufficient funds, expired)
        body = e.json_body
        err = body.get('error', {})
        error_msg = f"Stripe Card Error: {e.user_message}"
        logger.error(f"{error_msg} for order {order_id}. Code: {e.code}, Param: {e.param}", exc_info=True)
        update_payment_status(payment.payment_id, PaymentStatus.FAILED)
        publish_payment_failed_event(
            kafka_client,
            correlation_id,
            {'error': 'STRIPE_CARD_ERROR', 'message': error_msg, 'stripe_code': e.code}
        )
    except stripe.error.StripeError as e:
        # Other Stripe API errors (network, invalid request etc.)
        error_msg = f"Stripe API Error: {str(e)}"
        logger.error(f"{error_msg} for order {order_id}", exc_info=True)
        # Attempt to update status, might fail if payment is None due to earlier DB error
        if payment: update_payment_status(payment.payment_id, PaymentStatus.FAILED)
        publish_payment_failed_event(
            kafka_client,
            correlation_id,
            {'error': 'STRIPE_API_ERROR', 'message': error_msg}
        )
    except Exception as e:
        # Catch-all for unexpected errors during Stripe interaction or Kafka publishing
        error_msg = f"Unexpected error processing payment authorization for order {order_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if payment: update_payment_status(payment.payment_id, PaymentStatus.FAILED)
        # Try to publish failure event, might fail if Kafka is down
        try:
            publish_payment_failed_event(
                kafka_client,
                correlation_id,
                {'error': 'UNEXPECTED_PROCESSING_ERROR', 'message': error_msg}
            )
        except Exception as kafka_err:
            logger.error(f"Failed to publish payment failure event after processing error: {kafka_err}", exc_info=True)


# --- Helper Functions for DB Updates (e.g., called by webhook handler) ---

def update_payment_status(payment_id, new_status: PaymentStatus, payment_intent_id=None):
    """Updates the status of a payment record in the database."""
    if not isinstance(new_status, PaymentStatus):
        logger.error(f"Invalid status type provided to update_payment_status: {type(new_status)}")
        return False

    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            logger.error(f"Payment record {payment_id} not found for status update.")
            return False

        payment.status = new_status
        payment.updated_at = datetime.now(timezone.utc)
        # Optionally update intent ID if provided (e.g., if initial creation failed before saving it)
        if payment_intent_id and not payment.payment_intent_id:
             payment.payment_intent_id = payment_intent_id

        db.session.commit()
        logger.info(f"Payment record {payment_id} status updated to {new_status.value}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating status for payment {payment_id}: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error updating status for payment {payment_id}: {str(e)}", exc_info=True)
        return False


# --- Potentially useful internal methods (Not directly called by API/Kafka command) ---
# These might be triggered by webhooks or future internal logic

class StripeService:
    # Keep these static methods for now, they might be useful for webhook logic
    # or future direct interactions if needed. Refactor if they become unused.

    @staticmethod
    def capture_payment(payment_id):
        """Captures a previously authorized payment (called when order completes)."""
        logger.info(f"Attempting to capture payment {payment_id}")
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                logger.error(f"Payment {payment_id} not found for capture.")
                return {"success": False, "error": "not_found"}
            if not payment.payment_intent_id:
                 logger.error(f"Payment {payment_id} has no payment_intent_id for capture.")
                 return {"success": False, "error": "missing_intent_id"}

            # Check local status first
            if payment.status != PaymentStatus.AUTHORIZED:
                 logger.warning(f"Attempting to capture payment {payment_id} not in AUTHORIZED state (state: {payment.status.value}). Proceeding with Stripe capture check.")
                 # Allow proceeding, Stripe will enforce its state

            # Capture the payment via Stripe
            captured_intent = stripe.PaymentIntent.capture(payment.payment_intent_id)
            logger.info(f"Stripe capture successful for PaymentIntent {payment.payment_intent_id}, status: {captured_intent.status}")

            # Update local status based on Stripe's response
            new_status = PaymentStatus.SUCCEEDED if captured_intent.status == 'succeeded' else PaymentStatus.FAILED # Or map other statuses
            update_payment_status(payment.payment_id, new_status)

            return {"success": True, "status": new_status.value, "stripe_status": captured_intent.status}

        except stripe.error.StripeError as e:
            error_msg = f"Stripe error capturing payment {payment_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Update local status to FAILED? Depends on business logic for capture failures.
            update_payment_status(payment.payment_id, PaymentStatus.FAILED)
            return {"success": False, "error": "stripe_error", "message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error capturing payment {payment_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            update_payment_status(payment.payment_id, PaymentStatus.FAILED)
            return {"success": False, "error": "unexpected_error", "message": error_msg}


    @staticmethod
    def cancel_or_refund_payment(payment_id, reason="requested_by_customer"):
        """Cancels an authorized payment or refunds a captured/succeeded one."""
        logger.info(f"Attempting to cancel/refund payment {payment_id}")
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                logger.error(f"Payment {payment_id} not found for cancel/refund.")
                return {"success": False, "error": "not_found"}
            if not payment.payment_intent_id:
                 logger.error(f"Payment {payment_id} has no payment_intent_id for cancel/refund.")
                 return {"success": False, "error": "missing_intent_id"}

            # Get current state from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(payment.payment_intent_id)
            final_status = None
            stripe_status = payment_intent.status

            if stripe_status == "requires_capture":
                logger.info(f"Canceling PaymentIntent {payment.payment_intent_id} (status: {stripe_status})")
                canceled_intent = stripe.PaymentIntent.cancel(
                    payment.payment_intent_id,
                    cancellation_reason=reason
                )
                final_status = PaymentStatus.REVERTED # Or CANCELED
                stripe_status = canceled_intent.status
            elif stripe_status == "succeeded":
                logger.info(f"Refunding PaymentIntent {payment.payment_intent_id} (status: {stripe_status})")
                refund = stripe.Refund.create(
                    payment_intent=payment.payment_intent_id,
                    reason=reason
                )
                logger.info(f"Refund {refund.id} created for PaymentIntent {payment.payment_intent_id}, status: {refund.status}")
                final_status = PaymentStatus.REVERTED # Or REFUNDED
                # Stripe status remains 'succeeded', but we track locally as reverted/refunded
            elif stripe_status == "canceled":
                 logger.warning(f"PaymentIntent {payment.payment_intent_id} is already canceled.")
                 final_status = PaymentStatus.REVERTED
            else:
                error_msg = f"PaymentIntent {payment.payment_intent_id} cannot be canceled/refunded in state: {stripe_status}"
                logger.error(error_msg)
                return {"success": False, "error": "invalid_state", "message": error_msg}

            # Update local status
            if final_status:
                update_payment_status(payment.payment_id, final_status)

            return {"success": True, "status": final_status.value if final_status else None, "stripe_status": stripe_status}

        except stripe.error.StripeError as e:
            error_msg = f"Stripe error canceling/refunding payment {payment_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Don't change local status on Stripe error during cancel/refund? Or set to FAILED?
            # update_payment_status(payment.payment_id, PaymentStatus.FAILED) # Maybe too aggressive
            return {"success": False, "error": "stripe_error", "message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error canceling/refunding payment {payment_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # update_payment_status(payment.payment_id, PaymentStatus.FAILED)
            return {"success": False, "error": "unexpected_error", "message": error_msg}

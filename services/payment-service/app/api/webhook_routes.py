import logging
import os

import stripe
from app import db
from app.models.models import Payment, PaymentStatus
# Import helper functions and Kafka client/publishers
from app.services.kafka_service import (kafka_client,
                                        publish_payment_authorized_event,
                                        publish_payment_failed_event)
from app.services.stripe_service import update_payment_status
from flask import Blueprint, jsonify, request, current_app
from flasgger import swag_from # Import swag_from
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
webhook = Blueprint('webhook', __name__)

# Load webhook secret from environment variables
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
if not STRIPE_WEBHOOK_SECRET:
    logger.error("STRIPE_WEBHOOK_SECRET environment variable not set!")

@webhook.route('/stripe-webhook', methods=['POST'])
@swag_from({
    'tags': ['Webhooks'],
    'summary': 'Handle incoming Stripe webhook events.',
    'description': 'Receives events from Stripe, verifies the signature, processes payment_intent events (succeeded, canceled, failed), updates local DB status, and publishes Kafka events (payment.authorized, payment.failed).',
    'consumes': ['application/json'], # Stripe sends JSON
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'Stripe-Signature',
            'in': 'header',
            'required': True,
            'type': 'string',
            'description': 'Stripe webhook signature for verification.'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'description': 'Raw Stripe event payload (JSON).',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string', 'example': 'evt_...'},
                    'type': {'type': 'string', 'example': 'payment_intent.succeeded'},
                    'data': {'type': 'object'},
                    # ... other Stripe event fields
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Webhook received and acknowledged.',
            'schema': {
                'type': 'object',
                'properties': {'received': {'type': 'boolean', 'example': True}}
            }
        },
        '400': {'description': 'Bad Request (e.g., invalid payload, invalid signature)'},
        '500': {'description': 'Internal Server Error (e.g., webhook secret not configured, processing error)'}
    }
})
def stripe_webhook_handler():
    # Check if webhook secret is configured
    if not STRIPE_WEBHOOK_SECRET:
        logger.critical("Webhook processing failed: STRIPE_WEBHOOK_SECRET not configured.")
        return jsonify({"error": "Webhook secret not configured"}), 500

    payload = request.data # Use request.data for raw bytes
    sig_header = request.headers.get('Stripe-Signature')

    if not payload or not sig_header:
        logger.warning("Webhook request missing payload or signature header.")
        return jsonify({"error": "Invalid request"}), 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Received verified Stripe event: ID={event.id}, Type={event.type}")

    except ValueError as e:
        # Invalid payload
        logger.error(f"Webhook error: Invalid payload. {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Webhook error: Invalid signature. {str(e)}", exc_info=True)
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        logger.error(f"Webhook error during event construction: {str(e)}", exc_info=True)
        return jsonify({"error": "Webhook construction error"}), 500

    # --- Handle specific PaymentIntent events ---
    event_object = event.data.object # The actual object like payment_intent
    event_type = event.type

    if event_type == 'payment_intent.succeeded':
        handle_payment_succeeded(event_object)
    elif event_type == 'payment_intent.canceled':
        handle_payment_canceled(event_object)
    elif event_type == 'payment_intent.payment_failed':
        handle_payment_failed(event_object)
    elif event_type == 'payment_intent.requires_action':
        # Usually handled by the initial API call, but log if received via webhook
        logger.info(f"Received '{event_type}' webhook for PI: {event_object.id}. Status already updated during creation.")
    elif event_type == 'payment_intent.processing':
        logger.info(f"Received '{event_type}' webhook for PI: {event_object.id}. Payment is processing.")
        # Optionally update local status to PROCESSING if needed
    else:
        logger.debug(f"Unhandled Stripe event type: {event_type}")

    # Acknowledge receipt to Stripe
    return jsonify({"received": True}), 200


def handle_payment_succeeded(payment_intent):
    """
    Handles the 'payment_intent.succeeded' event.
    Updates local status and publishes 'payment.authorized' if needed.
    This event signifies the payment was successful (either immediately or after user action).
    If capture_method was 'manual', the status will be 'requires_capture' initially.
    This handler primarily confirms success after 'requires_action' or if capture was automatic.
    """
    pi_id = payment_intent.id
    metadata = payment_intent.get('metadata', {})
    payment_record_id = metadata.get('payment_record_id')
    correlation_id = metadata.get('correlation_id') # Get correlation ID for Kafka event

    if not payment_record_id:
        logger.warning(f"Webhook 'payment_intent.succeeded' received for PI {pi_id} without 'payment_record_id' in metadata.")
        return
    if not correlation_id:
         logger.warning(f"Webhook 'payment_intent.succeeded' received for PI {pi_id} without 'correlation_id' in metadata.")
         # Proceed with DB update, but cannot notify saga

    logger.info(f"Processing 'payment_intent.succeeded' for Payment {payment_record_id} (PI: {pi_id})")

    # Check current status in DB to avoid redundant updates/events
    payment = Payment.query.get(payment_record_id)
    if not payment:
        logger.error(f"Payment record {payment_record_id} not found for succeeded PI {pi_id}.")
        return

    current_status = payment.status

    # Determine the correct final status based on Stripe's status
    # If PI succeeded, it means funds are secured. For manual capture, it's ready.
    # If capture was automatic, it's fully succeeded.
    new_status = PaymentStatus.AUTHORIZED if payment_intent.status == 'requires_capture' else PaymentStatus.SUCCEEDED

    # Update local DB status
    if not update_payment_status(payment_record_id, new_status, pi_id):
        logger.error(f"Failed to update DB status to {new_status.value} for Payment {payment_record_id} after PI {pi_id} succeeded.")
        # Decide if we should still attempt to publish Kafka event - maybe not if DB failed.
        return

    # Publish Kafka event ONLY if the status changed meaningfully for the saga
    # e.g., if it was previously REQUIRES_ACTION or INITIATING
    if current_status in [PaymentStatus.INITIATING, PaymentStatus.REQUIRES_ACTION]:
        if correlation_id:
            logger.info(f"Publishing payment.authorized event for Payment {payment_record_id} (Correlation ID: {correlation_id})")
            publish_payment_authorized_event(
                kafka_client,
                correlation_id,
                {
                    'payment_id': payment_record_id,
                    'order_id': payment.order_id,
                    'payment_intent_id': pi_id,
                    'status': new_status.value # AUTHORIZED or SUCCEEDED
                }
            )
        else:
             logger.warning(f"Cannot publish payment.authorized event for Payment {payment_record_id}: Missing correlation_id.")
    else:
        logger.info(f"Payment {payment_record_id} already in status {current_status.value}. No Kafka event needed for PI success.")


def handle_payment_canceled(payment_intent):
    """
    Handles the 'payment_intent.canceled' event.
    Updates local status to REVERTED and publishes 'payment.failed'.
    """
    pi_id = payment_intent.id
    metadata = payment_intent.get('metadata', {})
    payment_record_id = metadata.get('payment_record_id')
    correlation_id = metadata.get('correlation_id')

    if not payment_record_id:
        logger.warning(f"Webhook 'payment_intent.canceled' received for PI {pi_id} without 'payment_record_id' in metadata.")
        return
    if not correlation_id:
         logger.warning(f"Webhook 'payment_intent.canceled' received for PI {pi_id} without 'correlation_id' in metadata.")

    logger.info(f"Processing 'payment_intent.canceled' for Payment {payment_record_id} (PI: {pi_id})")

    payment = Payment.query.get(payment_record_id)
    if not payment:
        logger.error(f"Payment record {payment_record_id} not found for canceled PI {pi_id}.")
        return

    current_status = payment.status
    new_status = PaymentStatus.REVERTED # Map Stripe 'canceled' to our 'REVERTED'

    if not update_payment_status(payment_record_id, new_status, pi_id):
        logger.error(f"Failed to update DB status to {new_status.value} for Payment {payment_record_id} after PI {pi_id} canceled.")
        return

    # Publish Kafka event if status changed meaningfully
    if current_status not in [PaymentStatus.REVERTED, PaymentStatus.FAILED]:
        if correlation_id:
            logger.info(f"Publishing payment.failed event for canceled Payment {payment_record_id} (Correlation ID: {correlation_id})")
            publish_payment_failed_event(
                kafka_client,
                correlation_id,
                {
                    'error': 'STRIPE_PAYMENT_CANCELED',
                    'message': f'Stripe PaymentIntent {pi_id} was canceled.',
                    'payment_id': payment_record_id,
                    'order_id': payment.order_id,
                }
            )
        else:
             logger.warning(f"Cannot publish payment.failed event for canceled Payment {payment_record_id}: Missing correlation_id.")
    else:
        logger.info(f"Payment {payment_record_id} already in status {current_status.value}. No Kafka event needed for PI cancel.")


def handle_payment_failed(payment_intent):
    """
    Handles the 'payment_intent.payment_failed' event.
    Updates local status to FAILED and publishes 'payment.failed'.
    """
    pi_id = payment_intent.id
    metadata = payment_intent.get('metadata', {})
    payment_record_id = metadata.get('payment_record_id')
    correlation_id = metadata.get('correlation_id')
    last_error = payment_intent.get('last_payment_error')
    error_message = last_error.get('message', 'Unknown Stripe payment error') if last_error else 'Unknown Stripe payment error'
    error_code = last_error.get('code') if last_error else None

    if not payment_record_id:
        logger.warning(f"Webhook 'payment_intent.payment_failed' received for PI {pi_id} without 'payment_record_id' in metadata.")
        return
    if not correlation_id:
         logger.warning(f"Webhook 'payment_intent.payment_failed' received for PI {pi_id} without 'correlation_id' in metadata.")

    logger.info(f"Processing 'payment_intent.payment_failed' for Payment {payment_record_id} (PI: {pi_id}). Error: {error_message}")

    payment = Payment.query.get(payment_record_id)
    if not payment:
        logger.error(f"Payment record {payment_record_id} not found for failed PI {pi_id}.")
        return

    current_status = payment.status
    new_status = PaymentStatus.FAILED

    if not update_payment_status(payment_record_id, new_status, pi_id):
        logger.error(f"Failed to update DB status to {new_status.value} for Payment {payment_record_id} after PI {pi_id} failed.")
        return

    # Publish Kafka event if status changed meaningfully
    if current_status != PaymentStatus.FAILED:
        if correlation_id:
            logger.info(f"Publishing payment.failed event for failed Payment {payment_record_id} (Correlation ID: {correlation_id})")
            publish_payment_failed_event(
                kafka_client,
                correlation_id,
                {
                    'error': 'STRIPE_PAYMENT_FAILED',
                    'message': error_message,
                    'stripe_code': error_code,
                    'payment_id': payment_record_id,
                    'order_id': payment.order_id,
                }
            )
        else:
             logger.warning(f"Cannot publish payment.failed event for failed Payment {payment_record_id}: Missing correlation_id.")
    else:
        logger.info(f"Payment {payment_record_id} already in status FAILED. No Kafka event needed for PI failure.")

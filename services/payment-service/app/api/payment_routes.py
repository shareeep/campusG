import logging
import uuid
from datetime import datetime, timezone # Added timezone

from app import db
from app.models.models import Payment
from flask import Blueprint, jsonify, current_app, request

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

PAYMENT_COMMANDS_TOPIC = 'payment_commands' # Define the topic name

# Note: The authorize, release, and revert endpoints have been removed.
# Payment authorization is now triggered by the 'authorize_payment' Kafka command.
# Release/revert logic will likely be triggered by Kafka commands from other sagas
# (e.g., CompleteOrderSaga, CancelOrderSaga) or potentially Stripe webhooks
# indicating capture/refund completion, depending on the final architecture.

@api.route('/payment/<order_id>/status', methods=['GET'])
def get_payment_status(order_id):
    """
    Check the status of a payment for a specific order.
    """
    logger.debug(f"Received request for payment status for order_id: {order_id}")
    try:
        payment = Payment.query.filter_by(order_id=order_id).first()
        if not payment:
            logger.warning(f"Payment not found for order_id: {order_id}")
            return jsonify({"success": False, "error": "NOT_FOUND", "message": "Payment not found"}), 404

        logger.info(f"Returning status for payment {payment.payment_id} (order: {order_id}): {payment.status.value}")
        return jsonify({
            "success": True,
            "payment": payment.to_dict() # Uses the updated to_dict method
        }), 200

    except Exception as e:
        logger.error(f"Error getting payment status for order {order_id}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "SERVER_ERROR",
            "message": "An internal server error occurred"
        }), 500

@api.route('/payment/<payment_id>/details', methods=['GET'])
def get_payment_details(payment_id):
    """
    Get detailed information about a specific payment using its internal payment_id.
    """
    logger.debug(f"Received request for payment details for payment_id: {payment_id}")
    try:
        # Use query.get for primary key lookup if payment_id is the PK
        # If payment_id is the secondary UUID, use filter_by
        # Assuming payment_id is the unique secondary ID based on the model
        payment = Payment.query.filter_by(payment_id=payment_id).first()
        # If 'id' is the primary key and payment_id is just a unique string:
        # payment = Payment.query.get(payment_id) # This would fail if payment_id is not the PK

        if not payment:
            logger.warning(f"Payment not found for payment_id: {payment_id}")
            return jsonify({"success": False, "error": "NOT_FOUND", "message": "Payment not found"}), 404

        logger.info(f"Returning details for payment {payment.payment_id}")
        return jsonify({
            "success": True,
            "payment": payment.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error getting payment details for payment {payment_id}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "SERVER_ERROR",
            "message": "An internal server error occurred"
        }), 500

# Health check endpoint
@api.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    # Add checks for DB and Kafka connection if needed
    return jsonify({"status": "healthy"}), 200


# --- API Endpoints to Trigger Kafka Commands ---

@api.route('/payment/<payment_id>/release', methods=['POST'])
def trigger_release_payment(payment_id):
    """
    API endpoint to trigger the 'release_payment' Kafka command.

    Expects a JSON body with the following format:
    {
        "runner_id": "string",
        "runner_connect_account_id": "string"
    }
    """
    logger.info(f"Received API request to trigger release for payment_id: {payment_id}")
    data = request.get_json()
    if not data:
        logger.error("Missing JSON body in release request")
        return jsonify({"success": False, "error": "BAD_REQUEST", "message": "Missing JSON body"}), 400

    runner_id = data.get('runner_id')
    runner_connect_account_id = data.get('runner_connect_account_id')

    if not runner_id or not runner_connect_account_id:
        logger.error("Missing 'runner_id' or 'runner_connect_account_id' in release request body")
        return jsonify({"success": False, "error": "BAD_REQUEST", "message": "Missing 'runner_id' or 'runner_connect_account_id'"}), 400

    correlation_id = str(uuid.uuid4())
    payload = {
        'payment_id': payment_id,
        'runner_id': runner_id,
        'runner_connect_account_id': runner_connect_account_id
    }
    message = {
        'type': 'release_payment',
        'correlation_id': correlation_id,
        'timestamp': datetime.now(timezone.utc).isoformat(), # Use timezone.utc
        'payload': payload,
        'source': 'payment-api'
    }

    try:
        producer = current_app.kafka_client.producer
        if not producer:
             logger.error("Kafka producer is not available.")
             return jsonify({"success": False, "error": "KAFKA_ERROR", "message": "Kafka producer unavailable"}), 503

        logger.info(f"Publishing 'release_payment' command to Kafka topic '{PAYMENT_COMMANDS_TOPIC}' with correlation_id: {correlation_id}")
        producer.send(PAYMENT_COMMANDS_TOPIC, message)
        producer.flush() # Ensure message is sent

        return jsonify({
            "success": True,
            "message": "Release payment command queued successfully.",
            "correlation_id": correlation_id
        }), 202 # Accepted

    except Exception as e:
        logger.error(f"Failed to publish 'release_payment' command to Kafka: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "KAFKA_PUBLISH_ERROR", "message": "Failed to publish command to Kafka"}), 500


@api.route('/payment/<payment_id>/revert', methods=['POST'])
def trigger_revert_payment(payment_id):
    """
    API endpoint to trigger the 'revert_payment' Kafka command.

    Optionally accepts a JSON body with the following format:
    {
        "reason": "string" // Optional
    }
    If no body or reason is provided, a default reason might be used downstream.
    """
    logger.info(f"Received API request to trigger revert for payment_id: {payment_id}")
    data = request.get_json()
    reason = data.get('reason') if data else None # Optional reason

    correlation_id = str(uuid.uuid4())
    payload = {'payment_id': payment_id}
    if reason:
        payload['reason'] = reason

    message = {
        'type': 'revert_payment',
        'correlation_id': correlation_id,
        'timestamp': datetime.now(timezone.utc).isoformat(), # Use timezone.utc
        'payload': payload,
        'source': 'payment-api'
    }

    try:
        producer = current_app.kafka_client.producer
        if not producer:
             logger.error("Kafka producer is not available.")
             return jsonify({"success": False, "error": "KAFKA_ERROR", "message": "Kafka producer unavailable"}), 503

        logger.info(f"Publishing 'revert_payment' command to Kafka topic '{PAYMENT_COMMANDS_TOPIC}' with correlation_id: {correlation_id}")
        producer.send(PAYMENT_COMMANDS_TOPIC, message)
        producer.flush() # Ensure message is sent

        return jsonify({
            "success": True,
            "message": "Revert payment command queued successfully.",
            "correlation_id": correlation_id
        }), 202 # Accepted

    except Exception as e:
        logger.error(f"Failed to publish 'revert_payment' command to Kafka: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "KAFKA_PUBLISH_ERROR", "message": "Failed to publish command to Kafka"}), 500

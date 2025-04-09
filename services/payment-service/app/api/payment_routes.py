import logging
import uuid
from datetime import datetime, timezone # Added timezone

from app import db
# Import PaymentStatus as well
from app.models.models import Payment, PaymentStatus
from flask import Blueprint, jsonify, current_app, request
from flasgger import swag_from # Import swag_from
# Import SQLAlchemyError for specific DB error handling
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

PAYMENT_COMMANDS_TOPIC = 'payment_commands' # Define the topic name

# Note: The authorize, release, and revert endpoints have been removed.
# Payment authorization is now triggered by the 'authorize_payment' Kafka command.
# Release/revert logic will likely be triggered by Kafka commands from other sagas
# (e.g., CompleteOrderSaga, CancelOrderSaga) or potentially Stripe webhooks
# indicating capture/refund completion, depending on the final architecture.

@api.route('/payment/<order_id>/status', methods=['GET'])
@swag_from({
    'tags': ['Payments'],
    'summary': 'Get payment status for a specific order.',
    'parameters': [
        {
            'name': 'order_id', 'in': 'path', 'type': 'string', 'required': True,
            'description': 'The ID of the order associated with the payment.'
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment status retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'payment': { '$ref': '#/definitions/Payment' }
                }
            }
        },
        '404': {'description': 'Payment not found for the given order ID.'},
        '500': {'description': 'Internal Server Error'}
    },
    # Define Payment schema (simplified example)
    'definitions': {
        'Payment': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'description': 'Internal primary key'},
                'payment_id': {'type': 'string', 'format': 'uuid', 'description': 'Public unique ID for the payment record'},
                'order_id': {'type': 'string', 'format': 'uuid'},
                'customer_id': {'type': 'string'},
                'runner_id': {'type': 'string', 'nullable': True},
                'amount': {'type': 'number', 'format': 'float'},
                'currency': {'type': 'string', 'example': 'sgd'},
                'status': {'type': 'string', 'enum': [s.name for s in PaymentStatus]},
                'stripe_payment_intent_id': {'type': 'string', 'nullable': True},
                'stripe_transfer_id': {'type': 'string', 'nullable': True},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'}
            }
        }
    }
})
def get_payment_status(order_id):
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
@swag_from({
    'tags': ['Payments'],
    'summary': 'Get details for a specific payment by its ID.',
    'parameters': [
        {
            'name': 'payment_id', 'in': 'path', 'type': 'string', 'format': 'uuid', 'required': True,
            'description': 'The internal UUID of the payment record.'
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment details retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'payment': { '$ref': '#/definitions/Payment' }
                }
            }
        },
        '404': {'description': 'Payment not found for the given payment ID.'},
        '500': {'description': 'Internal Server Error'}
    }
})
def get_payment_details(payment_id):
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
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check for the Payment Service API.',
    'responses': {
        '200': {
            'description': 'Service is healthy.',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'healthy'}
                }
            }
        }
    }
})
def health_check():
    # Add checks for DB and Kafka connection if needed
    return jsonify({"status": "healthy"}), 200


# --- New Payment History Route ---
@api.route('/history/<user_id>', methods=['GET'])
@swag_from({
    'tags': ['Payments'],
    'summary': "Get payment history summary for a user.",
    'description': "Fetches total amounts and counts for money spent (as customer) and earned (as runner) by a user.",
    'parameters': [
        {
            'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True,
            'description': 'The ID of the user (likely Clerk User ID).'
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment history summary retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'userId': {'type': 'string'},
                    'totalSpent': {'type': 'number', 'format': 'float'},
                    'totalEarned': {'type': 'number', 'format': 'float'},
                    'spentCount': {'type': 'integer'},
                    'earnedCount': {'type': 'integer'}
                }
            }
        },
        '500': {'description': 'Internal Server Error (Database or Processing error)'}
    }
})
def get_payment_history(user_id):
    logger.info(f"Fetching payment history for user_id: {user_id}")

    try:
        # Query for money spent (user is the customer)
        # Include AUTHORIZED and SUCCEEDED as they represent charges initiated by the customer
        spent_payments = Payment.query.filter(
            Payment.customer_id == user_id,
            Payment.status.in_([PaymentStatus.AUTHORIZED, PaymentStatus.SUCCEEDED])
        ).order_by(Payment.created_at.desc()).all()

        # Query for money earned (user is the runner)
        # Include only SUCCEEDED payments (assuming this status means payout was successful)
        earned_payments = Payment.query.filter(
            Payment.runner_id == user_id,
            Payment.status == PaymentStatus.SUCCEEDED
            # Removed check for transfer_id.isnot(None) as SUCCEEDED should be sufficient
        ).order_by(Payment.created_at.desc()).all()

        # Get counts
        spent_count = len(spent_payments)
        earned_count = len(earned_payments)

        # Calculate lifetime totals from the fetched objects
        # Convert Numeric to float for summation
        total_spent = sum(float(p.amount) for p in spent_payments)
        total_earned = sum(float(p.amount) for p in earned_payments)

        logger.info(f"Found {spent_count} spent (Total: {total_spent:.2f}) and {earned_count} earned (Total: {total_earned:.2f}) transactions for user {user_id}")

        return jsonify({
            'userId': user_id,
            'totalSpent': round(total_spent, 2),
            'totalEarned': round(total_earned, 2),
            'spentCount': spent_count,   # Return count instead of list
            'earnedCount': earned_count # Return count instead of list
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = f"Database error fetching payment history for user {user_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": "DATABASE_ERROR", "message": error_msg}), 500
    except Exception as e:
        error_msg = f"Unexpected error fetching payment history for user {user_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": "PROCESSING_ERROR", "message": error_msg}), 500


# --- API Endpoints to Trigger Kafka Commands ---

@api.route('/payment/<payment_id>/release', methods=['POST'])
@swag_from({
    'tags': ['Kafka Triggers'],
    'summary': "Trigger 'release_payment' Kafka command.",
    'description': "Publishes a 'release_payment' command to Kafka, typically used to initiate payment capture and transfer to a runner.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'payment_id', 'in': 'path', 'type': 'string', 'format': 'uuid', 'required': True,
            'description': 'The internal UUID of the payment record to release.'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['runner_id', 'runner_connect_account_id'],
                'properties': {
                    'runner_id': {'type': 'string', 'description': 'Clerk User ID of the runner.'},
                    'runner_connect_account_id': {'type': 'string', 'description': "Runner's Stripe Connect account ID (acct_...)."}
                }
            }
        }
    ],
    'responses': {
        '202': {
            'description': 'Release payment command queued successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'correlation_id': {'type': 'string', 'format': 'uuid'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing body or required fields)'},
        '500': {'description': 'Failed to publish command to Kafka.'},
        '503': {'description': 'Kafka producer unavailable.'}
    }
})
def trigger_release_payment(payment_id):
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
@swag_from({
    'tags': ['Kafka Triggers'],
    'summary': "Trigger 'revert_payment' Kafka command.",
    'description': "Publishes a 'revert_payment' command to Kafka, typically used to initiate payment cancellation or refund.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'payment_id', 'in': 'path', 'type': 'string', 'format': 'uuid', 'required': True,
            'description': 'The internal UUID of the payment record to revert.'
        },
        {
            'in': 'body',
            'name': 'body',
            'required': False,
            'schema': {
                'type': 'object',
                'properties': {
                    'reason': {'type': 'string', 'description': 'Optional reason for reverting the payment.'}
                }
            }
        }
    ],
    'responses': {
        '202': {
            'description': 'Revert payment command queued successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'correlation_id': {'type': 'string', 'format': 'uuid'}
                }
            }
        },
        '500': {'description': 'Failed to publish command to Kafka.'},
        '503': {'description': 'Kafka producer unavailable.'}
    }
})
def trigger_revert_payment(payment_id):
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

import logging

from app import db
from app.models.models import Payment
from flask import Blueprint, jsonify, current_app

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

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

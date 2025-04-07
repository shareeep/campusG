import logging
from flask import Blueprint, request, jsonify
from app import db
from app.models.saga_state import CreateOrderSagaState
from datetime import datetime

logger = logging.getLogger(__name__)
timer_bp = Blueprint('timer', __name__)

@timer_bp.route('/timer-callback', methods=['POST'])
def timer_callback():
    """
    Callback endpoint for Timer Service to notify when a timer is triggered.
    The Timer Service will call this endpoint when a timer expires.
    """
    try:
        data = request.json
        if not data:
            logger.error("No data provided in timer callback")
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        # Extract data from the timer notification
        saga_id = data.get('saga_id')
        order_id = data.get('order_id')
        timer_id = data.get('timer_id')
        
        logger.info(f"Received timer callback for saga_id: {saga_id}, order_id: {order_id}, timer_id: {timer_id}")
        
        if not saga_id:
            logger.error("No saga_id provided in timer callback")
            return jsonify({"success": False, "error": "No saga_id provided"}), 400
            
        # Process timer expiration for the saga
        # This could trigger a timeout event or other business logic
        
        # For now, we'll just log it since the saga should already be completed
        # In a real implementation, you might check if the order is still active
        # and take appropriate action (e.g., cancel the order if not accepted)
        
        logger.info(f"Timer triggered for saga {saga_id} - timer notification processed")
        
        # Return success response
        return jsonify({
            "success": True,
            "message": f"Timer callback processed for saga {saga_id}"
        }), 200
            
    except Exception as e:
        logger.error(f"Error processing timer callback: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

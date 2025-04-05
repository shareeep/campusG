"""
HTTP Routes for Timer Service

This module provides HTTP endpoints for starting timers,
acting as a placeholder for the future OutSystems integration.
"""

import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.services.kafka_service import publish_timer_started_event

logger = logging.getLogger(__name__)

# Create Blueprint for HTTP routes
http_bp = Blueprint('http', __name__)

@http_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "timer-service"}), 200

@http_bp.route('/api/timers', methods=['POST'])
def start_timer():
    """
    HTTP endpoint to start a timer for an order
    
    This serves as a placeholder for the future OutSystems integration.
    It immediately publishes a timer.started event to Kafka.
    
    Expected JSON payload:
    {
        "order_id": "string",
        "customer_id": "string",
        "timeout_at": "ISO8601 timestamp", 
        "saga_id": "string" (used as correlation_id)
    }
    
    Returns:
        JSON response indicating success or failure
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    # Validate required fields
    order_id = data.get('order_id')
    customer_id = data.get('customer_id')
    timeout_at = data.get('timeout_at')
    correlation_id = data.get('saga_id', data.get('correlation_id'))
    
    if not order_id:
        return jsonify({"success": False, "error": "order_id is required"}), 400
    
    if not timeout_at:
        return jsonify({"success": False, "error": "timeout_at is required"}), 400
    
    if not correlation_id:
        return jsonify({"success": False, "error": "saga_id or correlation_id is required"}), 400
    
    # Log the request
    logger.info(f"Timer requested for order {order_id}, customer {customer_id}, timeout: {timeout_at}")
    
    # Generate a timer ID
    timer_id = str(uuid.uuid4())
    
    # In the future, this is where you'd call OutSystems
    # response = requests.post(OUTSYSTEMS_URL, json=data)
    
    # For testing, immediately publish a timer.started event via Kafka
    try:
        # Get kafka client from app context
        kafka_client = current_app.kafka_client
        
        if not kafka_client:
            logger.error("Kafka client not available")
            return jsonify({
                "success": False,
                "error": "Kafka client not available",
                "message": "Timer could not be started"
            }), 500
        
        # Publish the timer.started event
        success = publish_timer_started_event(
            kafka_client,
            correlation_id,
            {
                'order_id': order_id,
                'customer_id': customer_id,
                'timeout_at': timeout_at,
                'timer_id': timer_id,
                'status': 'RUNNING'
            }
        )
        
        if not success:
            logger.error(f"Failed to publish timer.started event for order {order_id}")
            return jsonify({
                "success": False,
                "error": "Failed to publish timer event",
                "message": "Timer started but notification failed"
            }), 500
            
        logger.info(f"Timer {timer_id} started for order {order_id}")
        
        return jsonify({
            "success": True,
            "message": "Timer started successfully",
            "timer_id": timer_id,
            "order_id": order_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error starting timer for order {order_id}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to start timer"
        }), 500

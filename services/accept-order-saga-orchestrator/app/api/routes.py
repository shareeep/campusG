import requests
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

accept_order_saga_bp = Blueprint('accept_order_saga', __name__)

@accept_order_saga_bp.route('/acceptOrder', methods=['POST'])
def accept_order():
    """
    Orchestrator endpoint for accepting an order via the Accept Order Saga.

    Expected JSON input:
    {
        "orderId": "order-uuid",
        "runner_id": "runner-uuid"
    }

    Flow:
      1. POST /verifyAndAcceptOrder to the Order Service.
      2. POST /orderAccepted to the Timer Service.
      3. Return a success response to the UI indicating order acceptance.
    """
    try:
        data = request.json
        if not data or 'orderId' not in data or 'runner_id' not in data:
            return jsonify({'error': 'Missing required fields: orderId and runner_id'}), 400

        order_id = data['orderId']
        runner_id = data['runner_id']

        # 1. Call the Order Service's /verifyAndAcceptOrder endpoint.
        order_service_url = current_app.config.get('ORDER_SERVICE_URL', 'http://localhost:3002')
        # Corrected URL: Removed '/api' prefix as the Order Service blueprint is registered at root
        verify_url = f"{order_service_url}/verifyAndAcceptOrder"
        order_payload = {
            "orderId": order_id,
            "runner_id": runner_id
        }
        order_response = requests.post(verify_url, json=order_payload, timeout=10)
        if order_response.status_code != 200:
            current_app.logger.error(f"Order Service error: {order_response.text}")
            return jsonify({'error': 'Order Service failed to verify and accept order.'}), 500

            return jsonify({'error': 'Order Service failed to verify and accept order.'}), 500

        # 2. Call the Timer Service to stop the timer for this order.
        # Use the provided OutSystems URL as the default and ensure the path is correct.
        timer_service_url = current_app.config.get('TIMER_SERVICE_URL', 'https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI/StopTimer')
        # The URL from config likely already includes the full path, so just use it directly.
        # If TIMER_SERVICE_URL only contains the base, you'd append '/StopTimer' here.
        timer_url = timer_service_url
        # Use the required payload structure with capitalized keys
        timer_payload = {
            "OrderId": order_id,
            "RunnerId": runner_id
        }
        try:
            current_app.logger.info(f"Calling Timer Service at {timer_url} with payload: {json.dumps(timer_payload)}")
            timer_response = requests.post(timer_url, json=timer_payload, timeout=10)
            timer_response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            current_app.logger.info(f"Timer Service response: {timer_response.status_code}")
        except requests.exceptions.RequestException as timer_err:
            current_app.logger.error(f"Timer Service request failed: {timer_err}")
            # Decide if this failure should prevent order acceptance.
            # For now, let's log it but potentially allow the saga to succeed if the Order Service part worked.
            # If stopping the timer is critical, return 500 here:
            # return jsonify({'error': f'Timer Service failed: {timer_err}'}), 500
            pass # Continue even if timer call fails

        # 3. Return a 200 response to the UI indicating the order was accepted (by Order Service).
        return jsonify({
            'message': 'Order accepted successfully',
            'orderId': order_id,
            'runner_id': runner_id,
            'status': 'ORDER_ACCEPTED',
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in acceptOrder saga: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to accept order: {str(e)}"}), 500

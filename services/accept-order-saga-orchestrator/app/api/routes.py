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
        verify_url = f"{order_service_url}/api/verifyAndAcceptOrder"
        order_payload = {
            "orderId": order_id,
            "runner_id": runner_id
        }
        order_response = requests.post(verify_url, json=order_payload, timeout=10)
        if order_response.status_code != 200:
            current_app.logger.error(f"Order Service error: {order_response.text}")
            return jsonify({'error': 'Order Service failed to verify and accept order.'}), 500

        # 2. Notify the Timer Service that the order has been accepted.
        timer_service_url = current_app.config.get('TIMER_SERVICE_URL', 'https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI/StopTimer')
        timer_url = f"{timer_service_url}"
        timer_payload = {
            "orderId": order_id,
            "runner_id": runner_id
        }
        timer_response = requests.post(timer_url, json=timer_payload, timeout=10)
        if timer_response.status_code != 200:
            current_app.logger.error(f"Timer Service error: {timer_response.text}")
            return jsonify({'error': 'Timer Service failed to update order acceptance.'}), 500

        # 3. Return a 200 response to the UI indicating the order was accepted.
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

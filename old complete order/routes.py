import time
import json
from flask import Blueprint, Response, request, current_app, jsonify
from app.models.saga_state import CompleteOrderSagaState
from app.services.complete_order_saga_orchestrator import init_complete_order_orchestrator

complete_order_saga_bp = Blueprint('complete_order_saga', __name__)

@complete_order_saga_bp.route('/completeOrder', methods=['POST'])
def complete_order():
    """
    Endpoint for the UI to trigger the complete order saga when the runner declares the order delivered.
    
    Expected JSON input:
    {
        "orderId": "order-uuid"
    }
    
    Flow:
      1. The saga orchestrator updates the order status to "DELIVERED".
      2. Retrieves runner payment info.
      3. Commands the Payment Service to release funds.
      4. Updates the order status to "COMPLETED".
      5. Returns a response indicating the order has been completed.
    """
    data = request.get_json()
    if not data or 'orderId' not in data:
        return jsonify({'error': 'Missing required field: orderId'}), 400
    
    order_id = data['orderId']
    
    # Get the orchestrator instance from the app context,
    # or initialize it if it doesn't exist.
    orchestrator = current_app.config.get('COMPLETE_ORDER_ORCHESTRATOR')
    if orchestrator is None:
        orchestrator = init_complete_order_orchestrator()
        if orchestrator is None:
            return jsonify({'error': 'Failed to initialize complete order orchestrator'}), 500
        # Optionally store in app config or context for reuse:
        current_app.config['COMPLETE_ORDER_ORCHESTRATOR'] = orchestrator

    # Start the saga for the given order_id.
    success, message, saga_state = orchestrator.start_saga(order_id)
    if not success:
        return jsonify({'error': message}), 500

    # If everything went well, return a success response.
    return jsonify({
        'message': 'Complete order saga started successfully',
        'orderId': order_id,
        'sagaId': saga_state.id,
        'status': saga_state.status.value,
        'timestamp': saga_state.created_at.isoformat()
    }), 200

@complete_order_saga_bp.route('/orderUpdateStream/<saga_id>', methods=['GET'])
def order_update_stream(saga_id):
    """
    SSE endpoint that streams updates for a specific complete order saga.
    
    The UI subscribes to this endpoint to get real-time status updates for the saga.
    """
    def event_stream():
        while True:
            # Query the saga state from the database
            saga_state = CompleteOrderSagaState.query.get(saga_id)
            if saga_state:
                data = {
                    'sagaId': saga_state.id,
                    'orderId': saga_state.order_id,
                    'status': saga_state.status.value,
                    'currentStep': saga_state.current_step.value if saga_state.current_step else None,
                    'updatedAt': saga_state.updated_at.isoformat()
                }
                yield f"data: {json.dumps(data)}\n\n"
                
                # Stop streaming if the saga is completed or failed.
                if saga_state.status in ['COMPLETED', 'FAILED', 'COMPENSATED']:
                    break
            else:
                # If no saga state is found, report that as an error update.
                yield f"data: {json.dumps({'error': 'Saga state not found'})}\n\n"
                break
            time.sleep(2)  # Poll every 2 seconds; adjust as needed.
    
    return Response(event_stream(), mimetype='text/event-stream')
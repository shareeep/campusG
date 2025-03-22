from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime, timedelta
from app.models.models import Timer
from app import db
from app.services.kafka_service import kafka_client

api = Blueprint('api', __name__)

@api.route('/start-request-timer', methods=['POST'])
def start_request_timer():
    """
    Start a timer for order request
    
    Request body should contain:
    {
        "orderId": "order-123",
        "customerId": "customer-456",
        "runnerId": "runner-789" (optional, may be null at this stage)
    }
    
    This creates a timer record and starts tracking the order request.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        customer_id = data.get('customerId')
        runner_id = data.get('runnerId', '')  # May be empty initially
        
        if not order_id or not customer_id:
            return jsonify({'success': False, 'message': 'Missing required fields (orderId, customerId)'}), 400
            
        # Check if timer already exists for this order
        existing_timer = Timer.query.filter_by(order_id=order_id).first()
        if existing_timer:
            return jsonify({
                'success': False, 
                'message': f'Timer already exists for order {order_id}'
            }), 400
        
        # Create new timer
        timer = Timer(
            timer_id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            runner_id=runner_id,
            runner_accepted=False,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(timer)
        db.session.commit()
        
        # Publish timer started event to Kafka
        kafka_client.publish('timer-events', {
            'type': 'TIMER_STARTED',
            'payload': {
                'timerId': timer.timer_id,
                'orderId': order_id,
                'customerId': customer_id,
                'runnerId': runner_id
            }
        })
        
        current_app.logger.info(f"Timer started for order {order_id}")
        
        return jsonify({
            'success': True,
            'message': 'Timer started successfully',
            'timerId': timer.timer_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error starting timer: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to start timer: {str(e)}"}), 500

@api.route('/stop-request-timer', methods=['POST'])
def stop_request_timer():
    """
    Stop an active timer when a runner accepts the order
    
    Request body should contain:
    {
        "orderId": "order-123",
        "runnerId": "runner-789"
    }
    
    This updates the timer record with runner acceptance.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        runner_id = data.get('runnerId')
        
        if not order_id or not runner_id:
            return jsonify({'success': False, 'message': 'Missing required fields (orderId, runnerId)'}), 400
            
        # Find the timer for this order
        timer = Timer.query.filter_by(order_id=order_id).first()
        
        if not timer:
            return jsonify({'success': False, 'message': 'Timer not found for order'}), 404
            
        if timer.runner_accepted:
            return jsonify({'success': False, 'message': 'Timer already accepted'}), 400
            
        # Update timer with runner acceptance
        timer.runner_id = runner_id
        timer.runner_accepted = True
        db.session.commit()
        
        # Publish timer stopped event to Kafka
        kafka_client.publish('timer-events', {
            'type': 'TIMER_STOPPED',
            'payload': {
                'timerId': timer.timer_id,
                'orderId': order_id,
                'runnerId': runner_id
            }
        })
        
        current_app.logger.info(f"Timer stopped for order {order_id} - accepted by runner {runner_id}")
        
        return jsonify({
            'success': True,
            'message': 'Timer stopped successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error stopping timer: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to stop timer: {str(e)}"}), 500

@api.route('/cancel-timer', methods=['POST'])
def cancel_timer():
    """
    Cancel an active timer
    
    Request body should contain:
    {
        "orderId": "order-123"
    }
    
    This is used when the order is cancelled or times out.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'Missing order ID'}), 400
            
        # Find the timer for this order
        timer = Timer.query.filter_by(order_id=order_id).first()
        
        if not timer:
            return jsonify({'success': False, 'message': 'Timer not found for order'}), 404
            
        # Delete the timer
        db.session.delete(timer)
        db.session.commit()
        
        # Publish timer cancelled event to Kafka
        kafka_client.publish('timer-events', {
            'type': 'TIMER_CANCELLED',
            'payload': {
                'timerId': timer.timer_id,
                'orderId': order_id
            }
        })
        
        current_app.logger.info(f"Timer cancelled for order {order_id}")
        
        return jsonify({
            'success': True,
            'message': 'Timer cancelled successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling timer: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to cancel timer: {str(e)}"}), 500

@api.route('/check-order-timeout', methods=['GET'])
def check_order_timeout():
    """
    Check for orders that have timed out (30 minutes without runner acceptance)
    
    This endpoint is called by a scheduled job to find and handle timeout events.
    """
    try:
        # Calculate timeout threshold (30 minutes ago)
        timeout_threshold = datetime.utcnow() - timedelta(minutes=30)
        
        # Find timers older than 30 minutes that haven't been accepted
        timed_out_timers = Timer.query.filter(
            Timer.created_at <= timeout_threshold,
            Timer.runner_accepted == False
        ).all()
        
        if not timed_out_timers:
            return jsonify({
                'success': True,
                'message': 'No timed out orders found',
                'timedOutOrders': []
            }), 200
        
        timed_out_orders = []
        
        # Process each timed out order
        for timer in timed_out_timers:
            timed_out_orders.append({
                'orderId': timer.order_id,
                'timerId': timer.timer_id,
                'customerId': timer.customer_id,
                'createdAt': timer.created_at.isoformat()
            })
            
            # Publish timer timeout event to Kafka
            kafka_client.publish('timer-events', {
                'type': 'ORDER_TIMEOUT',
                'payload': {
                    'timerId': timer.timer_id,
                    'orderId': timer.order_id,
                    'customerId': timer.customer_id
                }
            })
            
            # Delete the timer
            db.session.delete(timer)
        
        # Commit all changes
        db.session.commit()
        
        current_app.logger.info(f"Found {len(timed_out_orders)} timed out orders")
        
        return jsonify({
            'success': True,
            'message': f'Found {len(timed_out_orders)} timed out orders',
            'timedOutOrders': timed_out_orders
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error checking order timeouts: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to check order timeouts: {str(e)}"}), 500

@api.route('/timers/<timer_id>', methods=['GET'])
def get_timer(timer_id):
    """Get a specific timer by ID"""
    try:
        timer = Timer.query.get(timer_id)
        
        if not timer:
            return jsonify({'success': False, 'message': 'Timer not found'}), 404
            
        return jsonify({
            'success': True,
            'timer': timer.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting timer {timer_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get timer: {str(e)}"}), 500

@api.route('/timers/order/<order_id>', methods=['GET'])
def get_timer_by_order(order_id):
    """Get the timer for a specific order"""
    try:
        timer = Timer.query.filter_by(order_id=order_id).first()
        
        if not timer:
            return jsonify({'success': False, 'message': 'Timer not found for order'}), 404
            
        return jsonify({
            'success': True,
            'timer': timer.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting timer for order {order_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get timer: {str(e)}"}), 500

from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime, timezone, timedelta
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
        runner_id = data.get('runnerId')  # Can be None
        
        if not order_id or not customer_id:
            return jsonify({'success': False, 'message': 'Missing required fields (orderId, customerId)'}), 400
            
        # Check if timer already exists for this order
        existing_timer = Timer.query.filter_by(order_id=order_id).first()
        if existing_timer:
            return jsonify({
                'success': False, 
                'message': f'Timer already exists for order {order_id}'
            }), 400
        
        # Calculate expiration time (30 minutes from now)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        # Create new timer
        timer = Timer(
            timer_id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            runner_id=runner_id,
            runner_accepted=False,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        
        # Save to database
        db.session.add(timer)
        db.session.commit()
        
        # Publish timer started event to Kafka
        kafka_topic = current_app.config.get('KAFKA_TOPIC_TIMER_EVENTS', 'timer-events')
        kafka_client.publish(kafka_topic, {
            'type': 'TIMER_STARTED',
            'payload': {
                'timerId': timer.timer_id,
                'orderId': order_id,
                'customerId': customer_id,
                'runnerId': runner_id,
                'expiresAt': expires_at.isoformat()
            }
        })
        
        current_app.logger.info(f"Timer started for order {order_id}")
        
        return jsonify({
            'success': True,
            'message': 'Timer started successfully',
            'timerId': timer.timer_id,
            'expiresAt': timer.expires_at.isoformat()
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
        kafka_topic = current_app.config.get('KAFKA_TOPIC_TIMER_EVENTS', 'timer-events')
        kafka_client.publish(kafka_topic, {
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
        kafka_topic = current_app.config.get('KAFKA_TOPIC_TIMER_EVENTS', 'timer-events')
        kafka_client.publish(kafka_topic, {
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

def check_order_timeout():
    """
    Check for orders that have timed out
    This function is called by the scheduler every minute
    """
    try:
        # Current time
        now = datetime.now(timezone.utc)
        
        # Find timers that have expired and haven't been accepted
        timed_out_timers = Timer.query.filter(
            Timer.expires_at <= now,
            Timer.runner_accepted == False
        ).all()
        
        if not timed_out_timers:
            current_app.logger.info("No timed out orders found")
            return
        
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
            kafka_topic = current_app.config.get('KAFKA_TOPIC_TIMER_EVENTS', 'timer-events')
            kafka_client.publish(kafka_topic, {
                'type': 'ORDER_TIMEOUT',
                'payload': {
                    'timerId': timer.timer_id,
                    'orderId': timer.order_id,
                    'customerId': timer.customer_id,
                    'expiresAt': timer.expires_at.isoformat()
                }
            })
            
            # Delete the timer
            db.session.delete(timer)
        
        # Commit all changes
        db.session.commit()
        
        current_app.logger.info(f"Found and processed {len(timed_out_orders)} timed out orders")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error checking order timeouts: {str(e)}")
        raise  # Re-raise to be caught by the scheduler wrapper

# Manual trigger endpoint for testing
@api.route('/check-order-timeout', methods=['GET'])
def check_order_timeout_endpoint():
    """Manually trigger timeout check (for testing)"""
    try:
        check_order_timeout()
        return jsonify({
            'success': True,
            'message': 'Timeout check completed'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in timeout check: {str(e)}")
        return jsonify({'success': False, 'message': f"Error: {str(e)}"}), 500

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

@api.route('/test-quick-timer', methods=['POST'])
def test_quick_timer():
    """
    Create a test timer that expires in 1 minute
    For testing purposes only
    
    Request body:
    {
        "orderId": "test-order-123",
        "customerId": "test-customer-456"
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        order_id = data.get('orderId', f"test-order-{str(uuid.uuid4())}")
        customer_id = data.get('customerId', f"test-customer-{str(uuid.uuid4())}")
        
        # Check if timer already exists for this order
        existing_timer = Timer.query.filter_by(order_id=order_id).first()
        if existing_timer:
            return jsonify({
                'success': False, 
                'message': f'Timer already exists for order {order_id}'
            }), 400
        
        # Calculate expiration time (1 minute from now)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)
        
        # Create new timer
        timer = Timer(
            timer_id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=customer_id,
            runner_accepted=False,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        
        # Save to database
        db.session.add(timer)
        db.session.commit()
        
        # Publish timer started event to Kafka
        kafka_topic = current_app.config.get('KAFKA_TOPIC_TIMER_EVENTS', 'timer-events')
        kafka_client.publish(kafka_topic, {
            'type': 'TIMER_STARTED',
            'payload': {
                'timerId': timer.timer_id,
                'orderId': order_id,
                'customerId': customer_id,
                'expiresAt': expires_at.isoformat(),
                'isTestTimer': True
            }
        })
        
        current_app.logger.info(f"Test timer started for order {order_id}, will expire in 1 minute")
        
        return jsonify({
            'success': True,
            'message': 'Test timer started successfully',
            'timerId': timer.timer_id,
            'expiresAt': timer.expires_at.isoformat(),
            'note': 'This timer will expire in 1 minute'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error starting test timer: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to start test timer: {str(e)}"}), 500

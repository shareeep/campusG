from flask import Blueprint, jsonify, request, current_app
from flasgger import swag_from # Import swag_from
from datetime import datetime, timezone
import json
import threading
import uuid
import logging
from app.models.models import Notifications
from app import db
from app.services.kafka_service import kafka_client

api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check for the Notification Service API.',
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
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@api.route('/send-notification', methods=['POST'])
@swag_from({
    'tags': ['Notifications'],
    'summary': 'Manually create a notification log entry.',
    'description': 'Creates a notification record directly in the database. This endpoint is primarily for manual logging or testing and does NOT trigger actual user notifications or Kafka events.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['customerId', 'orderId', 'event'],
                'properties': {
                    'customerId': {'type': 'string', 'example': 'cust_123'},
                    'runnerId': {'type': 'string', 'example': 'runner_456', 'description': 'Optional runner ID.'},
                    'orderId': {'type': 'string', 'example': 'order_789'},
                    'event': {'type': 'string', 'example': 'Manual notification message'}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'Notification record created successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'notification': { '$ref': '#/definitions/Notification' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing fields)'},
        '500': {'description': 'Internal Server Error'}
    },
    # Define Notification schema (simplified example)
    'definitions': {
        'Notification': {
            'type': 'object',
            'properties': {
                'notification_id': {'type': 'string', 'format': 'uuid'},
                'customer_id': {'type': 'string', 'nullable': True},
                'runner_id': {'type': 'string', 'nullable': True},
                'order_id': {'type': 'string', 'nullable': True},
                'event': {'type': 'string', 'description': 'JSON string of the logged event/message'},
                'status': {'type': 'string', 'nullable': True},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'source_topic': {'type': 'string', 'nullable': True},
                'event_type': {'type': 'string', 'nullable': True},
                'correlation_id': {'type': 'string', 'nullable': True},
                'source_service': {'type': 'string', 'nullable': True}
            }
        }
    }
})
def send_notification():
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        customer_id = data.get('customerId')
        runner_id = data.get('runnerId', '')  # May be empty
        order_id = data.get('orderId')
        event = data.get('event')
        
        if not customer_id or not order_id or not event:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Create notification record with metadata
        notification = Notifications(
            notification_id=str(uuid.uuid4()),
            customer_id=customer_id,
            runner_id=runner_id if runner_id not in ('None', 'null', '') else None,
            order_id=order_id,
            event=json.dumps({"message": event}),
            status='sent',
            source_topic='api',
            event_type='notification.manual',
            correlation_id=str(uuid.uuid4()),
            source_service='notification-service-api'
        )
        
        # Save to database
        db.session.add(notification)
        db.session.commit()
        
        # Log the notification creation
        logging.info(f"Created notification for customer {customer_id}, order {order_id}: {event}")
        
        # For backward compatibility - we don't actually publish to Kafka
        # since this service is only consuming Kafka messages
        
        return jsonify({
            'success': True,
            'message': 'Notification created successfully',
            'notification': notification.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating notification: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to create notification: {str(e)}"}), 500

# Kafka consumer function to listen to topics and save events in the notifications database
def consume_kafka_events():
    """
    Kafka consumer function to listen to all events from all services
    and save them in the notifications database
    """
    # Listen to ALL event topics from all services using consistent underscore naming
    topics = [
        "user_events", 
        "order_events", 
        "payment_events", 
        "escrow_events",
        "timer_events",
        "notification_events",
        # Command topics
        "order_commands",
        "user_commands",
        "payment_commands",
        "timer_commands"
    ]
    
    consumer = kafka_client.create_consumer(topics=topics)
    if not consumer:
        logging.error("Failed to create Kafka consumer. Notification service won't receive Kafka events.")
        return
        
    logging.info(f"Kafka consumer thread started. Listening to topics: {topics}")

    try:
        for message in consumer:
            try:
                topic = message.topic
                logging.info(f"Received Kafka message from topic {topic}")
                
                # Parse message value
                message_data = message.value
                if isinstance(message_data, str):
                    try:
                        message_data = json.loads(message_data)
                    except json.JSONDecodeError:
                        message_data = {"event": message_data}
                
                # Extract payload based on message structure
                event_type = message_data.get('type', 'unknown')
                payload = message_data.get('payload', message_data)
                correlation_id = message_data.get('correlation_id', '')
                source_service = message_data.get('source', 'unknown')
                
                # Extract customer, runner, order IDs with fallbacks for different naming conventions
                customer_id = str(payload.get('customer_id', payload.get('customerId', '')))
                runner_id = str(payload.get('runner_id', payload.get('runnerId', '')))
                order_id = str(payload.get('order_id', payload.get('orderId', '')))
                status_ = str(payload.get('status_id', payload.get('statusId', '')))
                
                # Format event information
                event_info = {
                    'topic': topic,
                    'event_type': event_type,
                    'correlation_id': correlation_id,
                    'source_service': source_service,
                    'timestamp': datetime.utcnow().isoformat(),
                    'payload': payload
                }
                
                # Create notification record with additional metadata
                notification = Notifications(
                    customer_id=customer_id if customer_id not in ('None', 'null', '') else '',
                    runner_id=runner_id if runner_id not in ('None', 'null', '') else None,
                    order_id=order_id if order_id not in ('None', 'null', '') else '',
                    event=json.dumps(event_info),
                    status=status_ if status_ not in ('None', 'null', '') else None,
                    source_topic=topic,
                    event_type=event_type,
                    correlation_id=correlation_id,
                    source_service=source_service
                )
                
                try:
                    db.session.add(notification)
                    db.session.commit()
                    logging.info(f"Kafka event from {source_service} (type: {event_type}) saved to notification database")
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Database commit failed: {e}")

            except Exception as e:
                logging.error(f"Error processing Kafka message: {e}")
                logging.error(f"Message content: {message.value}")
    except Exception as e:
        logging.error(f"Critical error in Kafka consumer loop: {e}")
    finally:
        try:
            consumer.close()
            logging.info("Kafka consumer closed.")
        except Exception as e:
            logging.error(f"Error closing Kafka consumer: {e}")


# Endpoint to get the latest status of an order by ID
@api.route('/order/<string:order_id>/latest', methods=['GET'])
@swag_from({
    'tags': ['Notifications'],
    'summary': 'Get the latest notification log entry for an order.',
    'parameters': [
        {
            'name': 'order_id', 'in': 'path', 'type': 'string', 'required': True,
            'description': 'The ID of the order.'
        }
    ],
    'responses': {
        '200': {
            'description': 'Latest notification retrieved.',
            'schema': { '$ref': '#/definitions/Notification' }
        },
        '404': {'description': 'No notifications found for this order.'}
    }
})
def get_latest_status(order_id):
    notification = (
        Notifications.query.filter_by(order_id=order_id)
        .order_by(Notifications.created_at.desc())
        .first()
    )
    
    if notification:
        return jsonify(notification.to_dict()), 200
    else:
        return jsonify({"error": "No notifications found for this order."}), 404

# Endpoint to get all updates for an order by ID
@api.route('/order/<string:order_id>', methods=['GET'])
@swag_from({
    'tags': ['Notifications'],
    'summary': 'Get all notification log entries for an order.',
    'parameters': [
        {
            'name': 'order_id', 'in': 'path', 'type': 'string', 'required': True,
            'description': 'The ID of the order.'
        }
    ],
    'responses': {
        '200': {
            'description': 'List of notifications retrieved.',
            'schema': {
                'type': 'array',
                'items': { '$ref': '#/definitions/Notification' }
            }
        },
        '404': {'description': 'No notifications found for this order.'}
    }
})
def get_all_updates(order_id):
    notifications = (
        Notifications.query.filter_by(order_id=order_id)
        .order_by(Notifications.created_at.asc())
        .all()
    )
    
    if notifications:
        return jsonify([notification.to_dict() for notification in notifications]), 200
    else:
        return jsonify({"error": "No notifications found for this order."}), 404

# Function to start consuming Kafka events in a background thread within app context
def start_kafka_consumer():
    from flask import current_app
    
    print("Starting Kafka consumer thread...")
    
    # Create a thread that runs the consumer with proper app context
    def _consume_with_app_context():
        with current_app.app_context():
            try:
                logging.info("Starting Kafka consumer with application context")
                consume_kafka_events()
            except Exception as e:
                logging.error(f"Critical error in Kafka consumer with context: {e}", exc_info=True)
            
    kafka_thread = threading.Thread(target=_consume_with_app_context, daemon=True)
    kafka_thread.start()
    print("Kafka consumer started.")

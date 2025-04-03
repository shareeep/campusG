from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import threading
from app.models.models import Notifications
from app import db
from app.services.kafka_service import kafka_client
import logging

api = Blueprint('api', __name__)

# Kafka consumer function to listen to topics and save events in the notifications database
def consume_kafka_events():
    topics = ["user-events", "order-events", "payment-events", "escrow-events", "scheduler-events"]
    
    consumer = kafka_client.create_consumer(topics=topics)
    logging.info("Kafka consumer thread started.")

    
    for message in consumer:
        logging.info(f"Received Kafka message: {message.value}")
        try:
            # Parse the message value if it's a string
            if isinstance(message.value, str):
                message_data = json.loads(message.value)
            else:
                message_data = message.value
            
            # Extract payload from the message
            if 'payload' in message_data:
                event_data = message_data['payload']
            else:
                event_data = message_data  # Some messages might not have the payload wrapper
            
            # Parse the event field if it's a string
            event_field = event_data.get('event', '{}')
            if isinstance(event_field, str):
                try:
                    # Try to parse it as JSON
                    parsed_event = json.loads(event_field)
                    # Convert back to string for storage
                    event_field = json.dumps(parsed_event)
                except json.JSONDecodeError:
                    # If not valid JSON, store as is
                    pass
            else:
                # If it's already an object, convert to string
                event_field = json.dumps(event_field)
            
            # Create notification record
            notification = Notifications(
                customer_id=event_data.get('customerId', ''),
                runner_id=event_data.get('runnerId'),
                order_id=event_data.get('orderId', ''),
                event=event_field,
                status=event_data.get('status', 'pending')
            )
            
            db.session.add(notification)
            db.session.commit()
            print(f"Saved notification for order {event_data.get('orderId', '')}")
        except Exception as e:
            print(f"Error processing message: {e}")
            # Print the message for debugging
            print(f"Message: {message.value}")
            continue

# Endpoint to get the latest status of an order by ID
@api.route('/order/<string:order_id>/latest', methods=['GET'])
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

# Function to start consuming Kafka events in a background thread
def start_kafka_consumer():
    print("Starting Kafka consumer thread...")
    kafka_thread = threading.Thread(target=consume_kafka_events, daemon=True)
    kafka_thread.start()
    print("Kafka consumer started.")

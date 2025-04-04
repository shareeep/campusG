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
        try:
            logging.info(f"Received Kafka message: {message.value}")
            
            # Parse message value
            if isinstance(message.value, str):
                message_data = json.loads(message.value)
            else:
                message_data = message.value

            # Extract payload
            event_data = message_data.get('payload', {})
            logging.info(f"Parsed event data: {event_data}")

            # Parse event field
            event_field = event_data.get('event', '{}')
            if isinstance(event_field, str):
                try:
                    event_field = json.dumps(json.loads(event_field))
                except json.JSONDecodeError:
                    pass

            # Create notification record
            notification = Notifications(
                customer_id=event_data.get('customer_id', ''),
                runner_id=event_data.get('runner_id'),
                order_id=event_data.get('order_id', ''),
                event=event_field,
                status=event_data.get('status', 'pending')
            )
            
            try:
                db.session.add(notification)
                db.session.commit()
                logging.info(f"Notification saved successfully for order ID: {event_data.get('order_id', '')}")
            except Exception as e:
                db.session.rollback()
                logging.error(f"Database commit failed: {e}")

        except Exception as e:
            logging.error(f"Error processing Kafka message: {e}")
            logging.error(f"Message content: {message.value}")


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

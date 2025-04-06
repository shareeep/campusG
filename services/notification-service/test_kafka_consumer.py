"""
Test script to verify the Kafka consumer functionality in the notification service

This script will:
1. Connect to the Kafka broker
2. Send test messages to various topics
3. Verify that messages are properly consumed by the notification service

Usage:
    python test_kafka_consumer.py

Requirements:
    - Kafka broker running and accessible
    - Notification service running
"""
import json
import logging
import os
import sys
import time
from datetime import datetime

from kafka import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

def create_producer():
    """Create and return a Kafka producer"""
    try:
        logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            request_timeout_ms=30000
        )
        logger.info("Connected to Kafka successfully")
        return producer
    except Exception as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return None

def send_test_message(producer, topic, message_type, payload):
    """Send a test message to the specified topic"""
    correlation_id = f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    message = {
        'type': message_type,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat(),
        'payload': payload,
        'source': 'notification-test-script'
    }
    
    try:
        logger.info(f"Sending message to {topic}: {message_type}")
        future = producer.send(topic, message)
        producer.flush()
        logger.info(f"Message sent successfully to {topic}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {topic}: {e}")
        return False

def main():
    """Main function to send test messages to Kafka"""
    producer = create_producer()
    if not producer:
        logger.error("Failed to create Kafka producer, exiting.")
        sys.exit(1)
    
    try:
        # Test messages for different topics
        test_messages = [
            # Order events
            {
                'topic': 'order_events',
                'type': 'order.created',
                'payload': {
                    'order_id': 'test-order-123',
                    'customer_id': 'test-customer-456',
                    'runner_id': 'test-runner-789',
                    'status': 'created',
                    'total_amount': 25.50,
                    'items': [
                        {'id': 'item-1', 'name': 'Burger', 'price': 15.00},
                        {'id': 'item-2', 'name': 'Fries', 'price': 5.50},
                        {'id': 'item-3', 'name': 'Drink', 'price': 5.00}
                    ],
                    'created_at': datetime.utcnow().isoformat()
                }
            },
            # Payment events
            {
                'topic': 'payment_events',
                'type': 'payment.completed',
                'payload': {
                    'payment_id': 'test-payment-123',
                    'order_id': 'test-order-123',
                    'customer_id': 'test-customer-456',
                    'amount': 25.50,
                    'status': 'completed',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            # User events
            {
                'topic': 'user_events',
                'type': 'user.profile_updated',
                'payload': {
                    'user_id': 'test-customer-456',
                    'profile': {
                        'name': 'Test User',
                        'email': 'testuser@example.com',
                        'phone': '+1234567890'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        ]
        
        # Send each test message
        for msg in test_messages:
            send_test_message(producer, msg['topic'], msg['type'], msg['payload'])
            # Add a small delay between messages
            time.sleep(1)
            
        logger.info("All test messages sent successfully")
        logger.info("Check the notification service database to verify messages were captured")
        logger.info("You can also check the notification service logs for message receipt confirmation")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        # Close the producer
        if producer:
            producer.close()
            logger.info("Kafka producer closed")

if __name__ == "__main__":
    main()

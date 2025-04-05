#!/usr/bin/env python3
"""
Notification Service Kafka Integration Test

This script tests the end-to-end integration between a service sending messages 
to Kafka and the notification service capturing those messages.

It:
1. Sends a test message to Kafka from a simulated service
2. Checks the notification service database to verify the message was captured
3. Reports success or failure with detailed diagnostics

Usage:
    python test_notification_kafka_integration.py

Requirements:
    - Kafka broker running and accessible
    - Notification service running and properly configured
    - Access to the notification service database
"""
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime

from kafka import KafkaProducer
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
# Inside docker container, use localhost:3000 (container's internal port)
# 3006 is only the external port mapping
NOTIFICATION_SERVICE_URL = os.getenv('NOTIFICATION_SERVICE_URL', 'http://localhost:3000')
DB_CONNECTION_STRING = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@notification-db:5432/notification_db'
)
WAIT_SECONDS = int(os.getenv('WAIT_SECONDS', '10'))  # Time to wait for notification service to process

def create_kafka_producer():
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

def get_db_connection():
    """Connect to the notification service database"""
    try:
        logger.info(f"Connecting to database with {DB_CONNECTION_STRING}...")
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        logger.info("Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def send_test_message(producer, service_name="order-service"):
    """
    Send a test message to Kafka simulating a message from another service
    Returns the correlation ID for later verification
    """
    # Generate unique IDs for the test
    correlation_id = str(uuid.uuid4())
    order_id = f"test-order-{uuid.uuid4().hex[:8]}"
    customer_id = f"test-customer-{uuid.uuid4().hex[:8]}"
    
    # Create message payload
    timestamp = datetime.utcnow().isoformat()
    payload = {
        'order_id': order_id,
        'customer_id': customer_id,
        'status': 'created',
        'items': [
            {'id': 'item-1', 'name': 'Test Item', 'price': 15.99},
        ],
        'total_amount': 15.99,
        'created_at': timestamp
    }
    
    # Create full message structure
    message = {
        'type': 'order.created',
        'correlation_id': correlation_id,
        'timestamp': timestamp,
        'payload': payload,
        'source': service_name
    }
    
    # Choose topic (use both naming conventions to test)
    topic = 'order_events'  # Could also use 'order-events'
    
    try:
        logger.info(f"Sending test message to topic '{topic}'")
        logger.debug(f"Message details: {json.dumps(message, indent=2)}")
        future = producer.send(topic, message)
        producer.flush()
        logger.info(f"Message sent successfully to {topic}")
        return {
            'correlation_id': correlation_id,
            'order_id': order_id,
            'customer_id': customer_id,
            'topic': topic
        }
    except Exception as e:
        logger.error(f"Failed to send message to {topic}: {e}")
        return None

def check_notification_service_health():
    """Verify the notification service is running"""
    try:
        response = requests.get(f"{NOTIFICATION_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("Notification service is healthy")
            return True
        else:
            logger.error(f"Notification service health check failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to connect to notification service: {e}")
        return False

def verify_message_capture(conn, message_info):
    """
    Check the notification service database to verify the message was captured
    Returns the captured notification record or None if not found
    """
    if not conn:
        logger.error("No database connection available")
        return None
        
    correlation_id = message_info['correlation_id']
    order_id = message_info['order_id']
    
    # Wait for notification service to process the message
    logger.info(f"Waiting {WAIT_SECONDS} seconds for notification service to process message...")
    time.sleep(WAIT_SECONDS)
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query by correlation ID (most reliable)
        cursor.execute(
            "SELECT * FROM notifications WHERE correlation_id = %s",
            (correlation_id,)
        )
        notification = cursor.fetchone()
        
        if notification:
            logger.info(f"Found notification with correlation ID: {correlation_id}")
            return notification
            
        # Fallback: query by order ID
        cursor.execute(
            "SELECT * FROM notifications WHERE order_id = %s ORDER BY created_at DESC",
            (order_id,)
        )
        notification = cursor.fetchone()
        
        if notification:
            logger.info(f"Found notification with order ID: {order_id}")
            return notification
            
        logger.error(f"No notification found for correlation ID {correlation_id} or order ID {order_id}")
        
        # Debug: Show all recent notifications
        cursor.execute(
            "SELECT notification_id, correlation_id, order_id, event_type, source_topic, created_at FROM notifications ORDER BY created_at DESC LIMIT 5"
        )
        recent_notifications = cursor.fetchall()
        
        if recent_notifications:
            logger.info("Recent notifications in the database:")
            for n in recent_notifications:
                logger.info(f"  {n['created_at']}: {n['event_type']} (correlation_id: {n['correlation_id']}, order_id: {n['order_id']})")
        else:
            logger.warning("No recent notifications found in the database")
            
        return None
        
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return None
    finally:
        cursor.close()

def main():
    """Main test function"""
    success = False
    
    try:
        # Step 1: Verify notification service is running
        if not check_notification_service_health():
            logger.error("Test failed: Notification service is not healthy")
            return False
            
        # Step 2: Create Kafka producer
        producer = create_kafka_producer()
        if not producer:
            logger.error("Test failed: Could not connect to Kafka")
            return False
            
        # Step 3: Connect to the database
        conn = get_db_connection()
        if not conn:
            logger.error("Test failed: Could not connect to database")
            producer.close()
            return False
            
        try:
            # Step 4: Send test message
            message_info = send_test_message(producer)
            if not message_info:
                logger.error("Test failed: Could not send test message")
                return False
                
            # Step 5: Verify message was captured
            notification = verify_message_capture(conn, message_info)
            
            if notification:
                logger.info("🎉 TEST PASSED! 🎉")
                logger.info("The notification service successfully captured the Kafka message")
                
                # Show full notification details
                logger.info("Captured notification details:")
                for key, value in notification.items():
                    if key == 'event':
                        try:
                            event_data = json.loads(value)
                            logger.info(f"  {key}: {json.dumps(event_data, indent=2)}")
                        except:
                            logger.info(f"  {key}: {value}")
                    else:
                        logger.info(f"  {key}: {value}")
                
                success = True
            else:
                logger.error("❌ TEST FAILED! ❌")
                logger.error("The notification service did not capture the message")
                success = False
                
            return success
            
        finally:
            if producer:
                producer.close()
            if conn:
                conn.close()
                
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

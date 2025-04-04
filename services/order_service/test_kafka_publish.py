#!/usr/bin/env python
"""
Test script to publish a message to Kafka from the order service.
This helps verify that messages are being properly published to the order_events topic
and can be received by the create-order-saga-orchestrator.
"""

import os
import json
import logging
import time
from datetime import datetime

from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
ORDER_EVENTS_TOPIC = 'order_events'

def main():
    # Create producer
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("Connected to Kafka successfully")
        
        # Create test order event message
        correlation_id = f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        test_order = {
            "order_id": "test-order-123",
            "customer_id": "test-customer-456",
            "restaurant_id": "test-restaurant-789",
            "items": [
                {"item_id": "item-1", "name": "Burger", "quantity": 2, "price": 5.99},
                {"item_id": "item-2", "name": "Fries", "quantity": 1, "price": 2.99}
            ],
            "total_price": 14.97,
            "status": "CREATED",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Format message according to expected structure
        message = {
            'type': 'order.created',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': test_order,
            'source': 'order-service'
        }
        
        # Publish message
        logger.info(f"Publishing test message to {ORDER_EVENTS_TOPIC} with correlation_id {correlation_id}...")
        logger.info(f"Message content: {json.dumps(message, indent=2)}")
        
        producer.send(ORDER_EVENTS_TOPIC, message)
        producer.flush()
        logger.info("Message sent successfully")
        
        # Wait a moment to ensure message is processed
        time.sleep(2)
        
    except Exception as e:
        logger.error(f"Error in Kafka test: {e}", exc_info=True)
    finally:
        if 'producer' in locals():
            producer.close()
            logger.info("Kafka producer closed")

if __name__ == "__main__":
    main()

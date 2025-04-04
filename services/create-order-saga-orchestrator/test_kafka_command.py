#!/usr/bin/env python
"""
Test script to publish a command message from the create-order-saga-orchestrator to the order service.
This helps verify that commands are being properly published to the order_commands topic
and can be received by the order service.
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
ORDER_COMMANDS_TOPIC = 'order_commands'

def main():
    # Create producer
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("Connected to Kafka successfully")
        
        # Create test command message
        correlation_id = f"test-saga-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create an update order status command
        command_payload = {
            "order_id": "test-order-123",
            "status": "CONFIRMED",
            "update_timestamp": datetime.utcnow().isoformat()
        }
        
        # Format message according to expected structure
        message = {
            'type': 'update_order_status',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': command_payload,
            'source': 'create-order-saga-orchestrator'
        }
        
        # Publish message
        logger.info(f"Publishing test command to {ORDER_COMMANDS_TOPIC} with correlation_id {correlation_id}...")
        logger.info(f"Command content: {json.dumps(message, indent=2)}")
        
        producer.send(ORDER_COMMANDS_TOPIC, message)
        producer.flush()
        logger.info("Command sent successfully")
        
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

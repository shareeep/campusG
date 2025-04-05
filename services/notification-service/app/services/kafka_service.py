import json
import logging
import os
import threading
import time
from datetime import datetime

from kafka import KafkaConsumer

logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
CONSUMER_GROUP_ID = 'notification-service-group'  # Unique consumer group ID

class KafkaClient:
    """Kafka client for the Notification Service - Consumer only implementation"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating KafkaClient instance")
            cls._instance = super(KafkaClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info("Initializing KafkaClient")
        self.bootstrap_servers = KAFKA_BOOTSTRAP_SERVERS
        self._initialized = True
        logger.info("KafkaClient initialized")

    def create_consumer(self, topics):
        """
        Create a Kafka consumer for the specified topics
        
        Args:
            topics: List of topics to subscribe to
            
        Returns:
            KafkaConsumer: Configured Kafka consumer or None if failed
        """
        if not self.bootstrap_servers:
            logger.warning("KAFKA_BOOTSTRAP_SERVERS not set. Cannot create consumer.")
            return None

        try:
            logger.info(f"Creating Kafka consumer for topics {topics} with group ID {CONSUMER_GROUP_ID}...")
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                enable_auto_commit=True,
                consumer_timeout_ms=1000  # Poll timeout
            )
            logger.info(f"Kafka consumer created successfully for topics {topics}")
            return consumer
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer for topics {topics}: {e}", exc_info=True)
            return None

    def publish(self, topic, message):
        """
        Dummy publish method to maintain compatibility with existing code
        This method is kept for backward compatibility only
        """
        logger.warning("publish() called, but this KafkaClient implementation is consumer-only")
        return True

    def close(self):
        """Placeholder close method (actual consumer closing happens in the consumer loop)"""
        logger.info("KafkaClient closing - note: consumers must be closed in their respective threads")

# Global Kafka client instance
kafka_client = KafkaClient()

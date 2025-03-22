import json
from datetime import datetime
from flask import current_app
import kafka
from kafka import KafkaProducer

class KafkaClient:
    """Kafka client for publishing events to Kafka topics"""
    
    def __init__(self, bootstrap_servers=None):
        """
        Initialize the Kafka client
        
        Args:
            bootstrap_servers (str, optional): Comma-separated list of Kafka broker addresses
        """
        self.bootstrap_servers = bootstrap_servers or current_app.config.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self._producer = None
    
    @property
    def producer(self):
        """Lazy-loaded KafkaProducer instance"""
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'  # Wait for all replicas to acknowledge
            )
        return self._producer
    
    def publish(self, topic, message):
        """
        Publish a message to a Kafka topic
        
        Args:
            topic (str): The Kafka topic to publish to
            message (dict): The message to publish
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add timestamp if not present
            if isinstance(message, dict) and 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow().isoformat()
                
            # Send message
            future = self.producer.send(topic, message)
            self.producer.flush()  # Ensure message is sent
            
            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)
            
            current_app.logger.debug(
                f"Published message to {topic} - Partition: {record_metadata.partition}, Offset: {record_metadata.offset}"
            )
            
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to publish message to {topic}: {str(e)}")
            return False
    
    def close(self):
        """Close the producer connection"""
        if self._producer:
            self._producer.close()
            self._producer = None

# Global Kafka client instance
kafka_client = KafkaClient()

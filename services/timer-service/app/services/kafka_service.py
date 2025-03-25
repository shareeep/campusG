from kafka import KafkaProducer
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class KafkaClient:
    """Kafka client for publishing events"""
    
    def __init__(self, bootstrap_servers=None):
        """Initialize the Kafka producer"""
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        
        # Try to connect to Kafka
        self._connect()
    
    def _connect(self):
        """Connect to Kafka"""
        if not self.bootstrap_servers:
            logger.warning("No Kafka bootstrap servers provided")
            return
            
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            self.producer = None
    
    def publish(self, topic, message):
        """Publish a message to Kafka"""
        # No-op if no producer
        if not self.producer:
            logger.warning(f"No Kafka producer available. Message not sent to {topic}")
            return False
            
        # Add timestamp if not present
        if isinstance(message, dict) and 'timestamp' not in message:
            message['timestamp'] = datetime.utcnow().isoformat()
        
        # Try to publish
        try:
            self.producer.send(topic, message)
            logger.info(f"Published message to {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {str(e)}")
            return False
    
    def close(self):
        """Close the Kafka producer"""
        if self.producer:
            self.producer.close()

# Global client instance
kafka_client = None

def init_kafka(app):
    """Initialize kafka client with app config"""
    global kafka_client
    kafka_client = KafkaClient(app.config.get('KAFKA_BOOTSTRAP_SERVERS'))
    return kafka_client

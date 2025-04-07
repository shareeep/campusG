from kafka import KafkaProducer, KafkaConsumer
import json
import logging
import uuid
import threading
import time
from datetime import datetime

from app.config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    COMPLETE_ORDER_COMMANDS_TOPIC,
    COMPLETE_ORDER_EVENTS_TOPIC,
    CONSUMER_GROUP_ID
)

logger = logging.getLogger(__name__)

class CompleteOrderKafkaClient:
    """Kafka client for publishing commands and consuming events for the Complete Order Saga."""
    
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        self.event_handlers = {}
        self._connect()
    
    def _connect(self):
        """Connect to Kafka by creating a producer and consumer."""
        if not self.bootstrap_servers:
            logger.warning("No Kafka bootstrap servers provided.")
            return
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
            
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            logger.info(f"Created Kafka consumer with group ID {CONSUMER_GROUP_ID}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            self.producer = None
            self.consumer = None
    
    def publish_command(self, topic, command_type, payload, correlation_id=None):
        """Publish a command message to Kafka."""
        if not self.producer:
            logger.warning(f"No Kafka producer available. Command {command_type} not sent to {topic}")
            return False, None
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        message = {
            'type': command_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload
        }
        
        try:
            self.producer.send(topic, message)
            self.producer.flush()  # Ensure the message is sent
            logger.info(f"Published command {command_type} to {topic} with correlation_id {correlation_id}")
            return True, correlation_id
        except Exception as e:
            logger.error(f"Failed to publish command to {topic}: {str(e)}")
            return False, None
    
    def register_event_handler(self, event_type, handler_function):
        """Register a handler for a specific event type."""
        self.event_handlers[event_type] = handler_function
        logger.info(f"Registered handler for event type: {event_type}")
    
    def subscribe_to_events(self, topics):
        """Subscribe to Kafka topics for events."""
        if not self.consumer:
            logger.warning("No Kafka consumer available. Cannot subscribe to topics.")
            return False
        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {str(e)}")
            return False
    
    def start_consuming(self):
        """Start consuming messages in a background thread."""
        if not self.consumer:
            logger.warning("No Kafka consumer available. Cannot start consuming.")
            return False
        
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_loop)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        logger.info("Kafka consumer started in background thread")
        return True
    
    def _consume_loop(self):
        """Main loop for consuming messages."""
        while self.running:
            try:
                message_batch = self.consumer.poll(timeout_ms=1000)
                for tp, messages in message_batch.items():
                    for message in messages:
                        self._process_message(message)
            except Exception as e:
                logger.error(f"Error in Kafka consumer loop: {str(e)}")
                time.sleep(1)
    
    def _process_message(self, message):
        """Process a received Kafka message."""
        try:
            event_type = message.value.get('type')
            correlation_id = message.value.get('correlation_id')
            payload = message.value.get('payload', {})
            
            logger.info(f"Received event {event_type} with correlation_id {correlation_id}")
            
            handler = self.event_handlers.get(event_type)
            if handler:
                threading.Thread(target=handler, args=(correlation_id, payload)).start()
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def stop_consuming(self):
        """Stop the consumer loop."""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5.0)
            logger.info("Kafka consumer stopped")
    
    def close(self):
        """Close Kafka connections."""
        self.stop_consuming()
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

# Global instance for the Complete Order Saga Kafka client
complete_order_kafka_client = CompleteOrderKafkaClient()

# Convenience methods for publishing commands specific to the Complete Order Saga
def publish_complete_order_command(order_data, correlation_id=None):
    """Publish a command to update the order status as part of order completion."""
    return complete_order_kafka_client.publish_command(
        COMPLETE_ORDER_COMMANDS_TOPIC,
        'complete_order',
        order_data,
        correlation_id
    )

def init_complete_order_kafka():
    """Initialize the Kafka client for the Complete Order Saga.
    
    Returns:
        CompleteOrderKafkaClient: The initialized Kafka client.
    """
    global complete_order_kafka_client
    topics = [COMPLETE_ORDER_EVENTS_TOPIC]
    complete_order_kafka_client.subscribe_to_events(topics)
    complete_order_kafka_client.start_consuming()
    logger.info("Complete Order Kafka client initialized")
    return complete_order_kafka_client

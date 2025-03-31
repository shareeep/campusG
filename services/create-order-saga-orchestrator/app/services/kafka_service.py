from kafka import KafkaProducer, KafkaConsumer
import json
from datetime import datetime
import logging
import uuid
import threading
import time

from app.config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    ORDER_COMMANDS_TOPIC,
    PAYMENT_COMMANDS_TOPIC,
    TIMER_COMMANDS_TOPIC,
    USER_COMMANDS_TOPIC,
    ORDER_EVENTS_TOPIC,
    PAYMENT_EVENTS_TOPIC,
    TIMER_EVENTS_TOPIC,
    USER_EVENTS_TOPIC,
    CONSUMER_GROUP_ID
)

logger = logging.getLogger(__name__)

class KafkaClient:
    """Kafka client for publishing commands and consuming events"""
    
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        """Initialize the Kafka client"""
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        
        # Event handlers by message type
        self.event_handlers = {}
        
        # Try to connect to Kafka
        self._connect()
    
    def _connect(self):
        """Connect to Kafka"""
        if not self.bootstrap_servers:
            logger.warning("No Kafka bootstrap servers provided")
            return
            
        try:
            # Create producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
            
            # Create consumer
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
        """Publish a command message to Kafka"""
        # No-op if no producer
        if not self.producer:
            logger.warning(f"No Kafka producer available. Command {command_type} not sent to {topic}")
            return False, None
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Create the message structure
        message = {
            'type': command_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload
        }
        
        # Try to publish
        try:
            self.producer.send(topic, message)
            self.producer.flush()  # Ensure message is sent
            logger.info(f"Published command {command_type} to {topic} with correlation_id {correlation_id}")
            return True, correlation_id
        except Exception as e:
            logger.error(f"Failed to publish command to {topic}: {str(e)}")
            return False, None
    
    def register_event_handler(self, event_type, handler_function):
        """Register a handler for a specific event type"""
        self.event_handlers[event_type] = handler_function
        logger.info(f"Registered handler for event type: {event_type}")
    
    def subscribe_to_events(self, topics):
        """Subscribe to Kafka topics for events"""
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
        """Start consuming messages in a background thread"""
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
        """Main loop for consuming messages"""
        while self.running:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for tp, messages in message_batch.items():
                    for message in messages:
                        self._process_message(message)
                        
            except Exception as e:
                logger.error(f"Error in Kafka consumer loop: {str(e)}")
                time.sleep(1)  # Avoid tight loop in case of repeated errors
    
    def _process_message(self, message):
        """Process a received Kafka message"""
        try:
            # Extract message data
            event_type = message.value.get('type')
            correlation_id = message.value.get('correlation_id')
            payload = message.value.get('payload', {})
            
            logger.info(f"Received event {event_type} from {message.topic} with correlation_id {correlation_id}")
            
            # Find and execute the appropriate handler
            handler = self.event_handlers.get(event_type)
            if handler:
                logger.debug(f"Executing handler for {event_type}")
                threading.Thread(target=handler, args=(correlation_id, payload)).start()
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def stop_consuming(self):
        """Stop the consumer loop"""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5.0)
            logger.info("Kafka consumer stopped")
    
    def close(self):
        """Close Kafka connections"""
        self.stop_consuming()
        
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
        
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


# Global instance
kafka_client = KafkaClient()

# Convenience methods for specific command types

def publish_create_order_command(kafka_service, order_data, correlation_id=None):
    """Publish a command to create an order"""
    return kafka_service.publish_command(
        ORDER_COMMANDS_TOPIC,
        'create_order',
        order_data,
        correlation_id
    )

def publish_get_user_payment_info_command(kafka_service, user_id, correlation_id=None):
    """Publish a command to retrieve user payment information"""
    return kafka_service.publish_command(
        USER_COMMANDS_TOPIC,
        'get_payment_info',
        {'user_id': user_id},
        correlation_id
    )

def publish_authorize_payment_command(kafka_service, payment_data, correlation_id=None):
    """Publish a command to authorize payment"""
    return kafka_service.publish_command(
        PAYMENT_COMMANDS_TOPIC,
        'authorize_payment',
        payment_data,
        correlation_id
    )

def publish_update_order_status_command(kafka_service, order_id, status, correlation_id=None):
    """Publish a command to update order status"""
    return kafka_service.publish_command(
        ORDER_COMMANDS_TOPIC,
        'update_order_status',
        {'order_id': order_id, 'status': status},
        correlation_id
    )

def publish_start_timer_command(kafka_service, timer_data, correlation_id=None):
    """Publish a command to start an order timeout timer"""
    return kafka_service.publish_command(
        TIMER_COMMANDS_TOPIC,
        'start_order_timer',
        timer_data,
        correlation_id
    )

def init_kafka():
    """Initialize the Kafka client
    
    Returns:
        KafkaClient: The Kafka client instance
    """
    global kafka_client
    
    # Ensure topics exist
    event_topics = [ORDER_EVENTS_TOPIC, PAYMENT_EVENTS_TOPIC, TIMER_EVENTS_TOPIC, USER_EVENTS_TOPIC]
    kafka_client.subscribe_to_events(event_topics)
    kafka_client.start_consuming()
    
    logger.info("Kafka client initialization completed")
    return kafka_client

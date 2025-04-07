import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime

from flask import Flask
from kafka import KafkaConsumer, KafkaProducer

logger = logging.getLogger(__name__)

# Kafka Configuration (adjust topic names and group ID as needed)
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
PAYMENT_COMMANDS_TOPIC = 'payment_commands'  # Topic to consume commands from
PAYMENT_EVENTS_TOPIC = 'payment_events'      # Topic to publish events to
CONSUMER_GROUP_ID = 'payment-service-group' # Unique consumer group ID

class KafkaService:
    """Kafka client for the Payment Service"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating KafkaService instance")
            cls._instance = super(KafkaService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info("Initializing KafkaService")
        self.bootstrap_servers = KAFKA_BOOTSTRAP_SERVERS
        self.producer = None
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        self.command_handlers = {} # Handlers for incoming commands
        self.app = None  # Add this line to store Flask app
        self._connect()
        self._initialized = True
        logger.info("KafkaService initialized")


    def _connect(self):
        """Connect to Kafka brokers."""
        if not self.bootstrap_servers:
            logger.warning("KAFKA_BOOTSTRAP_SERVERS not set. Kafka client disabled.")
            return

        try:
            logger.info(f"Attempting to connect Kafka producer to {self.bootstrap_servers}...")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=5, # Retry connecting
                request_timeout_ms=30000 # Increase timeout
            )
            logger.info("Kafka producer connected successfully.")

            logger.info(f"Attempting to connect Kafka consumer to {self.bootstrap_servers} with group ID {CONSUMER_GROUP_ID}...")
            self.consumer = KafkaConsumer(
                PAYMENT_COMMANDS_TOPIC, # Subscribe only to the commands topic
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000 # Poll timeout
            )
            logger.info(f"Kafka consumer connected and subscribed to {PAYMENT_COMMANDS_TOPIC}.")

        except Exception as e:
            logger.error(f"Failed to connect to Kafka at {self.bootstrap_servers}: {e}", exc_info=True)
            self.producer = None
            self.consumer = None

    def publish_event(self, event_type, payload, correlation_id):
        """Publish an event message to the PAYMENT_EVENTS_TOPIC."""
        if not self.producer:
            logger.warning(f"No Kafka producer available. Event {event_type} not sent.")
            return False

        if not correlation_id:
            logger.error("Cannot publish event without correlation_id.")
            return False

        message = {
            'type': event_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload,
            'source': 'payment-service' # Identify the source service
        }

        try:
            logger.info(f"Publishing event {event_type} to {PAYMENT_EVENTS_TOPIC} with correlation_id {correlation_id}")
            future = self.producer.send(PAYMENT_EVENTS_TOPIC, message)
            # Wait for send confirmation (optional, adds latency but ensures delivery)
            # result = future.get(timeout=10)
            # logger.info(f"Event {event_type} published successfully to partition {result.partition} offset {result.offset}")
            self.producer.flush() # Ensure message is sent
            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} to {PAYMENT_EVENTS_TOPIC}: {e}", exc_info=True)
            return False

    def register_command_handler(self, command_type, handler_function):
        """Register a handler for a specific command type."""
        self.command_handlers[command_type] = handler_function
        logger.info(f"Registered handler for command type: {command_type}")

    def start_consuming(self):
        """Start consuming command messages in a background thread."""
        if not self.consumer:
            logger.warning("No Kafka consumer available. Cannot start consuming.")
            return False
        if self.running:
            logger.warning("Consumer already running.")
            return True

        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.consumer_thread.start()
        logger.info(f"Kafka consumer started in background thread, listening on {PAYMENT_COMMANDS_TOPIC}.")
        return True

    def _consume_loop(self):
        """Main loop for consuming command messages."""
        logger.info("Consumer loop started.")
        while self.running:
            try:
                # Poll for messages
                # The consumer is already subscribed during initialization
                for message in self.consumer:
                    if not self.running:
                        break
                    self._process_message(message)

            except Exception as e:
                logger.error(f"Error in Kafka consumer loop: {e}", exc_info=True)
                # Avoid tight loop on persistent errors
                time.sleep(5)
        logger.info("Consumer loop stopped.")


    def _process_message(self, message):
        """Process a received Kafka command message."""
        try:
            command_data = message.value
            
            # Fix for string messages - add this block
            if isinstance(command_data, str):
                try:
                    command_data = json.loads(command_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON message from {message.topic}: {command_data[:100]}...")
                    logger.error(f"JSON decode error: {str(e)}")
                    return
            
            # Now command_data should be a dictionary
            command_type = command_data.get('type')
            correlation_id = command_data.get('correlation_id')
            payload = command_data.get('payload', {})

            if not command_type or not correlation_id:
                logger.warning(f"Received invalid message structure on {message.topic}: {command_data}")
                return

            logger.info(f"Received command {command_type} from {message.topic} with correlation_id {correlation_id}")

            handler = self.command_handlers.get(command_type)
            if handler:
                logger.debug(f"Executing handler for {command_type} (correlation_id: {correlation_id})")
                # Run handler in a separate thread with app context
                thread = threading.Thread(
                    target=self._run_handler_with_app_context, 
                    args=(handler, correlation_id, payload)
                )
                thread.start()
            else:
                logger.warning(f"No handler registered for command type: {command_type}")

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message from {message.topic}: {message.value}")
        except Exception as e:
            logger.error(f"Error processing message from {message.topic}: {e}", exc_info=True)

    def stop_consuming(self):
        """Stop the consumer loop."""
        if not self.running:
            return
        logger.info("Stopping Kafka consumer...")
        self.running = False
        if self.consumer:
             # Wake up consumer to exit loop if it's blocking on poll
             # This might not be strictly necessary with kafka-python's consumer_timeout_ms
             pass
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5.0)
            if self.consumer_thread.is_alive():
                logger.warning("Consumer thread did not exit cleanly.")
        logger.info("Kafka consumer stopped.")


    def _run_handler_with_app_context(self, handler, correlation_id, payload):
        """Execute handler function within app context."""
        if not self.app:
            logger.error("Cannot run handler with app context: Flask app not set")
            return
            
        with self.app.app_context():
            try:
                handler(correlation_id, payload)
            except Exception as e:
                logger.error(f"Error in handler execution: {e}", exc_info=True)

    def close(self):
        """Close Kafka connections."""
        logger.info("Closing Kafka service connections...")
        self.stop_consuming()

        if self.producer:
            try:
                self.producer.close(timeout=5)
                logger.info("Kafka producer closed.")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}", exc_info=True)
            self.producer = None

        if self.consumer:
            try:
                # Closing the consumer implicitly unsubscribes and leaves the group
                self.consumer.close()
                logger.info("Kafka consumer closed.")
            except Exception as e:
                logger.error(f"Error closing Kafka consumer: {e}", exc_info=True)
            self.consumer = None
        logger.info("Kafka service connections closed.")


# --- Convenience methods for publishing specific payment events ---

def publish_payment_authorized_event(kafka_service, correlation_id, payload):
    """Publish a payment.authorized event."""
    return kafka_service.publish_event(
        'payment.authorized',
        payload,
        correlation_id
    )

def publish_payment_failed_event(kafka_service, correlation_id, error_payload):
    """Publish a payment.failed event."""
    return kafka_service.publish_event(
        'payment.failed',
        error_payload, # Should contain reason for failure
        correlation_id
    )

def publish_payment_released_event(kafka_service, correlation_id, payload):
    """Publish a payment.released event."""
    return kafka_service.publish_event(
        'payment.released',
        payload,
        correlation_id
    )

# --- Initialization ---

# Global instance (using singleton pattern via __new__)
kafka_client = KafkaService()

def init_kafka(app):
    """Initialize the Kafka client and start consuming."""
    global kafka_client
    if not kafka_client.producer or not kafka_client.consumer:
        logger.warning("Kafka client not fully connected during init_kafka. Will rely on lazy connection.")
        # Attempt to reconnect or rely on lazy connection within methods
        kafka_client._connect() # Try connecting again

    if kafka_client.consumer:
        # Register command handlers here (or preferably in the main app setup)
        # Example: from app.services.payment_processing import handle_authorize_payment_command
        # kafka_client.register_command_handler('authorize_payment', handle_authorize_payment_command)

        kafka_client.start_consuming()
    else:
        logger.error("Cannot start Kafka consumer - connection failed during initialization.")
    
    # We'll handle shutdown in a signal handler rather than app context teardown
    # to prevent Kafka connections from closing during normal app context exits
    import signal
    def handle_shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down Kafka client.")
        kafka_client.close()
        
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("Kafka client initialization sequence completed.")
    return kafka_client

import json
import os
import threading
import logging
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from datetime import datetime, timezone
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Kafka Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')
USER_COMMANDS_TOPIC = os.environ.get('KAFKA_USER_COMMANDS_TOPIC', 'user_commands')
USER_EVENTS_TOPIC = os.environ.get('KAFKA_USER_EVENTS_TOPIC', 'user_events')
CONSUMER_GROUP_ID = os.environ.get('KAFKA_USER_SERVICE_GROUP_ID', 'user-service-group')
RETRY_DELAY_SECONDS = 5 # Delay before retrying connection

class KafkaService:
    """Manages Kafka Producer and Consumer for User Service using kafka-python"""

    def __init__(self, app=None):
        self._producer = None
        self._consumer = None
        self._consumer_thread = None
        self._running = False
        self._lock = threading.Lock()
        self.app = app # Store Flask app context if provided

    def _init_producer(self):
        """Initializes the Kafka producer instance."""
        while self._running and self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    client_id='user-service-producer',
                    retries=5, # Retry sending messages
                    acks='all' # Wait for all replicas to acknowledge
                )
                logger.info("Kafka Producer initialized successfully.")
                return True
            except NoBrokersAvailable:
                logger.error(f"Kafka Producer: No brokers available at {KAFKA_BOOTSTRAP_SERVERS}. Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
            except Exception as e:
                logger.error(f"Failed to initialize Kafka Producer: {e}. Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)
        return False

    def get_producer(self):
        """Returns the Kafka producer instance, initializing if needed."""
        if self._producer is None:
            with self._lock:
                if self._producer is None:
                    # Attempt initialization directly if called outside the running service
                    if not self._running:
                         self._init_producer()
                    else:
                        # If called within the running service, initialization happens in start()
                        logger.warning("Producer accessed before start() finished initialization.")
        return self._producer

    def publish(self, topic, message_data):
        """Publishes a message to the specified Kafka topic."""
        producer = self.get_producer()
        if not producer:
            logger.error("Producer not available. Cannot publish message.")
            return False

        try:
            future = producer.send(topic, value=message_data)
            # Optional: Block for confirmation (can impact performance)
            # result = future.get(timeout=10)
            # logger.debug(f"Message sent to {result.topic} partition {result.partition} offset {result.offset}")
            logger.info(f"Published message to topic {topic}: Type {message_data.get('type', 'N/A')}")
            producer.flush() # Ensure message is sent
            return True
        except KafkaError as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            # Consider re-initializing producer on certain errors
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing message to {topic}: {e}")
            return False

    def _consume_loop(self):
        """The main loop for the Kafka consumer."""
        consumer = None
        while self._running:
            try:
                if consumer is None:
                    logger.info(f"Attempting to connect Kafka Consumer to {KAFKA_BOOTSTRAP_SERVERS}...")
                    # Define a safer deserializer that won't crash on bad JSON
                    def safe_deserializer(data):
                        try:
                            if data is None:
                                return None
                            return json.loads(data.decode('utf-8'))
                        except json.JSONDecodeError as e:
                            logger.error(f"Could not decode message: {e} - Raw data: {data[:50]}...")
                            return None  # Return None for messages that can't be parsed
                        except Exception as e:
                            logger.error(f"Error in deserializer: {e}")
                            return None
                    
                    consumer = KafkaConsumer(
                        USER_COMMANDS_TOPIC,
                        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                        group_id=CONSUMER_GROUP_ID,
                        value_deserializer=safe_deserializer,
                        auto_offset_reset='latest',  # Switch to latest to avoid old bad messages
                        enable_auto_commit=False, # Commit manually
                        consumer_timeout_ms=1000 # Poll timeout
                    )
                    self._consumer = consumer # Store reference
                    logger.info(f"Kafka Consumer subscribed to topic: {USER_COMMANDS_TOPIC}")

                # Poll for messages
                for message in consumer:
                    if not self._running: # Check if stop was requested during poll
                        break
                    
                    # Skip messages that couldn't be parsed by the deserializer
                    if message.value is None:
                        logger.warning(f"Skipping unparseable message at {message.topic} [{message.partition}] @ {message.offset}")
                        consumer.commit()
                        continue
                        
                    try:
                        logger.info(f"Received message from {message.topic}: Type {message.value.get('type', 'N/A')}")
                        # Process the message within the Flask app context if available
                        if self.app:
                            with self.app.app_context():
                                self.process_message(message.value)
                        else:
                            self.process_message(message.value) # Process without app context

                        # Commit offset after successful processing
                        consumer.commit()
                        logger.debug(f"Committed offset for {message.topic} [{message.partition}] @ {message.offset}")

                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                        # Still commit so we don't get stuck in a loop with a bad message
                        consumer.commit()

            except NoBrokersAvailable:
                logger.error(f"Kafka Consumer: No brokers available at {KAFKA_BOOTSTRAP_SERVERS}. Retrying in {RETRY_DELAY_SECONDS}s...")
                if consumer:
                    consumer.close()
                    consumer = None
                    self._consumer = None
                time.sleep(RETRY_DELAY_SECONDS)
            except Exception as e:
                logger.error(f"Unexpected error in consumer loop: {e}", exc_info=True)
                if consumer:
                    consumer.close()
                    consumer = None
                    self._consumer = None
                time.sleep(RETRY_DELAY_SECONDS) # Wait before retrying connection

        # Cleanup on exit
        if consumer:
            consumer.close()
        logger.info("Kafka Consumer loop stopped.")

    def process_message(self, message_data):
        """Processes a single message received from Kafka."""
        # Import necessary functions/models here to avoid circular imports
        # and work within app context if needed
        from app.models.models import User
        from app import db # Assuming db is initialized in app factory

        message_type = message_data.get('type')
        correlation_id = message_data.get('correlation_id')
        payload = message_data.get('payload', {})

        logger.info(f"Processing message type: {message_type} with correlation_id: {correlation_id}")

        # Corrected the check to match the command type sent by the orchestrator
        if message_type == 'get_payment_info':
            # The orchestrator sends 'user_id' in the payload for this command
            user_id = payload.get('user_id')

            if not user_id or not correlation_id:
                logger.error("Missing user_id or correlation_id in get_payment_info message.")
                # Optionally publish failure event if needed by orchestrator
                # self.publish_payment_info_failed(correlation_id, "Missing user_id or correlation_id")
                return # Cannot process without these

            try:
                # Assuming user_id from the command corresponds to clerk_user_id in the User model
                # This might need adjustment if user_id is a different identifier
                user = User.query.filter_by(clerk_user_id=user_id).first()

                if not user:
                    logger.warning(f"User not found for user_id (clerk_user_id): {user_id}")
                    self.publish_payment_info_failed(correlation_id, "User not found")
                    return

                if not user.stripe_customer_id:
                    logger.warning(f"Stripe customer ID missing for user: {user_id}")
                    self.publish_payment_info_failed(correlation_id, "Stripe customer ID not configured for user")
                    return

                # Check for payment method details stored in user_stripe_card JSONB field
                payment_method_id = user.user_stripe_card.get('payment_method_id') if user.user_stripe_card else None
                if not payment_method_id:
                    logger.warning(f"Default payment method ID missing for user: {user_id}")
                    self.publish_payment_info_failed(correlation_id, "Default payment method not set for user")
                    return

                # Success case: Prepare and publish the response event
                # The payload structure should match what the orchestrator expects
                # based on its handle_payment_info_retrieved method.
                response_payload = {
                    "payment_info": {
                        "stripeCustomerId": user.stripe_customer_id,
                        "paymentMethodId": payment_method_id
                        # Include other fields if needed by the orchestrator/payment service
                    }
                }

                response_message = {
                    "type": "user.payment_info_retrieved", # Event type expected by orchestrator
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": response_payload,
                    "source": "user-service"
                }
                self.publish(USER_EVENTS_TOPIC, response_message)
                logger.info(f"Published user.payment_info_retrieved for correlation_id: {correlation_id}")

            except Exception as e:
                # Catch exceptions during user lookup or processing
                logger.error(f"Error retrieving payment info for user {user_id}: {e}", exc_info=True)
                self.publish_payment_info_failed(correlation_id, f"Internal server error: {str(e)}")

        else:
            # Log unhandled message types
            logger.warning(f"Unhandled message type received: {message_type}")

    def publish_payment_info_failed(self, correlation_id, reason):
        """Publishes a failure event when payment info retrieval fails."""
        error_message = {
            "type": "user.payment_info_failed",
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "error": reason
            },
            "source": "user-service"
        }
        self.publish(USER_EVENTS_TOPIC, error_message)
        logger.info(f"Published user.payment_info_failed for correlation_id: {correlation_id}, Reason: {reason}")


    def start(self, app=None):
        """Starts the Kafka consumer in a separate thread and initializes producer."""
        if self._running:
            logger.warning("KafkaService already running.")
            return

        if app:
            self.app = app # Store app context for consumer thread

        self._running = True
        # Initialize producer first (can block if Kafka isn't ready)
        if not self._init_producer():
             logger.error("Producer initialization failed. Cannot start consumer.")
             self._running = False
             return

        # Start consumer loop in a background thread
        self._consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._consumer_thread.start()
        logger.info("KafkaService started.")

    def stop(self):
        """Stops the Kafka consumer thread and closes connections."""
        if not self._running:
            logger.info("KafkaService not running.")
            return

        logger.info("Stopping KafkaService...")
        self._running = False # Signal consumer loop to stop

        # Wait for consumer thread to finish
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=10) # Wait up to 10 seconds
            if self._consumer_thread.is_alive():
                 logger.warning("Consumer thread did not stop gracefully.")

        # Close producer
        if self._producer:
            try:
                self._producer.flush(timeout=5) # Flush remaining messages
                self._producer.close(timeout=5)
                logger.info("Kafka Producer closed.")
            except Exception as e:
                 logger.error(f"Error closing Kafka Producer: {e}")
            finally:
                 self._producer = None

        self._consumer = None # Clear consumer reference
        logger.info("KafkaService stopped.")

# --- Global Kafka Service Instance ---
# Initialize lazily or within Flask app factory
kafka_service = KafkaService()

# --- Optional: Flask Integration ---
def init_kafka(app):
    """Initialize Kafka service with Flask app context."""
    global kafka_service
    kafka_service = KafkaService(app)
    # Start the service when the Flask app starts
    # Note: This might run multiple times in debug mode with reloader
    # Consider using Flask-APScheduler or similar for robust background tasks
    if not app.config.get('TESTING'): # Don't start consumer during tests
         kafka_service.start(app)
    # Add teardown logic if needed
    # @app.teardown_appcontext
    # def teardown_kafka(exception=None):
    #     kafka_service.stop()

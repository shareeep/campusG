import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

# Import necessary components from the app
# Assuming TimerJob model exists if DB interaction is needed
# from app import db
# from app.models.models import TimerJob

# Force logger level for this module to ensure messages appear
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Ensure handlers are attached if basicConfig wasn't called or was overridden
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False # Prevent duplicate messages if root logger also has handlers

# Kafka Configuration from environment or defaults
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TIMER_COMMANDS_TOPIC = os.getenv('KAFKA_TIMER_COMMANDS_TOPIC', 'timer_commands') # Topic to consume commands
TIMER_EVENTS_TOPIC = os.getenv('KAFKA_TIMER_EVENTS_TOPIC', 'timer_events')       # Topic to publish events
CONSUMER_GROUP_ID = os.getenv('KAFKA_TIMER_SERVICE_GROUP_ID', 'timer-service-group') # Consumer group

class KafkaClient:
    """Kafka client for Timer Service (Producer & Consumer)"""

    _instance = None

    def __new__(cls, app=None):
        if cls._instance is None:
            logger.info("Creating KafkaClient instance for Timer Service")
            cls._instance = super(KafkaClient, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance.app = app # Store app context early
        return cls._instance

    def __init__(self, app=None):
        if self._initialized:
            return
        logger.info("Initializing KafkaClient for Timer Service")
        self.bootstrap_servers = KAFKA_BOOTSTRAP_SERVERS
        self.producer = None
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        self.command_handlers = {}
        # self.app is set in __new__ or init_kafka
        self._connect()
        self._initialized = True
        logger.info("KafkaClient for Timer Service initialized")

    def _connect(self):
        """Connect producer and consumer."""
        logger.info(">>> KafkaClient._connect entered <<<") # Added explicit log
        if not self.bootstrap_servers:
            logger.warning("KAFKA_BOOTSTRAP_SERVERS not set. Kafka client disabled.")
            return

        # Connect Producer
        try:
            logger.info(f"Attempting to connect Kafka producer to {self.bootstrap_servers}...")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                retries=5,
                request_timeout_ms=30000
            )
            logger.info("Kafka producer connected successfully.")
        except NoBrokersAvailable:
             logger.error(f"Kafka Producer: No brokers available at {self.bootstrap_servers}.")
             self.producer = None
        except Exception as e:
            logger.error(f"Failed to connect Kafka producer: {e}", exc_info=True)
            self.producer = None

        # Connect Consumer
        try:
            logger.info(f"Attempting to connect Kafka consumer to {self.bootstrap_servers} with group ID {CONSUMER_GROUP_ID}...")
            self.consumer = KafkaConsumer(
                # We will subscribe later in start_consuming
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000 # Poll timeout
            )
            logger.info(f"Kafka consumer created for group {CONSUMER_GROUP_ID}.")
        except NoBrokersAvailable:
             logger.error(f"Kafka Consumer: No brokers available at {self.bootstrap_servers}.")
             self.consumer = None
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}", exc_info=True)
            self.consumer = None

    def publish_event(self, event_type, payload, correlation_id=None):
        """Publish an event message to the TIMER_EVENTS_TOPIC."""
        if not self.producer:
            logger.warning(f"No Kafka producer available. Event {event_type} not sent.")
            return False

        message = {
            'type': event_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'payload': payload,
            'source': 'timer-service'
        }

        try:
            logger.info(f"Publishing event {event_type} to {TIMER_EVENTS_TOPIC} with correlation_id {correlation_id}")
            future = self.producer.send(TIMER_EVENTS_TOPIC, message)
            self.producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} to {TIMER_EVENTS_TOPIC}: {e}", exc_info=True)
            return False

    def register_command_handler(self, command_type, handler_function):
        """Register a handler for a specific command type."""
        self.command_handlers[command_type] = handler_function
        logger.info(f"Registered handler for command type: {command_type}")

    def start_consuming(self):
        """Subscribe to topics and start consuming messages."""
        if not self.consumer:
            logger.error("No Kafka consumer available. Cannot start consuming.")
            return False
        if self.running:
            logger.warning("Consumer already running.")
            return True

        try:
            self.consumer.subscribe([TIMER_COMMANDS_TOPIC])
            logger.info(f"Kafka consumer subscribed to topic: {TIMER_COMMANDS_TOPIC}")
        except Exception as e:
             logger.error(f"Failed to subscribe consumer to {TIMER_COMMANDS_TOPIC}: {e}", exc_info=True)
             return False

        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.consumer_thread.start()
        logger.info(f"Kafka consumer started in background thread.")
        return True

    def _consume_loop(self):
        """Main loop for consuming command messages."""
        logger.info("Timer Service consumer loop started.")
        while self.running:
            try:
                for message in self.consumer:
                    if not self.running: break
                    self._process_message(message)
            except Exception as e:
                logger.error(f"Error in Timer Service Kafka consumer loop: {e}", exc_info=True)
                time.sleep(5) # Avoid tight loop on errors
        logger.info("Timer Service consumer loop stopped.")

    def _process_message(self, message):
        """Process a received Kafka command message."""
        try:
            command_data = message.value
            command_type = command_data.get('type')
            correlation_id = command_data.get('correlation_id')
            payload = command_data.get('payload', {})

            logger.info(f"Received command {command_type} from {message.topic} with correlation_id {correlation_id}")

            handler = self.command_handlers.get(command_type)
            if handler:
                logger.debug(f"Executing handler for {command_type} (correlation_id: {correlation_id})")
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

    def _run_handler_with_app_context(self, handler, correlation_id, payload):
        """Execute handler function within app context."""
        if not self.app:
            logger.error("Cannot run handler: Flask app context not available")
            return
        with self.app.app_context():
            try:
                handler(correlation_id, payload)
            except Exception as e:
                logger.error(f"Error in handler execution for {correlation_id}: {e}", exc_info=True)

    def stop_consuming(self):
        """Stop the consumer loop."""
        if not self.running: return
        logger.info("Stopping Timer Service Kafka consumer...")
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5.0)
        logger.info("Timer Service Kafka consumer stopped.")

    def close(self):
        """Close Kafka connections."""
        logger.info("Closing Timer Service Kafka connections...")
        self.stop_consuming()
        if self.producer:
            self.producer.close(timeout=5)
            logger.info("Timer Service Kafka producer closed.")
        if self.consumer:
            self.consumer.close()
            logger.info("Timer Service Kafka consumer closed.")

# --- Command Handler ---

def handle_start_order_timer(correlation_id, payload):
    """Handles the 'start_order_timer' command."""
    logger.info(f"Handling start_order_timer for saga {correlation_id}")
    global kafka_client # Use the global client instance

    try:
        order_id = payload.get('order_id')
        customer_id = payload.get('customer_id') # Keep customer_id if needed for logging/DB
        timeout_at_str = payload.get('timeout_at')

        if not order_id or not timeout_at_str:
             logger.error(f"Missing order_id or timeout_at in start_order_timer payload for saga {correlation_id}")
             # Optionally publish timer.failed event
             # kafka_client.publish_event('timer.failed', {'error': 'Missing fields'}, correlation_id)
             return

        # Parse timeout string (optional for placeholder, but good practice)
        try:
            timeout_at = datetime.fromisoformat(timeout_at_str)
        except ValueError:
             logger.error(f"Invalid timeout_at format '{timeout_at_str}' for saga {correlation_id}")
             # kafka_client.publish_event('timer.failed', {'error': 'Invalid timestamp format'}, correlation_id)
             return

        # Create TimerJob record (optional, depends on if Timer Service persists timers)
        # For this placeholder, we might skip DB interaction or just log it
        logger.info(f"Placeholder: Timer requested for order {order_id}, timeout at {timeout_at_str}")
        # Example DB interaction (if needed):
        # from app import db # Import db within context if needed
        # from app.models.models import TimerJob # Import model if needed
        # timer_job = TimerJob(order_id=order_id, customer_id=customer_id, timeout_at=timeout_at)
        # db.session.add(timer_job)
        # db.session.commit()

        # Immediately publish the 'timer.started' event as a placeholder
        event_payload = {
            'order_id': order_id,
            'timer_set_at': datetime.now(timezone.utc).isoformat()
        }
        success = kafka_client.publish_event('timer.started', event_payload, correlation_id)

        if success:
            logger.info(f"Published placeholder timer.started event for order {order_id}, saga {correlation_id}")
        else:
            logger.error(f"Failed to publish placeholder timer.started event for order {order_id}, saga {correlation_id}")

    except Exception as e:
        # db.session.rollback() # Rollback if DB interaction was added
        logger.error(f"Error handling start_order_timer command for saga {correlation_id}: {e}", exc_info=True)
        # Optionally publish timer.failed event
        # kafka_client.publish_event('timer.failed', {'error': str(e)}, correlation_id)


# --- Initialization ---

# Global client instance
kafka_client = None

def init_kafka(app):
    """Initialize Kafka client, register handlers, and start consuming."""
    print(">>> PRINT: Timer Service init_kafka function entered <<<", flush=True) # Added print statement
    logger.info(">>> Timer Service init_kafka function entered <<<") # Keep logger too
    global kafka_client
    if kafka_client is None: # Avoid re-initialization
        logger.info("Initializing KafkaClient for Timer Service via init_kafka") # Added explicit log
        kafka_client = KafkaClient(app)

        # Register command handlers
        kafka_client.register_command_handler('start_order_timer', handle_start_order_timer)

        # Start consumer if connection was successful
        if kafka_client.consumer:
            kafka_client.start_consuming()
        else:
             logger.error("Cannot start Timer Service Kafka consumer - connection failed during initialization.")

    return kafka_client

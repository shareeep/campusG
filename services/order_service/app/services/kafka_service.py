import json
import logging
import os
import threading
import time
from datetime import datetime, timezone # Added timezone import

from kafka import KafkaConsumer, KafkaProducer
import uuid
import json
from decimal import Decimal

# Import necessary components from the app
from app import db
from app.models.models import Order, OrderStatus
from app.utils.calculations import calculate_food_total, calculate_delivery_fee # Import from utils

logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
ORDER_COMMANDS_TOPIC = 'order_commands'    # Topic to consume commands from (Changed hyphen to underscore)
ORDER_EVENTS_TOPIC = 'order_events'        # Topic to publish events to
CONSUMER_GROUP_ID = 'order-service-group'  # Unique consumer group ID

class KafkaService:
    """Kafka client for the Order Service"""

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
        self.command_handlers = {}  # Handlers for incoming commands
        self.app = None  # To store Flask app
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
                retries=5,  # Retry connecting
                request_timeout_ms=30000  # Increase timeout
            )
            logger.info("Kafka producer connected successfully.")

            logger.info(f"Attempting to connect Kafka consumer to {self.bootstrap_servers} with group ID {CONSUMER_GROUP_ID}...")
            self.consumer = KafkaConsumer(
                ORDER_COMMANDS_TOPIC,  # Subscribe only to the commands topic
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000  # Poll timeout
            )
            logger.info(f"Kafka consumer connected and subscribed to {ORDER_COMMANDS_TOPIC}.")

        except Exception as e:
            logger.error(f"Failed to connect to Kafka at {self.bootstrap_servers}: {e}", exc_info=True)
            self.producer = None
            self.consumer = None

    def publish_event(self, event_type, payload, correlation_id=None):
        """Publish an event message to the ORDER_EVENTS_TOPIC."""
        if not self.producer:
            logger.warning(f"No Kafka producer available. Event {event_type} not sent.")
            return False

        if not correlation_id:
            correlation_id = f"order-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
            logger.info(f"Generated new correlation_id: {correlation_id}")

        message = {
            'type': event_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload,
            'source': 'order-service'  # Identify the source service
        }

        try:
            logger.info(f"Publishing event {event_type} to {ORDER_EVENTS_TOPIC} with correlation_id {correlation_id}")
            future = self.producer.send(ORDER_EVENTS_TOPIC, message)
            # Wait for send confirmation (optional, adds latency but ensures delivery)
            # result = future.get(timeout=10)
            # logger.info(f"Event {event_type} published successfully to partition {result.partition} offset {result.offset}")
            self.producer.flush()  # Ensure message is sent
            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} to {ORDER_EVENTS_TOPIC}: {e}", exc_info=True)
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
        logger.info(f"Kafka consumer started in background thread, listening on {ORDER_COMMANDS_TOPIC}.")
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

# --- Convenience methods for publishing specific order events ---

def publish_order_created_event(kafka_service, order_data, correlation_id=None):
    """Publish an order.created event."""
    return kafka_service.publish_event(
        'order.created',
        order_data,
        correlation_id
    )

def publish_order_updated_event(kafka_service, order_data, correlation_id=None):
    """Publish an order.updated event."""
    return kafka_service.publish_event(
        'order.updated',
        order_data,
        correlation_id
    )

def publish_order_status_changed_event(kafka_service, order_id, old_status, new_status, correlation_id=None):
    """Publish an order.status_changed event."""
    return kafka_service.publish_event(
        'order.status_changed',
        {
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status
        },
        correlation_id
    )

def publish_order_cancelled_event(kafka_service, order_id, reason, correlation_id=None):
    """Publish an order.cancelled event."""
    return kafka_service.publish_event(
        'order.cancelled', # New event type
        {
            'order_id': order_id,
            'reason': reason
        },
        correlation_id
    )

# --- Initialization ---

# Global instance (using singleton pattern via __new__)
kafka_client = KafkaService()

def init_kafka(app):
    """Initialize the Kafka client and start consuming."""
    global kafka_client
    
    # Store the Flask app reference
    kafka_client.app = app
    
    if not kafka_client.producer or not kafka_client.consumer:
        logger.warning("Kafka client not fully connected during init_kafka. Will rely on lazy connection.")
        # Attempt to reconnect or rely on lazy connection within methods
        kafka_client._connect()  # Try connecting again

    # Register command handlers here
    # Example: register_create_order_handler(kafka_client)
    # Register command handlers
    kafka_client.register_command_handler('create_order', handle_create_order_command)
    kafka_client.register_command_handler('update_order_status', handle_update_order_status_command)
    kafka_client.register_command_handler('cancel_order', handle_cancel_order_command) # Register cancellation handler

    if kafka_client.consumer:
        kafka_client.start_consuming()
    else:
        logger.error("Cannot start Kafka consumer - connection failed during initialization.")
    
    # Handle graceful shutdown
    import signal
    def handle_shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down Kafka client.")
        kafka_client.close()
        
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("Kafka client initialization sequence completed.")
    return kafka_client


# --- Command Handlers ---

def handle_create_order_command(correlation_id, payload):
    """Handles the 'create_order' command received from Kafka."""
    logger.info(f"Handling create_order command for saga {correlation_id}")
    try:
        customer_id = payload.get('customer_id')
        order_details = payload.get('order_details')
        saga_id = payload.get('saga_id') # Saga ID is expected from orchestrator

        if not customer_id or not order_details or not saga_id:
            logger.error(f"Missing required fields in create_order payload for saga {correlation_id}")
            # Optionally publish a failure event
            # kafka_client.publish_event('order.creation_failed', {'error': 'Missing fields'}, correlation_id)
            return

        # Extract details from payload
        food_items = order_details.get('foodItems', [])
        delivery_location = order_details.get('deliveryLocation', '')
        store_location = order_details.get('storeLocation', None) # Extract store location
        input_delivery_fee = order_details.get('deliveryFee', None) # Extract delivery fee

        # Calculate food fee
        food_fee = calculate_food_total(food_items)
        
        # Use extracted delivery fee
        try:
            delivery_fee = Decimal(str(input_delivery_fee)) if input_delivery_fee is not None else Decimal('0.00')
        except (TypeError, ValueError):
             logger.warning(f"Invalid deliveryFee '{input_delivery_fee}' received in Kafka command for saga {correlation_id}. Defaulting to 0.")
             delivery_fee = Decimal('0.00')

        # Create a new order
        order = Order(
            order_id=str(uuid.uuid4()), # Generate a new unique ID for the order itself
            cust_id=customer_id,
            order_description=json.dumps(food_items),
            food_fee=food_fee,
            delivery_fee=delivery_fee, # Use extracted fee
            store_location=store_location, # Add extracted store location
            delivery_location=delivery_location,
            order_status=OrderStatus.PENDING, # Initial status for saga-created orders
            saga_id=saga_id # Store the saga ID for reference
        )

        # Save to database
        db.session.add(order)

        db.session.commit()
        logger.info(f"Order {order.order_id} created successfully in DB for saga {correlation_id}")

        # Publish the order.created event, passing the correlation_id from the command
        event_payload = {
            'order_id': order.order_id,
            'customer_id': order.cust_id,
            'status': order.order_status.name,
            'saga_id': saga_id
            # Include other relevant details if needed
        }
        success = publish_order_created_event(kafka_client, event_payload, correlation_id)

        if success:
            logger.info(f"Published order.created event for order {order.order_id}, saga {correlation_id}")
        else:
            logger.error(f"Failed to publish order.created event for order {order.order_id}, saga {correlation_id}")
            # Consider compensating action if event publishing fails critically

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error handling create_order command for saga {correlation_id}: {e}", exc_info=True)
        # Optionally publish a failure event
        # kafka_client.publish_event('order.creation_failed', {'error': str(e)}, correlation_id)

    # REMOVE THE ERRONEOUS RAISE EXCEPTION LINE THAT WAS HERE

def handle_update_order_status_command(correlation_id, payload):
    """Handles the 'update_order_status' command received from Kafka."""
    logger.info(f"Handling update_order_status command for saga {correlation_id}")
    try:
        order_id = payload.get('order_id')
        new_status_str = payload.get('status')

        if not order_id or not new_status_str:
            logger.error(f"Missing order_id or status in update_order_status payload for saga {correlation_id}")
            # Optionally publish failure event
            # kafka_client.publish_event('order.status_update_failed', {'error': 'Missing fields'}, correlation_id)
            return

        # Find the order
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for status update (saga {correlation_id})")
            # Optionally publish failure event
            # kafka_client.publish_event('order.status_update_failed', {'error': 'Order not found'}, correlation_id)
            return

        # Validate and set the new status
        try:
            new_status = OrderStatus[new_status_str] # Convert string to enum
        except KeyError:
            logger.error(f"Invalid status '{new_status_str}' received for order {order_id} (saga {correlation_id})")
            # Optionally publish failure event
            # kafka_client.publish_event('order.status_update_failed', {'error': 'Invalid status'}, correlation_id)
            return
        
        # --- TEMPORARY FOR TESTING SCENARIO 1b COMMENT TO TEST STATUS UPDATE FAILURE---
        # raise Exception("Simulating status update failure") 
        # --- REMOVE AFTER TESTING ---

        order.order_status = new_status
        order.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info(f"Order {order_id} status updated to {new_status.name} successfully for saga {correlation_id}")

        # Publish the order.status_updated event
        event_payload = {
            'order_id': order.order_id,
            'status': order.order_status.name,
            'saga_id': order.saga_id # Include saga_id if available and needed
        }
        # Publish the specific 'order.status_updated' event expected by the orchestrator
        success = kafka_client.publish_event(
            'order.status_updated', # Correct event type
            event_payload,
            correlation_id
        )

        if success:
            logger.info(f"Published order.status_updated event for order {order_id}, saga {correlation_id}")
        else:
            logger.error(f"Failed to publish order.status_updated event for order {order_id}, saga {correlation_id}")
            # Consider compensating action

    except Exception as e:
        db.session.rollback()
        error_message = f"Error handling update_order_status command for saga {correlation_id}: {str(e)}"
        logger.error(error_message, exc_info=True)
        # Publish failure event so orchestrator can compensate
        failure_payload = {
            'order_id': payload.get('order_id'), # Include order_id if available in original payload
            'error': str(e)
        }
        kafka_client.publish_event('order.status_update_failed', failure_payload, correlation_id)


def handle_cancel_order_command(correlation_id, payload):
    """Handles the 'cancel_order' command received from Kafka."""
    logger.info(f"Handling cancel_order command for saga {correlation_id}")
    try:
        order_id = payload.get('order_id')
        reason = payload.get('reason', 'Cancellation requested') # Default reason

        if not order_id:
            logger.error(f"Missing order_id in cancel_order payload for saga {correlation_id}")
            # Optionally publish failure event
            # kafka_client.publish_event('order.cancellation_failed', {'error': 'Missing order_id'}, correlation_id)
            return

        # Find the order
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for cancellation (saga {correlation_id})")
            # Optionally publish failure event
            # kafka_client.publish_event('order.cancellation_failed', {'error': 'Order not found'}, correlation_id)
            return

        # Check if order is already cancelled or completed
        if order.order_status in [OrderStatus.CANCELLED, OrderStatus.COMPLETED, OrderStatus.DELIVERED]:
             logger.warning(f"Order {order_id} is already in a final state ({order.order_status.name}) and cannot be cancelled.")
             # Publish success anyway? Or a specific event? Let's publish success for idempotency.
             success = publish_order_cancelled_event(kafka_client, order.order_id, f"Already in final state: {order.order_status.name}", correlation_id)
             return

        # Update status to CANCELLED
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        # Optionally store the reason somewhere if the model supports it
        db.session.commit()
        logger.info(f"Order {order_id} status updated to CANCELLED successfully for saga {correlation_id}")

        # Publish the order.cancelled event
        success = publish_order_cancelled_event(kafka_client, order.order_id, reason, correlation_id)

        if success:
            logger.info(f"Published order.cancelled event for order {order_id}, saga {correlation_id}")
        else:
            logger.error(f"Failed to publish order.cancelled event for order {order_id}, saga {correlation_id}")
            # Consider compensating action? Unlikely needed for cancellation failure.

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error handling cancel_order command for saga {correlation_id}: {e}", exc_info=True)
        # Optionally publish failure event
        # kafka_client.publish_event('order.cancellation_failed', {'error': str(e)}, correlation_id)

    # Ensure the temporary raise Exception for testing Scenario 1b is NOT in handle_update_order_status_command unless actively testing that scenario.

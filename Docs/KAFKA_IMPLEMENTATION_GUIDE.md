# Guide to Implementing Kafka in a Microservice

This guide provides a step-by-step approach to implementing Kafka messaging in a microservice for bidirectional communication (sending and receiving messages).

## Step 1: Add Required Dependencies

Add the necessary dependency to your `requirements.txt` file:

```
kafka-python==2.0.2
```

## Step 2: Create the Kafka Service Module

Create a file named `kafka_service.py` in your service's `app/services/` directory with the following structure:

```python
import json
import logging
import os
import threading
import time
from datetime import datetime

from kafka import KafkaConsumer, KafkaProducer

logger = logging.getLogger(__name__)

# Kafka Configuration - customize these for your service
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
SERVICE_COMMANDS_TOPIC = 'service_commands'  # Topic to consume commands from
SERVICE_EVENTS_TOPIC = 'service_events'      # Topic to publish events to
CONSUMER_GROUP_ID = 'your-service-group'     # Unique consumer group ID

class KafkaService:
    """Kafka client for the service"""

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
        self.app = None  # To store Flask app reference
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
                SERVICE_COMMANDS_TOPIC,  # Subscribe to the commands topic
                bootstrap_servers=self.bootstrap_servers,
                group_id=CONSUMER_GROUP_ID,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000  # Poll timeout
            )
            logger.info(f"Kafka consumer connected and subscribed to {SERVICE_COMMANDS_TOPIC}.")

        except Exception as e:
            logger.error(f"Failed to connect to Kafka at {self.bootstrap_servers}: {e}", exc_info=True)
            self.producer = None
            self.consumer = None

    def publish_event(self, event_type, payload, correlation_id=None):
        """Publish an event message to the SERVICE_EVENTS_TOPIC."""
        if not self.producer:
            logger.warning(f"No Kafka producer available. Event {event_type} not sent.")
            return False

        if not correlation_id:
            correlation_id = f"service-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
            logger.info(f"Generated new correlation_id: {correlation_id}")

        message = {
            'type': event_type,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload,
            'source': 'your-service-name'  # Identify the source service
        }

        try:
            logger.info(f"Publishing event {event_type} to {SERVICE_EVENTS_TOPIC} with correlation_id {correlation_id}")
            future = self.producer.send(SERVICE_EVENTS_TOPIC, message)
            # Wait for send confirmation (optional, adds latency but ensures delivery)
            # result = future.get(timeout=10)
            # logger.info(f"Event {event_type} published successfully to partition {result.partition} offset {result.offset}")
            self.producer.flush()  # Ensure message is sent
            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} to {SERVICE_EVENTS_TOPIC}: {e}", exc_info=True)
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
        logger.info(f"Kafka consumer started in background thread, listening on {SERVICE_COMMANDS_TOPIC}.")
        return True

    def _consume_loop(self):
        """Main loop for consuming command messages."""
        logger.info("Consumer loop started.")
        while self.running:
            try:
                # Poll for messages
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
                self.consumer.close()
                logger.info("Kafka consumer closed.")
            except Exception as e:
                logger.error(f"Error closing Kafka consumer: {e}", exc_info=True)
            self.consumer = None
        logger.info("Kafka service connections closed.")

# --- Convenience methods for publishing specific events ---

def publish_example_event(kafka_service, data, correlation_id=None):
    """Publish an example.created event."""
    return kafka_service.publish_event(
        'example.created',
        data,
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
    # Example: register_handler(kafka_client)

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
```

## Step 3: Update Your Application Initialization

Modify your `run.py` to initialize the Kafka service:

```python
from app import create_app, db
from app.services.kafka_service import init_kafka
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = create_app()

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    logging.info("Database tables created (if they didn't exist)")

# Initialize Kafka service
init_kafka(app)
logging.info("Kafka service initialized")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
```

## Step 4: Update Docker Configuration

Ensure your service has the proper Kafka configuration in `docker-compose.yml`:

```yaml
your-service:
  build:
    context: ./services/your-service
  environment:
    - DATABASE_URL=postgresql://postgres:postgres@your-service-db:5432/your_service_db
    - KAFKA_BOOTSTRAP_SERVERS=kafka:9092  # Add this environment variable
    - FLASK_APP=run.py
    - FLASK_DEBUG=0
  depends_on:
    your-service-db:
      condition: service_healthy
    kafka:  # Add dependency on Kafka
      condition: service_healthy
  ports:
    - "3000:3000"
  volumes:
    - ./services/your-service:/app  # For development - mount code changes
```

## Step 5: Implement Command Handlers

Create handlers for commands you want to process:

```python
# In a separate module or in kafka_service.py
def handle_example_command(correlation_id, payload):
    """
    Handle an example command.
    This function will be called when an 'example_command' message is received.
    
    Args:
        correlation_id: The ID to correlate this command with its response
        payload: The command payload/data
    """
    logger.info(f"Processing example command with correlation_id {correlation_id}")
    # Process the command
    # ...
    
    # Optionally publish a response event
    from app.services.kafka_service import kafka_client
    kafka_client.publish_event(
        'example.command_processed',
        {'status': 'success', 'result': 'Command processed successfully'},
        correlation_id
    )

# Register handler in init_kafka function
def register_handlers(kafka_client):
    kafka_client.register_command_handler('example_command', handle_example_command)
    # Register more handlers as needed
```

Then update the init_kafka function to register handlers:

```python
def init_kafka(app):
    """Initialize the Kafka client and start consuming."""
    # ... existing code ...
    
    # Register command handlers here
    register_handlers(kafka_client)
    
    # ... rest of existing code ...
```

## Step 6: Publishing Events

To publish events from your service, use the Kafka client:

```python
from app.services.kafka_service import kafka_client

# Within a route or service function
def your_business_function():
    # Do something
    result = perform_business_logic()
    
    # Publish an event to notify other services
    kafka_client.publish_event(
        'your_entity.created',  # Event type
        {                       # Event payload
            'id': result.id,
            'name': result.name,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }
    )
    
    return result
```

## Step 7: Testing Kafka Communication

Create test scripts to verify your Kafka integration:

```python
# test_kafka_publish.py
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
YOUR_EVENTS_TOPIC = 'your_service_events'

def main():
    # Create producer
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("Connected to Kafka successfully")
        
        # Create test event message
        correlation_id = f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        test_data = {
            "id": "test-123",
            "name": "Test Entity",
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Format message
        message = {
            'type': 'entity.created',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': test_data,
            'source': 'your-service'
        }
        
        # Publish message
        logger.info(f"Publishing test message to {YOUR_EVENTS_TOPIC} with correlation_id {correlation_id}...")
        logger.info(f"Message content: {json.dumps(message, indent=2)}")
        
        producer.send(YOUR_EVENTS_TOPIC, message)
        producer.flush()
        logger.info("Message sent successfully")
        
        # Wait to ensure message is processed
        time.sleep(2)
        
    except Exception as e:
        logger.error(f"Error in Kafka test: {e}", exc_info=True)
    finally:
        if 'producer' in locals():
            producer.close()
            logger.info("Kafka producer closed")

if __name__ == "__main__":
    main()
```

## Step 8: Running and Testing

1. Start your services with Kafka:
   ```bash
   docker-compose up -d kafka zookeeper your-service
   ```

2. Verify Kafka connection logs:
   ```bash
   docker logs your-service | grep Kafka
   ```

3. Run the test script to send a message:
   ```bash
   docker exec -it your-service bash
   cd /app
   python test_kafka_publish.py
   ```

4. Monitor the logs to verify the message is received by the subscribing service:
   ```bash
   docker logs other-service | grep "correlation_id"
   ```

## Best Practices

1. **Use Correlation IDs**: Always include correlation IDs to track message flows across services.

2. **Define Clear Event Types**: Use a consistent naming convention (e.g., `entity.action`) for event types.

3. **Idempotent Handlers**: Ensure command handlers are idempotent to handle potential message duplicates.

4. **Error Handling**: Implement robust error handling in consumer loops and command handlers.

5. **Graceful Shutdown**: Always close Kafka connections when your service shuts down.

6. **Monitoring**: Add logging to track Kafka connection status and message flows.

7. **Retry Mechanism**: Implement retry logic for failed message processing.

## Common Issues and Solutions

1. **Connection Failures**:
   - Verify Kafka bootstrap servers are correct
   - Check network connectivity between services
   - Ensure Kafka container is running

2. **Message Format Errors**:
   - Verify serialization/deserialization logic
   - Ensure consistent message structure

3. **Lost Messages**:
   - Check consumer group configuration
   - Verify offset management

4. **High Latency**:
   - Optimize batch size and compression settings
   - Consider increasing Kafka resources

5. **Testing Tips**:
   - Use separate topics for testing
   - Create dedicated test scripts

By following these steps, you should be able to successfully implement Kafka messaging in your microservice for both sending and receiving messages.

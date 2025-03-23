# Changelog - 23 March 2025

## Disabled Kafka Dependencies to Fix Microservice Connectivity Issues

### Problem
Multiple microservices (escrow, notification, timer, scheduler, payment) were failing to connect to their API endpoints, resulting in errors like:
```
GET http://localhost:3004/api/escrow/1
Error: connect ECONNREFUSED 127.0.0.1:3004
```

### Root Causes
1. Services were failing to start properly due to failed Kafka connection attempts
2. Kafka dependencies were causing startup issues while Kafka integration is on hold (as noted in TO-DO.md)
3. Unlike order service (fixed in previous changelog), the issue was with Kafka dependencies rather than async/await patterns

### Changes Made
1. Modified `docker-compose.yml`:
   - Disabled Kafka and Zookeeper services (commented them out)
   - Removed Kafka dependencies from all microservices' `depends_on` sections
   - Commented out Kafka-related environment variables

2. Created mock implementations of `kafka_service.py` in each service:
   - Escrow service
   - Payment service 
   - Notification service
   - Timer service
   
3. Updated the Kafka client to log messages instead of actually connecting to Kafka:
   ```python
   class KafkaClient:
       """Mock Kafka client that logs messages instead of publishing to Kafka topics"""
       
       def __init__(self, bootstrap_servers=None):
           current_app.logger.info("Initializing Mock Kafka Client - Kafka functionality is disabled")
       
       def publish(self, topic, message):
           # Add timestamp if not present
           if isinstance(message, dict) and 'timestamp' not in message:
               message['timestamp'] = datetime.utcnow().isoformat()
               
           # Log the message
           current_app.logger.info(f"[KAFKA DISABLED] Would publish to {topic}: {message}")
           
           return True
       
       def close(self):
           """No-op close method"""
           pass
   ```

### Results
- All services now start successfully and can be accessed via their API endpoints
- Current REST API-based communication works normally
- Kafka-related code execution is preserved but just logs messages without attempting connections
- No runtime errors related to Kafka connections

### Notes
- This change is intended to be temporary until all services are fully operational
- Kafka integration will be revisited once core functionality is working properly
- No database migrations or schema changes were made

## How to Re-enable Kafka in the Future

When you're ready to re-enable Kafka functionality, follow these steps:

### 1. Restore docker-compose.yml
- Uncomment the Kafka and Zookeeper services 
- Restore the Kafka dependencies in each service's `depends_on` section
- Uncomment the Kafka-related environment variables

### 2. Restore Kafka client implementations
For each service (escrow, payment, notification, timer), restore the original Kafka client implementation:

```python
import json
from datetime import datetime
from flask import current_app
import kafka
from kafka import KafkaProducer

class KafkaClient:
    """Kafka client for publishing events to Kafka topics"""
    
    def __init__(self, bootstrap_servers=None):
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
        """Publish a message to a Kafka topic"""
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
```

### 3. Implement Kafka Consumers
As outlined in TO-DO.md (task 3.1), implement Kafka consumers for handling events:

- Create `services/notification-service/app/consumers/order_events_consumer.py`
- Implement event handling for various order status changes
- Add consumer initialization in the service's startup code

### 4. Update Saga Implementations
Ensure Saga orchestrators use Kafka events for inter-service communication:

- Update `services/order_service/app/sagas/create_order_saga.py` 
- Implement `services/order_service/app/sagas/accept_order_saga.py`
- Implement `services/order_service/app/sagas/complete_order_saga.py`

### 5. Testing and Verification
- Verify Kafka connectivity and event publishing
- Test each event flow to ensure subscribers receive events
- Verify saga compensations work properly

### Additional Tips
- When implementing consumers, use the `KafkaConsumer` class from the `kafka-python` package
- Consider implementing a graceful fallback mechanism for when Kafka is unavailable
- Implement better error handling around Kafka operations
- Add monitoring for Kafka health and event delivery

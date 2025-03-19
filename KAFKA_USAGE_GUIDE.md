# Kafka Usage Guide for CampusG

This document explains how Kafka is used in our CampusG microservices architecture and provides a simple guide for using and monitoring it.

## What is Kafka and How We Use It

### Simple Explanation

Apache Kafka is a message broker system that acts like a central message board for our microservices. It allows different services to communicate without direct connections.

Think of Kafka as a post office with different mailboxes (topics):
- Services can put messages in specific mailboxes (publishing)
- Other services can check specific mailboxes for new messages (subscribing)
- Messages stay in the mailbox until they're processed (persistence)

### Key Concepts

1. **Topics**: Named channels where messages are published
   - We use specific topics for different events (e.g., `payment-events`, `order-events`)

2. **Producers**: Services that send messages to Kafka topics
   - All our microservices act as producers when they need to announce events

3. **Consumers**: Services that read messages from Kafka topics
   - Services subscribe to topics relevant to their function

4. **Messages**: The data being sent, with a key and value
   - Our standard format includes event type, timestamp, and payload

## Kafka Topics in Our System

| Topic Name | Description | Publisher Services | Consumer Services |
|------------|-------------|-------------------|-------------------|
| `payment-events` | Payment-related events | Payment Service | Order Service, Notification Service |
| `order-events` | Order status updates | Order Service | Notification Service, Timer Service |
| `escrow-events` | Escrow fund operations | Escrow Service | Order Service, Notification Service |
| `timer-events` | Timeout events | Timer Service | Order Service |
| `notification-events` | User notifications | Notification Service | - |
| `system-logs` | Centralized logging | All Services | Log consumers |

## Message Structure

All messages follow this format:

```json
{
  "type": "EVENT_TYPE",
  "timestamp": "2025-03-19T13:00:00.000Z",
  "payload": {
    // Event-specific data
  }
}
```

Examples:
- `PAYMENT_AUTHORIZED` - When a payment is authorized
- `ORDER_CREATED` - When an order is created
- `FUNDS_HELD` - When funds are held in escrow
- `ORDER_TIMEOUT` - When an order times out

## How Our Kafka Integration Works

### Publishing Events

We've added a standardized `kafka_service.py` to each microservice. Example of publishing an event:

```python
# In any service
from app.services.kafka_service import kafka_client

# When something important happens
kafka_client.publish('payment-events', {
    'type': 'PAYMENT_AUTHORIZED', 
    'payload': {
        'orderId': 'order-123',
        'amount': 29.99
    }
})
```

### Consuming Events

Services set up consumers to listen for relevant events:

```python
# Example consumer function
def consume_payment_events():
    for message in kafka_consumer.consume('payment-events'):
        event_data = json.loads(message.value)
        event_type = event_data.get('type')
        
        if event_type == 'PAYMENT_AUTHORIZED':
            # Handle payment authorization
            pass
```

### Centralized Logging

All services send logs to the `system-logs` topic:

```python
kafka_client.publish('system-logs', {
    'service': 'payment-service',
    'level': 'INFO',
    'message': 'Payment authorized for order xyz',
    'data': { 'orderId': 'order-123' }
})
```

## Running Kafka with Docker Compose

Our `docker-compose.yml` already has Kafka and Zookeeper configured:

```bash
# Start Kafka and Zookeeper
docker-compose up -d zookeeper kafka

# Start all services
docker-compose up -d
```

## Monitoring Kafka

### Basic Health Check

```bash
# Check if Kafka container is running
docker ps | grep kafka

# Check Kafka logs
docker-compose logs -f kafka
```

### Viewing Topics

```bash
# List all topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Describe a specific topic
docker-compose exec kafka kafka-topics --describe --topic payment-events --bootstrap-server localhost:9092
```

### Viewing Messages

```bash
# Monitor messages on a topic
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic payment-events --from-beginning
```

## Debugging Tips

1. **Service Not Receiving Messages?**
   - Check if the service is subscribed to the correct topic
   - Verify the consumer group ID is correct
   - Check for errors in the service logs

2. **Messages Not Being Sent?**
   - Check Kafka logs for errors
   - Verify the producer configuration
   - Check network connectivity between services and Kafka

3. **Getting Serialization Errors?**
   - Ensure consistent message formats
   - Check JSON serialization/deserialization

## Common Kafka Commands

```bash
# Create a topic
docker-compose exec kafka kafka-topics --create --topic my-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Delete a topic
docker-compose exec kafka kafka-topics --delete --topic my-topic --bootstrap-server localhost:9092

# Produce a test message
docker-compose exec kafka kafka-console-producer --bootstrap-server localhost:9092 --topic my-topic
```

## Saga Workflow Example with Kafka

### Create Order Saga:

1. Order Service creates order → publishes `ORDER_CREATED` to `order-events`
2. Payment Service receives event → authorizes payment → publishes `PAYMENT_AUTHORIZED` to `payment-events`
3. Escrow Service receives event → holds funds → publishes `FUNDS_HELD` to `escrow-events`
4. Timer Service receives event → starts timeout timer → publishes `TIMER_STARTED` to `timer-events`
5. Notification Service receives all events → sends appropriate notifications

This enables a loosely coupled architecture where each service can work independently and recover from failures.

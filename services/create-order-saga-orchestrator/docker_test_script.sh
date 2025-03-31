#!/bin/bash

# Docker-friendly test script for Create Order Saga

echo "Create Order Saga Orchestrator Test Script (Docker version)"
echo ""

# Set bootstrap servers for Kafka
KAFKA_SERVERS=kafka:9092

# Create a test event directly
echo "Sending a test message to Kafka..."
python -c "
from kafka import KafkaProducer
import json, uuid
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers='$KAFKA_SERVERS',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

correlation_id = str(uuid.uuid4())
order_id = 'order-' + str(uuid.uuid4())[:8]

message = {
    'type': 'test.event',
    'correlation_id': correlation_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'order_id': order_id,
        'test': True
    }
}

# Send to a test topic
future = producer.send('test_topic', message)
try:
    record_metadata = future.get(timeout=10)
    print(f'Message sent to {record_metadata.topic} partition {record_metadata.partition}')
except Exception as e:
    print(f'Error sending message: {e}')
finally:
    producer.flush()
    producer.close()
    print(f'Test complete - message sent with correlation_id: {correlation_id}')
"

echo "Test complete. Check the logs for results."

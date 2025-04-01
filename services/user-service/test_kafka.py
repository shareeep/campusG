#!/usr/bin/env python3
"""
Test script for User Service Kafka integration.
This sends a test message to the user_commands topic and listens for a response
on the user_events topic.
"""

from kafka import KafkaProducer, KafkaConsumer
import json
import uuid
import time
from datetime import datetime

# Configuration
BOOTSTRAP_SERVERS = ['kafka:9092']
USER_COMMANDS_TOPIC = 'user_commands'
USER_EVENTS_TOPIC = 'user_events'
CORRELATION_ID = f"test_kafka_{uuid.uuid4().hex[:8]}"
CLERK_USER_ID = "user_test_1apr2025_02"  # Our test user

def main():
    print(f"Starting Kafka test with correlation_id: {CORRELATION_ID}")
    
    # Start consumer for user_events first (non-blocking)
    consumer = KafkaConsumer(
        USER_EVENTS_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        group_id=f'test-consumer-{uuid.uuid4().hex[:8]}',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=1000
    )
    
    # Create and configure producer
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Prepare test message
    test_message = {
        "type": "get_user_payment_info",
        "correlation_id": CORRELATION_ID,
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "clerkUserId": CLERK_USER_ID,
            "order": {
                "amount": 5000,
                "description": "Test Order for Kafka Integration"
            }
        }
    }
    
    print("Sending test message to user_commands topic...")
    
    # Send message
    future = producer.send(USER_COMMANDS_TOPIC, test_message)
    producer.flush()
    message_metadata = future.get(timeout=10)
    
    print(f"Message sent to {message_metadata.topic} partition {message_metadata.partition} offset {message_metadata.offset}")
    
    # Wait for and print response (for up to 10 seconds)
    print(f"Waiting for response on {USER_EVENTS_TOPIC} topic...")
    start_time = time.time()
    response_received = False
    
    while time.time() - start_time < 10:
        for message in consumer:
            response = message.value
            if response.get('correlation_id') == CORRELATION_ID:
                print(f"Received response: {json.dumps(response, indent=2)}")
                response_received = True
                break
        
        if response_received:
            break
            
        time.sleep(0.5)
    
    if not response_received:
        print("No response received within 10 seconds.")
    
    consumer.close()
    producer.close()
    print("Test completed.")

if __name__ == "__main__":
    main()

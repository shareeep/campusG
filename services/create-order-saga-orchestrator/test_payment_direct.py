#!/usr/bin/env python
"""
Direct test script for Payment Service Stripe integration
This sends an authorize_payment command directly to the payment_commands topic
"""

import json
import uuid
import time
import sys
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'kafka:9092'  # Use kafka:9092 when running in Docker
PAYMENT_COMMANDS_TOPIC = 'payment_commands'
PAYMENT_EVENTS_TOPIC = 'payment_events'
ORDER_ID = f"test-order-{int(time.time())}"
CORRELATION_ID = str(uuid.uuid4())

print("Payment Service - Direct Stripe Integration Test")
print("-----------------------------------------")
print(f"Using correlation ID: {CORRELATION_ID}")
print(f"Using order ID: {ORDER_ID}")

# Create Kafka producer
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print(f"Successfully connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
except Exception as e:
    print(f"Failed to connect to Kafka: {e}")
    sys.exit(1)

# Create an authorize_payment command with valid Stripe data
authorize_payment_command = {
    'type': 'authorize_payment',
    'correlation_id': CORRELATION_ID,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'order_id': ORDER_ID,
        'customer': {
            'clerkUserId': 'clerk_test_user_id',
            'stripeCustomerId': 'cus_S2oxjQYZK8Z1Qy',  # Valid Stripe customer ID
            'userStripeCard': {
                'payment_method_id': 'pm_card_visa'  # Default test card for Stripe
            }
        },
        'order': {
            'amount': 1299,  # $12.99 in cents
            'description': f"Test payment for order {ORDER_ID}"
        }
    }
}

print("\nSending authorize_payment command to Kafka...")
producer.send(PAYMENT_COMMANDS_TOPIC, authorize_payment_command)
producer.flush()
print("Command sent successfully.")

# Set up a consumer to listen for response events
print("\nSetting up consumer to listen for payment_events...")
consumer = KafkaConsumer(
    PAYMENT_EVENTS_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id=f'payment-test-{uuid.uuid4()}',  # Unique group ID
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# Listen for response events
print("\nWaiting for payment response events (30 second timeout)...")
print("Looking for correlation_id:", CORRELATION_ID)

response_received = False
start_time = time.time()
timeout = 30  # seconds

try:
    while time.time() - start_time < timeout:
        # Poll with a 1-second timeout
        messages = consumer.poll(timeout_ms=1000)
        
        if not messages:
            sys.stdout.write('.')
            sys.stdout.flush()
            continue
            
        for topic_partition, msgs in messages.items():
            for msg in msgs:
                message = msg.value
                
                # Check if this message has our correlation ID
                if message.get('correlation_id') == CORRELATION_ID:
                    event_type = message.get('type')
                    payload = message.get('payload', {})
                    
                    print(f"\n\nReceived response: {event_type}")
                    print(f"Payload: {json.dumps(payload, indent=2)}")
                    
                    if event_type == 'payment.authorized':
                        print("\n✅ TEST SUCCEEDED: Payment was authorized successfully!")
                        response_received = True
                        break
                    elif event_type == 'payment.failed':
                        print(f"\n❌ TEST FAILED: Payment authorization failed.")
                        print(f"Error: {payload.get('error')}")
                        print(f"Message: {payload.get('message')}")
                        response_received = True
                        break
                        
            if response_received:
                break
                
        if response_received:
            break
            
    if not response_received:
        print("\n\n⚠️ TEST INCONCLUSIVE: No response received within timeout period.")
        print("Check payment-service logs for more details.")

except KeyboardInterrupt:
    print("\nTest interrupted by user.")
finally:
    consumer.close()
    producer.close()
    print("\nTest completed. Kafka connections closed.")

print("\nTo check payment service logs, run:")
print(f"docker logs campusg-payment-service-1 | grep {CORRELATION_ID}")

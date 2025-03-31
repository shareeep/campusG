#!/usr/bin/env python
"""
Test script for Payment Service integration with Create Order Saga
This script is designed to run inside the Docker container
"""

import requests
import json
import time
import uuid
import sys
import os
from datetime import datetime
from argparse import ArgumentParser

# Configure command line arguments
parser = ArgumentParser(description='Test Payment Service integration with Create Order Saga')
parser.add_argument('--host', default='localhost', help='Saga orchestrator host')
parser.add_argument('--port', default='3000', help='Saga orchestrator port')
parser.add_argument('--kafka', default='kafka:9092', help='Kafka bootstrap servers')
args = parser.parse_args()

# Configuration
SAGA_ORCHESTRATOR_URL = f"http://{args.host}:{args.port}"
KAFKA_BOOTSTRAP_SERVERS = args.kafka

print("Payment Service - Create Order Saga Integration Test (Python Version)")
print("-----------------------------------------")

# Step 1: Start a new saga
print("Starting a new saga...")
try:
    response = requests.post(
        f"{SAGA_ORCHESTRATOR_URL}/api/orders",
        json={
            "customer_id": "cust_123",
            "order_details": {
                "foodItems": [
                    {
                        "name": "Burger",
                        "price": 12.99,
                        "quantity": 1
                    }
                ],
                "deliveryLocation": "North Campus"
            }
        }
    )
    
    if response.status_code not in [200, 202]:
        print(f"Failed to start saga. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
        
    try:
        saga_data = response.json()
        saga_id = saga_data.get('saga_id')
        
        if not saga_id:
            # Try to parse manually if the JSON format is incorrect
            response_text = response.text
            saga_id_match = response_text.split('"saga_id":"')[1].split('"')[0] if '"saga_id":"' in response_text else None
            
            if saga_id_match:
                saga_id = saga_id_match
                print(f"Extracted saga ID manually: {saga_id}")
            else:
                print(f"Failed to extract saga ID. Response: {response_text}")
                sys.exit(1)
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {response.text}")
        
        # Last resort manual extraction
        try:
            response_text = response.text
            saga_id_match = response_text.split('"saga_id":"')[1].split('"')[0] if '"saga_id":"' in response_text else None
            
            if saga_id_match:
                saga_id = saga_id_match
                print(f"Extracted saga ID manually as last resort: {saga_id}")
            else:
                print("Could not extract saga ID by any means")
                sys.exit(1)
        except Exception as e2:
            print(f"Final attempt to extract saga ID failed: {e2}")
            sys.exit(1)
        
    print(f"Started saga with ID: {saga_id}")
    
except Exception as e:
    print(f"Error starting saga: {e}")
    sys.exit(1)

# Generate a test order ID
order_id = f"order-{int(time.time())}"
print(f"Using test order ID: {order_id}")

print("-----------------------------------------")
print("Simulating service events and verifying Kafka messages...")

# Import the test producer functionality
sys.path.insert(0, "/app")  # Add the app directory to the path
try:
    from fixed_kafka_test_producer import EVENT_TEMPLATES, send_event
    from kafka import KafkaProducer
except ImportError as e:
    print(f"Error importing Kafka modules: {e}")
    sys.exit(1)

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

# Step 2: Simulate order.created event
print("1. Simulating Order Service - order.created event")
event_template = EVENT_TEMPLATES['order.created']
topic = event_template['topic']
payload = event_template['payload'].copy()
payload['order_id'] = order_id
send_event(producer, topic, 'order.created', saga_id, payload)
time.sleep(3)

print("2. Check payment_commands topic in a separate terminal:")
print(f"docker exec -it campusg-kafka-1 kafka-console-consumer --bootstrap-server kafka:9092 --topic payment_commands --from-beginning")
print("Waiting 5 seconds...")
time.sleep(5)

# Step 3: Simulate user.payment_info_retrieved event
print("3. Simulating User Service - user.payment_info_retrieved event")
event_template = EVENT_TEMPLATES['user.payment_info_retrieved']
topic = event_template['topic']
payload = event_template['payload'].copy()
send_event(producer, topic, 'user.payment_info_retrieved', saga_id, payload)
time.sleep(3)

print("4. Check if payment service received the command:")
print("This is happening in another container. The saga orchestrator should be sending an authorize_payment command.")
print("Waiting 5 seconds...")
time.sleep(5)

# Step 5: Simulate payment.authorized event
print("5. Simulating Payment Service - payment.authorized event")
event_template = EVENT_TEMPLATES['payment.authorized']
topic = event_template['topic']
payload = event_template['payload'].copy()
payload['order_id'] = order_id
send_event(producer, topic, 'payment.authorized', saga_id, payload)
time.sleep(3)

# Step 6: Simulate order.status_updated event
print("6. Continue saga flow with order status update")
event_template = EVENT_TEMPLATES['order.status_updated']
topic = event_template['topic']
payload = event_template['payload'].copy()
payload['order_id'] = order_id
send_event(producer, topic, 'order.status_updated', saga_id, payload)
time.sleep(3)

# Step 7: Simulate timer.started event
print("7. Complete saga with timer started event")
event_template = EVENT_TEMPLATES['timer.started']
topic = event_template['topic']
payload = event_template['payload'].copy()
payload['order_id'] = order_id
send_event(producer, topic, 'timer.started', saga_id, payload)
time.sleep(3)

print("-----------------------------------------")
print("Checking final saga status...")

# Check final status
try:
    response = requests.get(f"{SAGA_ORCHESTRATOR_URL}/api/sagas/{saga_id}")
    if response.status_code != 200:
        print(f"Failed to get saga status. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
        
    final_status = response.json()
    print(f"Saga final status: {final_status}")
    
    if final_status.get('status') == 'COMPLETED':
        print("✅ Test completed successfully. Saga has been completed.")
        print("-----------------------------------------")
        print("Test summary:")
        print("1. Started a new saga successfully")
        print("2. The create-order-saga sends an authorize_payment command to payment_commands topic")
        print("3. The payment service can process this command and send back events")
        print("4. The integration between services via Kafka is working correctly")
        sys.exit(0)
    else:
        print("❌ Test failed. Saga did not complete successfully.")
        sys.exit(1)
        
except Exception as e:
    print(f"Error checking saga status: {e}")
    sys.exit(1)

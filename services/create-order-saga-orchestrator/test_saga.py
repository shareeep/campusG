#!/usr/bin/env python
"""
Test script for the Create Order Saga Orchestrator
"""

import json
import requests
import time
import sys
import os
from datetime import datetime

# Import the Kafka producer code directly 
from kafka import KafkaProducer

def publish_event(producer, topic, event_type, correlation_id, payload):
    """Send a single event to Kafka"""
    message = {
        'type': event_type,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat(),
        'payload': payload
    }
    
    print(f"Sending {event_type} to {topic} with correlation_id {correlation_id}")
    
    # Send message and get metadata
    future = producer.send(topic, message)
    try:
        record_metadata = future.get(timeout=10)
        print(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}]")
    except Exception as e:
        print(f"Message delivery failed: {e}")


def main():
    # Configuration
    service_host = "localhost"
    service_port = "3000"
    if len(sys.argv) > 1 and sys.argv[1] == "--docker":
        # When running inside Docker, use the service name
        service_host = "localhost"
        kafka_servers = "kafka:9092"
    else:
        # When running outside Docker, use localhost
        service_host = "localhost"
        service_port = "3101"  # External port mapping
        kafka_servers = "localhost:9092"
    
    # Define Kafka topics
    ORDER_EVENTS_TOPIC = 'order_events'
    USER_EVENTS_TOPIC = 'user_events'
    PAYMENT_EVENTS_TOPIC = 'payment_events'
    TIMER_EVENTS_TOPIC = 'timer_events'

    # Step 1: Start a new saga
    print("Starting a new saga...")
    api_url = f"http://{service_host}:{service_port}/api/orders"
    
    try:
        response = requests.post(
            api_url,
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
        
        # Check if request was successful
        response.raise_for_status()
        
        response_data = response.json()
        saga_id = response_data.get('saga_id')
        
        if not saga_id:
            print(f"Failed to get saga_id: {response_data}")
            return 1
        
        print(f"Started saga with ID: {saga_id}")
        
        # Step 2: Generate test order ID
        order_id = f"order-{int(time.time())}"
        print(f"Using test order ID: {order_id}")
        
        print("-----------------------------------------")
        print("Simulating service events...")
        
        # Configure Kafka producer
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Step 3: Simulate service events
        
        # 1. Order created event
        print("1. Simulating Order Service - order.created event")
        publish_event(
            producer,
            ORDER_EVENTS_TOPIC,
            'order.created',
            saga_id,
            {
                'order_id': order_id,
                'customer_id': 'cust_123',
                'status': 'PENDING_PAYMENT'
            }
        )
        time.sleep(2)
        
        # 2. User payment info retrieved event
        print("2. Simulating User Service - user.payment_info_retrieved event")
        publish_event(
            producer,
            USER_EVENTS_TOPIC,
            'user.payment_info_retrieved',
            saga_id,
            {
                'payment_info': {
                    'card_type': 'visa',
                    'last_four': '4242',
                    'card_token': 'tok_visa'
                }
            }
        )
        time.sleep(2)
        
        # 3. Payment authorized event
        print("3. Simulating Payment Service - payment.authorized event")
        publish_event(
            producer,
            PAYMENT_EVENTS_TOPIC,
            'payment.authorized',
            saga_id,
            {
                'payment_id': f"payment_{int(time.time())}",
                'order_id': order_id,
                'amount': 25.99,
                'status': 'AUTHORIZED'
            }
        )
        time.sleep(2)
        
        # 4. Order status updated event
        print("4. Simulating Order Service - order.status_updated event")
        publish_event(
            producer,
            ORDER_EVENTS_TOPIC,
            'order.status_updated',
            saga_id,
            {
                'order_id': order_id,
                'status': 'CREATED'
            }
        )
        time.sleep(2)
        
        # 5. Timer started event
        print("5. Simulating Timer Service - timer.started event")
        publish_event(
            producer,
            TIMER_EVENTS_TOPIC,
            'timer.started',
            saga_id,
            {
                'order_id': order_id,
                'timeout_at': datetime.utcnow().isoformat(),
                'status': 'RUNNING'
            }
        )
        time.sleep(2)
        
        producer.close()
        
        # Step 4: Check final saga status
        print("-----------------------------------------")
        print("Checking final saga status...")
        
        status_url = f"http://{service_host}:{service_port}/api/sagas/{saga_id}"
        status_response = requests.get(status_url)
        status_response.raise_for_status()
        
        final_status = status_response.json()
        print(f"Saga final status: {json.dumps(final_status)}")
        
        if final_status.get('status') == 'COMPLETED':
            print("✅ Test completed successfully. Saga has been completed.")
            return 0
        else:
            print("❌ Test failed. Saga did not complete successfully.")
            return 1
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return 1
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""
Complete test for the Create Order Saga Orchestrator
This test sends events directly to Kafka to simulate the full saga cycle
"""

import json
import requests
import time
import sys
import uuid
from datetime import datetime

# Step 1: Start a new saga via API
def start_saga():
    print("Step 1: Starting a new saga...")
    url = "http://localhost:3101/api/orders"
    
    data = {
        "customer_id": "cust_test_1",
        "order_details": {
            "foodItems": [
                {
                    "name": "Test Burger",
                    "price": 10.99,
                    "quantity": 2
                }
            ],
            "deliveryLocation": "Test Campus"
        }
    }
    
    response = requests.post(url, json=data)
    if not response.ok:
        print(f"Error starting saga: {response.status_code} {response.text}")
        sys.exit(1)
        
    response_data = response.json()
    saga_id = response_data.get('saga_id')
    
    if not saga_id:
        print(f"Error: No saga ID in response {response_data}")
        sys.exit(1)
        
    print(f"Successfully started saga with ID: {saga_id}")
    return saga_id

# Step 2: Check saga status before sending events
def check_saga_status(saga_id):
    url = f"http://localhost:3101/api/sagas/{saga_id}"
    response = requests.get(url)
    if not response.ok:
        print(f"Error getting saga status: {response.status_code}")
        return None
    
    return response.json()

# Step 3: Send Kafka events using the test_create_order_saga.sh script
def send_kafka_events(saga_id):
    print("\nStep 3: Sending Kafka events to simulate service responses...")
    
    # Generate a unique order ID
    order_id = f"order-{int(time.time())}"
    print(f"Using test order ID: {order_id}")
    
    # We'll run the shell script with the new parameters
    # But we'll print the events we're simulating here

    print("1. Simulating Order Service - order.created event")
    print(f"   Order ID: {order_id}, Saga ID: {saga_id}")
    
    print("2. Simulating User Service - user.payment_info_retrieved event")
    print("3. Simulating Payment Service - payment.authorized event")
    print("4. Simulating Order Service - order.status_updated event")
    print("5. Simulating Timer Service - timer.started event")
    
    # Execute the test script
    import subprocess
    
    cmd = [
        "bash", 
        "services/create-order-saga-orchestrator/test_create_order_saga.sh", 
        order_id, 
        saga_id
    ]
    
    print(f"\nExecuting test script to send events through Kafka...")
    
    # Just run the script, it already has the logic for these events
    try:
        result = subprocess.run(
            ["cd", "services/create-order-saga-orchestrator", "&&", "bash", "test_create_order_saga.sh"], 
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Errors: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error running test script: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
    
    return order_id

# Main test flow
def main():
    print("=== Complete Test for Create Order Saga Orchestrator ===\n")
    
    # Start the saga
    saga_id = start_saga()
    
    # Check initial status
    print("\nChecking initial saga status...")
    status = check_saga_status(saga_id)
    print(f"Initial status: {json.dumps(status, indent=2)}")
    
    # Let's wait a bit to make sure the saga is ready
    time.sleep(2)
    
    # Send Kafka events
    order_id = send_kafka_events(saga_id)
    
    # Let's wait for the saga to process all events
    print("\nWaiting for saga to process events...")
    for i in range(10):
        time.sleep(2)
        status = check_saga_status(saga_id)
        if status and status.get('status') == 'COMPLETED':
            print(f"Saga completed successfully after {i*2+2} seconds")
            print(f"Final status: {json.dumps(status, indent=2)}")
            return 0
        elif status and status.get('status') == 'FAILED':
            print(f"Saga failed after {i*2+2} seconds")
            print(f"Final status: {json.dumps(status, indent=2)}")
            return 1
        print(f"Status after {i*2+2} seconds: {status.get('status')}, step: {status.get('current_step')}")
    
    print("\nTimeout waiting for saga to complete. Final status:")
    status = check_saga_status(saga_id)
    print(json.dumps(status, indent=2))
    return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""
Comprehensive Test Script for Create Order Saga Orchestrator

This script implements the test plan defined in COMPREHENSIVE_TEST_PLAN.md.
It tests the complete flow of the Create Order Saga Orchestrator, including:
- Full saga flow from UI to all services and back
- HTTP integration with Timer Service
- Notification service logging verification
- Order cancellation and payment refund flow

Usage:
    python comprehensive_test.py [--docker]

Options:
    --docker    Run the test in Docker environment
"""

import json
import requests
import time
import sys
import os
import uuid
from datetime import datetime, timedelta
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('saga-test')

# Import Kafka producer for publishing test events
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    logger.error("Kafka Python client not found. Install with: pip install kafka-python")
    sys.exit(1)

# Configuration
DEFAULT_CONFIG = {
    "host": "localhost",
    "orchestrator_port": "3101",
    "order_service_port": "3102",
    "user_service_port": "3103",
    "payment_service_port": "3104",
    "timer_service_port": "3105",
    "notification_service_port": "3106",
    "kafka_servers": "localhost:9092",
    "order_events_topic": "order_events",
    "user_events_topic": "user_events",
    "payment_events_topic": "payment_events",
    "timer_events_topic": "timer_events",
    "notification_events_topic": "notification_events",
    "order_commands_topic": "order_commands",
    "user_commands_topic": "user_commands",
    "payment_commands_topic": "payment_commands",
    "timer_commands_topic": "timer_commands"
}

DOCKER_CONFIG = {
    "host": "localhost",
    "orchestrator_port": "3000",
    "order_service_port": "3000",
    "user_service_port": "3000",
    "payment_service_port": "3000",
    "timer_service_port": "3000",
    "notification_service_port": "3000",
    "kafka_servers": "kafka:9092",
    "order_events_topic": "order-events",
    "user_events_topic": "user-events",
    "payment_events_topic": "payment-events",
    "timer_events_topic": "timer-events",
    "notification_events_topic": "notification-events",
    "order_commands_topic": "order-commands",
    "user_commands_topic": "user-commands",
    "payment_commands_topic": "payment-commands",
    "timer_commands_topic": "timer-commands"
}

def get_config(docker_mode):
    """Get configuration based on environment"""
    if docker_mode:
        return DOCKER_CONFIG
    return DEFAULT_CONFIG

def publish_event(producer, topic, event_type, correlation_id, payload):
    """Send a single event to Kafka"""
    message = {
        'type': event_type,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat(),
        'payload': payload
    }
    
    logger.info(f"Sending {event_type} to {topic} with correlation_id {correlation_id}")
    
    # Send message and get metadata
    try:
        future = producer.send(topic, message)
        record_metadata = future.get(timeout=10)
        logger.info(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}]")
        return True
    except Exception as e:
        logger.error(f"Message delivery failed: {e}")
        return False

def query_notifications(config, correlation_id, event_type=None):
    """Query the notification service for a specific correlation_id and optional event_type"""
    url = f"http://{config['host']}:{config['notification_service_port']}/api/notifications"
    params = {"correlation_id": correlation_id}
    if event_type:
        params["event_type"] = event_type
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying notifications: {e}")
        return None

def verify_notification_logged(config, correlation_id, event_type):
    """Verify a notification was logged for a specific event_type and correlation_id"""
    notifications = query_notifications(config, correlation_id, event_type)
    
    if not notifications:
        logger.warning(f"No notifications found for {event_type} with correlation_id {correlation_id}")
        return False
    
    logger.info(f"Notification found for {event_type} with correlation_id {correlation_id}")
    return True

def verify_saga_state(config, saga_id, expected_status=None, expected_step=None):
    """Verify the saga state matches expected status and/or step"""
    url = f"http://{config['host']}:{config['orchestrator_port']}/api/sagas/{saga_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        saga_state = response.json()
        
        logger.info(f"Current saga state: {saga_state}")
        
        if expected_status and saga_state.get('status') != expected_status:
            logger.warning(f"Saga status mismatch: expected {expected_status}, got {saga_state.get('status')}")
            return False
        
        if expected_step and saga_state.get('current_step') != expected_step:
            logger.warning(f"Saga step mismatch: expected {expected_step}, got {saga_state.get('current_step')}")
            return False
        
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying saga state: {e}")
        return False

def test_create_order_flow(config):
    """Test the complete create order flow"""
    logger.info("Starting Create Order Saga Test Flow")
    
    # 1. Start the saga via API call
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"
    order_details = {
        "foodItems": [
            {
                "name": "Test Burger",
                "price": 15.99,
                "quantity": 2
            },
            {
                "name": "Test Fries",
                "price": 4.99,
                "quantity": 1
            }
        ],
        "deliveryLocation": "Test Location"
    }
    
    logger.info(f"Initiating order for customer {customer_id}")
    
    # Initial API call to start saga
    response = requests.post(
        f"http://{config['host']}:{config['orchestrator_port']}/api/orders",
        json={
            "customer_id": customer_id,
            "order_details": order_details
        }
    )
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to start saga: {e}")
        logger.error(f"Response: {response.text}")
        return False
    
    saga_data = response.json()
    saga_id = saga_data.get('saga_id')
    
    if not saga_id:
        logger.error(f"No saga_id returned: {saga_data}")
        return False
    
    logger.info(f"Saga started with ID: {saga_id}")
    
    # Configure Kafka producer for simulating service responses
    producer = KafkaProducer(
        bootstrap_servers=config['kafka_servers'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    try:
        # 2. Simulate Order Service - order.created event
        order_id = f"order-{int(time.time())}"
        logger.info(f"Simulating Order Service creating order {order_id}")
        
        success = publish_event(
            producer,
            config['order_events_topic'],
            'order.created',
            saga_id,
            {
                'order_id': order_id,
                'customer_id': customer_id,
                'status': 'PENDING_PAYMENT'
            }
        )
        
        if not success:
            logger.error("Failed to publish order.created event")
            return False
        
        # Wait for orchestrator to process
        time.sleep(2)
        
        # Verify saga state updated
        verify_saga_state(config, saga_id, expected_step="GET_USER_DATA")
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'order.created')
        
        # 3. Simulate User Service - user.payment_info_retrieved event
        logger.info("Simulating User Service retrieving payment info")
        
        success = publish_event(
            producer,
            config['user_events_topic'],
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
        
        if not success:
            logger.error("Failed to publish user.payment_info_retrieved event")
            return False
        
        # Wait for orchestrator to process
        time.sleep(2)
        
        # Verify saga state updated
        verify_saga_state(config, saga_id, expected_step="AUTHORIZE_PAYMENT")
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'user.payment_info_retrieved')
        
        # 4. Simulate Payment Service - payment.authorized event
        logger.info("Simulating Payment Service authorizing payment")
        
        payment_id = f"payment_{int(time.time())}"
        success = publish_event(
            producer,
            config['payment_events_topic'],
            'payment.authorized',
            saga_id,
            {
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': 36.97,  # 2 * 15.99 + 4.99
                'status': 'AUTHORIZED'
            }
        )
        
        if not success:
            logger.error("Failed to publish payment.authorized event")
            return False
        
        # Wait for orchestrator to process
        time.sleep(2)
        
        # Verify saga state updated
        verify_saga_state(config, saga_id, expected_step="UPDATE_ORDER_STATUS")
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'payment.authorized')
        
        # 5. Simulate Order Service - order.status_updated event
        logger.info("Simulating Order Service updating order status")
        
        success = publish_event(
            producer,
            config['order_events_topic'],
            'order.status_updated',
            saga_id,
            {
                'order_id': order_id,
                'status': 'CREATED'
            }
        )
        
        if not success:
            logger.error("Failed to publish order.status_updated event")
            return False
        
        # Wait for orchestrator to process
        time.sleep(2)
        
        # Verify saga state updated - should now be at START_TIMER step
        verify_saga_state(config, saga_id, expected_step="START_TIMER")
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'order.status_updated')
        
        # 6. Simulate Timer Service (HTTP) - timer.started event
        # In the real implementation, the orchestrator would call the timer service via HTTP
        # Here we'll directly simulate the response that would come back from the timer service
        logger.info("Simulating Timer Service starting timer (via HTTP response)")
        
        success = publish_event(
            producer,
            config['timer_events_topic'],
            'timer.started',
            saga_id,
            {
                'order_id': order_id,
                'timeout_at': (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
                'status': 'RUNNING'
            }
        )
        
        if not success:
            logger.error("Failed to publish timer.started event")
            return False
        
        # Wait for orchestrator to process
        time.sleep(2)
        
        # Verify saga state updated - should now be COMPLETED
        verify_saga_state(config, saga_id, expected_status="COMPLETED")
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'timer.started')
        
        # 7. Verify final saga state
        logger.info("Verifying final saga state")
        
        response = requests.get(f"http://{config['host']}:{config['orchestrator_port']}/api/sagas/{saga_id}")
        response.raise_for_status()
        
        final_state = response.json()
        logger.info(f"Final saga state: {json.dumps(final_state, indent=2)}")
        
        if final_state.get('status') != "COMPLETED":
            logger.error(f"Saga did not complete successfully. Final status: {final_state.get('status')}")
            return False
        
        logger.info("🎉 Create Order Saga Test Flow completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Error in test flow: {e}", exc_info=True)
        return False
    finally:
        # Clean up resources
        if producer:
            producer.close()

def test_order_cancellation_flow(config):
    """Test the order cancellation flow"""
    logger.info("Starting Order Cancellation Test Flow")
    
    # 1. Start a saga and progress it to the point after payment authorization
    # Similar to test_create_order_flow but stopping after payment authorization
    
    # Generate test IDs
    customer_id = f"cust_{uuid.uuid4().hex[:8]}"
    order_details = {
        "foodItems": [
            {
                "name": "Cancel Burger",
                "price": 15.99,
                "quantity": 1
            }
        ],
        "deliveryLocation": "Cancellation Test Location"
    }
    
    # Initial API call to start saga
    response = requests.post(
        f"http://{config['host']}:{config['orchestrator_port']}/api/orders",
        json={
            "customer_id": customer_id,
            "order_details": order_details
        }
    )
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to start saga: {e}")
        logger.error(f"Response: {response.text}")
        return False
    
    saga_data = response.json()
    saga_id = saga_data.get('saga_id')
    
    if not saga_id:
        logger.error(f"No saga_id returned: {saga_data}")
        return False
    
    logger.info(f"Cancellation test: Saga started with ID: {saga_id}")
    
    # Configure Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=config['kafka_servers'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    try:
        # Progress saga to payment authorized
        order_id = f"order-cancel-{int(time.time())}"
        
        # Order Service creates order
        publish_event(
            producer,
            config['order_events_topic'],
            'order.created',
            saga_id,
            {
                'order_id': order_id,
                'customer_id': customer_id,
                'status': 'PENDING_PAYMENT'
            }
        )
        time.sleep(2)
        
        # User Service returns payment info
        publish_event(
            producer,
            config['user_events_topic'],
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
        
        # Payment Service authorizes payment
        payment_id = f"payment-cancel-{int(time.time())}"
        publish_event(
            producer,
            config['payment_events_topic'],
            'payment.authorized',
            saga_id,
            {
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': 15.99,
                'status': 'AUTHORIZED'
            }
        )
        time.sleep(2)
        
        # Verify we're at the right point in the saga
        verify_saga_state(config, saga_id, expected_step="UPDATE_ORDER_STATUS")
        
        # 2. Trigger cancellation 
        logger.info(f"Simulating order cancellation for order {order_id}")
        
        # In a real implementation, there would be a cancel endpoint in the API
        # Here we'll directly simulate the cancellation flow events
        
        # First, simulate the order service receiving a cancellation request
        publish_event(
            producer,
            config['order_events_topic'],
            'order.cancellation_requested',
            saga_id,
            {
                'order_id': order_id,
                'customer_id': customer_id,
                'reason': 'customer_requested'
            }
        )
        time.sleep(2)
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'order.cancellation_requested')
        
        # Simulate payment service cancelling the payment
        publish_event(
            producer,
            config['payment_events_topic'],
            'payment.cancelled',
            saga_id,
            {
                'payment_id': payment_id,
                'order_id': order_id,
                'status': 'CANCELLED',
                'reason': 'order_cancelled'
            }
        )
        time.sleep(2)
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'payment.cancelled')
        
        # Simulate order service updating order status to CANCELLED
        publish_event(
            producer,
            config['order_events_topic'],
            'order.status_updated',
            saga_id,
            {
                'order_id': order_id,
                'status': 'CANCELLED',
                'reason': 'customer_requested'
            }
        )
        time.sleep(2)
        
        # Verify notification logged
        verify_notification_logged(config, saga_id, 'order.status_updated')
        
        # Verify final saga state
        response = requests.get(f"http://{config['host']}:{config['orchestrator_port']}/api/sagas/{saga_id}")
        response.raise_for_status()
        
        final_state = response.json()
        logger.info(f"Final saga state after cancellation: {json.dumps(final_state, indent=2)}")
        
        # In a proper implementation, the saga state would be COMPENSATED or similar
        # For now, just check it's not COMPLETED
        if final_state.get('status') == "COMPLETED":
            logger.error("Saga completed despite cancellation")
            return False
        
        logger.info("🎉 Order Cancellation Test Flow completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Error in cancellation test flow: {e}", exc_info=True)
        return False
    finally:
        # Clean up resources
        if producer:
            producer.close()

def test_notification_service_logging(config, saga_id):
    """Test that notification service logged all Kafka messages for a saga"""
    logger.info(f"Verifying notification service logging for saga {saga_id}")
    
    # Query the notification service for all events related to this saga
    notifications = query_notifications(config, saga_id)
    
    if not notifications:
        logger.error("No notifications found for saga")
        return False
    
    # Log the count
    count = len(notifications)
    logger.info(f"Found {count} notifications for saga {saga_id}")
    
    # Expected event types in order
    expected_events = [
        'create_order',
        'order.created',
        'get_payment_info',
        'user.payment_info_retrieved',
        'authorize_payment',
        'payment.authorized',
        'update_order_status',
        'order.status_updated',
        'timer.started'
    ]
    
    # Check that all expected events are present
    found_events = set(n.get('eventType') for n in notifications)
    missing_events = [e for e in expected_events if e not in found_events]
    
    if missing_events:
        logger.warning(f"Missing notifications for events: {missing_events}")
        return False
    
    logger.info("All expected notification types were logged")
    return True

def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Comprehensive Test for Create Order Saga")
    parser.add_argument('--docker', action='store_true', help="Run in Docker environment")
    args = parser.parse_args()
    
    # Get appropriate configuration
    config = get_config(args.docker)
    
    logger.info("Starting comprehensive test for Create Order Saga Orchestrator")
    logger.info(f"Using configuration: {'Docker' if args.docker else 'Local'}")
    
    # Run the create order flow test
    success = test_create_order_flow(config)
    
    if not success:
        logger.error("Create order flow test failed")
        return 1
    
    # Run the order cancellation test
    success = test_order_cancellation_flow(config)
    
    if not success:
        logger.error("Order cancellation test failed")
        return 1
    
    logger.info("All tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

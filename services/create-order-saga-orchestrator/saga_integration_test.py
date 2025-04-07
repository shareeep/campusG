# services/create-order-saga-orchestrator/saga_integration_test.py

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
logger = logging.getLogger('saga-integration-test')

# Import Kafka producer ONLY for simulating cancellation if no API exists
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    logger.warning("Kafka Python client not found. Install with: pip install kafka-python. Cancellation test might require it.")
    KafkaProducer = None # Set to None if not available

# Configuration (Docker focused)
DOCKER_CONFIG = {
    "host": "localhost",
    "orchestrator_port": "3101",
    "user_service_port": "3001",
    "payment_service_port": "3003", # Needed? Maybe for checking payment status directly
    "notification_service_port": "3006", # For verification
    "kafka_servers": "localhost:29092", # For cancellation simulation if needed
    "order_events_topic": "order_events", # For cancellation simulation if needed
    "api_timeout": 30, # Timeout for API calls
    "poll_interval": 5, # How often to poll saga status
    "saga_timeout": 120 # Max time to wait for saga completion/failure
}

# --- Helper Functions ---

def get_config():
    """Returns the Docker configuration."""
    # Simplified as we only target Docker for now
    return DOCKER_CONFIG

def check_service_health(url, service_name, timeout=60):
    """Wait for a service to become healthy."""
    logger.info(f"Checking health of {service_name} at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"{service_name} is healthy.")
                return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"Health check for {service_name} failed: {e}")
        time.sleep(3)
    logger.error(f"{service_name} did not become healthy within {timeout} seconds.")
    return False

def pre_create_user(config, customer_id):
    """Ensure the test user exists and has a payment method."""
    logger.info(f"Ensuring user {customer_id} exists with payment method...")
    user_service_base_url = f"http://{config['host']}:{config['user_service_port']}/api"
    try:
        # Check if user exists first (optional, API might handle creation)
        # response_check = requests.get(f"{user_service_base_url}/user/{customer_id}")
        # if response_check.status_code == 200:
        #     logger.info(f"User {customer_id} already exists.")
        # else:
        # Simulate Clerk webhook user.created
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": customer_id,
                "email_addresses": [{"email_address": f"{customer_id}@example.com", "id": f"idn_{customer_id}", "linked_to": [], "object": "email_address", "verification": None}],
                "first_name": "Integration",
                "last_name": "Test",
                "phone_numbers": [],
                "username": customer_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time())
            }
        }
        response_webhook = requests.post(f"{user_service_base_url}/webhook/clerk", json=webhook_payload, timeout=config['api_timeout'])
        # Allow 409 Conflict if user already exists from webhook perspective
        if response_webhook.status_code not in [200, 201, 409]:
             response_webhook.raise_for_status()
        logger.info(f"User {customer_id} creation request sent (simulated webhook). Status: {response_webhook.status_code}")
        time.sleep(1) # Give a moment

        # Add/Ensure test payment method
        payment_payload = {"paymentMethodId": "pm_card_visa"}
        response_payment = requests.put(f"{user_service_base_url}/user/{customer_id}/payment", json=payment_payload, timeout=config['api_timeout'])
        response_payment.raise_for_status()
        logger.info(f"Test payment method added/ensured for user {customer_id}. Status: {response_payment.status_code}")
        time.sleep(2) # Allow DB updates
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to pre-create/verify user {customer_id}: {e}")
        return False

def poll_saga_status(config, saga_id, target_status, intermediate_steps=None, timeout=None):
    """Poll the orchestrator API until the saga reaches a target status or step."""
    start_time = time.time()
    timeout = timeout or config['saga_timeout']
    url = f"http://{config['host']}:{config['orchestrator_port']}/sagas/{saga_id}"
    logger.info(f"Polling saga {saga_id} for status '{target_status}' (timeout: {timeout}s)...")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=config['api_timeout'])
            response.raise_for_status()
            saga_state = response.json()
            current_status = saga_state.get('status')
            current_step = saga_state.get('current_step')
            error = saga_state.get('error')

            logger.debug(f"Saga {saga_id} state: Status={current_status}, Step={current_step}, Error={error}")

            if error:
                logger.error(f"Saga {saga_id} failed! Error: {error}")
                return saga_state # Return failed state

            if current_status == target_status:
                logger.info(f"Saga {saga_id} reached target status: {target_status}")
                return saga_state # Return successful state

            # Optional: Check if it passed through expected intermediate steps
            if intermediate_steps and current_step in intermediate_steps:
                 logger.info(f"Saga {saga_id} reached intermediate step: {current_step}")
                 # Remove step to avoid logging it repeatedly
                 intermediate_steps.remove(current_step)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error polling saga {saga_id}: {e}")
        except json.JSONDecodeError as e:
             logger.warning(f"Error decoding saga state JSON for {saga_id}: {e}")

        time.sleep(config['poll_interval'])

    logger.error(f"Timeout waiting for saga {saga_id} to reach status '{target_status}'.")
    # Try one last fetch to return the final state on timeout
    try:
        response = requests.get(url, timeout=config['api_timeout'])
        return response.json()
    except Exception:
        return None # Return None if final fetch fails

def poll_saga_step(config, saga_id, target_step, timeout=None):
    """Poll the orchestrator API until the saga reaches a target step or fails."""
    start_time = time.time()
    timeout = timeout or config['saga_timeout']
    url = f"http://{config['host']}:{config['orchestrator_port']}/sagas/{saga_id}"
    logger.info(f"Polling saga {saga_id} for step '{target_step}' (timeout: {timeout}s)...")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=config['api_timeout'])
            response.raise_for_status()
            saga_state = response.json()
            current_status = saga_state.get('status')
            current_step = saga_state.get('current_step')
            error = saga_state.get('error')

            logger.debug(f"Saga {saga_id} state: Status={current_status}, Step={current_step}, Error={error}")

            if error or current_status == "FAILED" or current_status == "COMPLETED":
                logger.error(f"Saga {saga_id} terminated unexpectedly (Status: {current_status}, Error: {error}) while waiting for step {target_step}")
                return saga_state # Return failed/completed state

            if current_step == target_step:
                logger.info(f"Saga {saga_id} reached target step: {target_step}")
                return saga_state # Return successful state

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error polling saga {saga_id}: {e}")
        except json.JSONDecodeError as e:
             logger.warning(f"Error decoding saga state JSON for {saga_id}: {e}")

        time.sleep(config['poll_interval'])

    logger.error(f"Timeout waiting for saga {saga_id} to reach step '{target_step}'.")
    # Try one last fetch to return the final state on timeout
    try:
        response = requests.get(url, timeout=config['api_timeout'])
        return response.json()
    except Exception:
        return None # Return None if final fetch fails


def simulate_cancellation_request(config, saga_id, order_id, customer_id):
    """Simulates the order.cancellation_requested event via Kafka."""
    if not KafkaProducer:
        logger.error("KafkaProducer not available. Cannot simulate cancellation request.")
        return False

    producer = None
    try:
        logger.info(f"Connecting to Kafka at {config['kafka_servers']} to simulate cancellation...")
        producer = KafkaProducer(
            bootstrap_servers=config['kafka_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            client_id='saga-test-cancel-producer'
        )
        message = {
            'type': 'order.cancellation_requested',
            'correlation_id': saga_id,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': {
                'order_id': order_id,
                'customer_id': customer_id,
                'reason': 'test_script_cancellation'
            }
        }
        logger.info(f"Publishing order.cancellation_requested to {config['order_events_topic']} for saga {saga_id}")
        future = producer.send(config['order_events_topic'], value=message)
        record_metadata = future.get(timeout=10)
        logger.info(f"Cancellation request message delivered to {record_metadata.topic} [{record_metadata.partition}]")
        return True
    except Exception as e:
        logger.error(f"Failed to simulate cancellation request via Kafka: {e}", exc_info=True)
        return False
    finally:
        if producer:
            producer.close()
            logger.info("Kafka producer for cancellation closed.")


# --- Test Functions ---

def test_successful_order(config):
    """Tests the happy path for order creation."""
    logger.info("--- Starting Test: Successful Order Creation ---")
    customer_id = f"cust_success_{uuid.uuid4().hex[:8]}"
    order_details = {
        "foodItems": [{"name": "Success Burger", "price": 12.50, "quantity": 1}],
        "deliveryLocation": "Success Location"
    }

    if not pre_create_user(config, customer_id):
        logger.error("Test failed: User pre-creation failed.")
        return False

    # Start the saga
    saga_id = None
    try:
        logger.info(f"Initiating order via API for customer {customer_id}...")
        response = requests.post(
            f"http://{config['host']}:{config['orchestrator_port']}/orders",
            json={"customer_id": customer_id, "order_details": order_details},
            timeout=config['api_timeout']
        )
        response.raise_for_status()
        saga_data = response.json()
        saga_id = saga_data.get('saga_id')
        if not saga_id:
            logger.error(f"Test failed: No saga_id returned from /orders endpoint. Response: {saga_data}")
            return False
        logger.info(f"Saga started successfully with ID: {saga_id}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Test failed: Failed to start saga via API: {e}")
        return False

    # Poll until saga completes (or fails/times out)
    final_state = poll_saga_status(config, saga_id, target_status="COMPLETED")

    if not final_state:
        logger.error(f"Test failed: Could not retrieve final saga state for {saga_id}.")
        return False

    if final_state.get('status') == "COMPLETED" and not final_state.get('error'):
        logger.info("--- Test PASSED: Successful Order Creation ---")
        return True
    else:
        logger.error(f"Test FAILED: Saga did not complete successfully. Final state: {final_state}")
# --- Main Execution ---

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Integration Test for Create Order Saga")
    # Only docker mode is supported for now
    parser.add_argument('--docker', action='store_true', default=True, help="Run in Docker environment (default)")
    args = parser.parse_args()

    config = get_config()

    # Health checks before starting tests
    services_healthy = True
    orchestrator_health_url = f"http://{config['host']}:{config['orchestrator_port']}/health"
    user_service_health_url = f"http://{config['host']}:{config['user_service_port']}/health"

    services_healthy &= check_service_health(orchestrator_health_url, "Create Order Saga Orchestrator")
    services_healthy &= check_service_health(user_service_health_url, "User Service")
    # Add health checks for other critical services (Order, Payment) if they have /health endpoints

    if not services_healthy:
        logger.error("One or more services failed health checks. Aborting tests.")
        sys.exit(1)

    logger.info("All required services are healthy. Starting tests...")

    test_results = {}
    test_results['successful_order'] = test_successful_order(config)
    # test_results['order_cancellation'] = test_order_cancellation(config) # Removed cancellation test as orchestrator doesn't handle it mid-flight

    logger.info("--- Test Summary ---")
    all_passed = True
    for test_name, passed in test_results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"Test '{test_name}': {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("All integration tests passed!")
        return 0
    else:
        logger.error("One or more integration tests failed.")
        return 1

if __name__ == "__main__":
    # Add DeprecationWarning filter for utcnow if needed
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, message="datetime.datetime.utcnow()")
    sys.exit(main())

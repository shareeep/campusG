"""
HTTP Client for the Create Order Saga Orchestrator

This module provides HTTP client functionality for services
that require HTTP communication instead of Kafka.
"""

import json
import logging
import os
import uuid
import requests
from requests.exceptions import RequestException
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration - can be overridden with environment variables
TIMER_SERVICE_URL = os.getenv('TIMER_SERVICE_URL', 'https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI')
HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '5'))

# Custom JSON encoder to handle UUID objects
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID to string
            return str(obj)
        return super().default(obj)

class HttpClient:
    """HTTP client for external service communication"""
    
    def __init__(self, base_urls=None):
        """
        Initialize the HTTP client
        
        Args:
            base_urls (dict, optional): Dictionary of service URLs. Defaults to None.
        """
        self.base_urls = base_urls or {
            'timer': TIMER_SERVICE_URL,
            'order': os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
        }
        logger.info(f"Initialized HttpClient with base URLs: {self.base_urls}")
    
    def start_timer(self, order_id, customer_id, timeout_at, correlation_id):
        """
        Start a timer via HTTP request to the Timer Service
        
        Args:
            order_id (str): The ID of the order
            customer_id (str): The ID of the customer
            timeout_at (str): ISO8601 timestamp when the timer should trigger (not used by current API)
            correlation_id (str): Correlation ID for tracking (saga_id) (not used by current API)
            
        Returns:
            tuple: (success, response_data)
        """
        # Use the correct endpoint for the Timer Service
        timer_url = f"{self.base_urls['timer']}/StartTimer"
        
        # Convert any UUID objects to strings to ensure JSON serialization works
        if isinstance(order_id, uuid.UUID):
            order_id = str(order_id)
        if isinstance(customer_id, uuid.UUID):
            customer_id = str(customer_id)
        
        # Format the payload according to the API's expected format
        # Note: PascalCase field names and empty RunnerId
        payload = {
            'OrderId': order_id,
            'CustomerId': customer_id,
            'RunnerId': ""  # Empty string as required by the API
        }
        
        logger.info(f"Sending timer request to {timer_url} for order {order_id}")
        
        try:
            response = requests.post(
                timer_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=HTTP_TIMEOUT
            )
            
            # Check for success (2xx status code)
            if 200 <= response.status_code < 300:
                try:
                    response_data = response.json()
                except ValueError:
                    logger.warning(f"Timer service returned non-JSON response: {response.text}")
                    response_data = {"message": "Timer started (non-JSON response)"}
                
                logger.info(f"Timer service response: {response_data}")
                return True, response_data
            else:
                logger.error(f"Timer service returned error status: {response.status_code}, body: {response.text}")
                return False, {'error': f"HTTP {response.status_code}: {response.text}"}
            
        except RequestException as e:
            logger.error(f"HTTP error starting timer for order {order_id}: {str(e)}")
            return False, {'error': str(e)}
        except ValueError as e:
            logger.error(f"Invalid JSON response from timer service: {str(e)}")
            return False, {'error': 'Invalid response from timer service'}
        except Exception as e:
            logger.error(f"Unexpected error starting timer for order {order_id}: {str(e)}", exc_info=True)
            return False, {'error': str(e)}

    def get_timers_for_cancellation(self):
        """
        Poll the Timer Service to get timers eligible for cancellation check.
        
        Returns:
            tuple: (success, response_data) - response_data is a list of timers or error dict
        """
        poll_url = f"{self.base_urls['timer']}/GetTimersForCancellationCheck"
        logger.debug(f"Polling timer cancellation check URL: {poll_url}")
        
        try:
            response = requests.get(
                poll_url,
                headers={"Accept": "application/json"},
                timeout=HTTP_TIMEOUT
            )
            
            if 200 <= response.status_code < 300:
                try:
                    response_data = response.json()
                    # Ensure it's a list as expected from the API doc example
                    if not isinstance(response_data, list):
                         logger.error(f"Timer cancellation check returned non-list data: {response_data}")
                         return False, {'error': 'Invalid response format from timer service (expected list)'}
                    logger.debug(f"Timer cancellation check successful, received {len(response_data)} timers.")
                    return True, response_data
                except ValueError:
                    logger.error(f"Timer cancellation check returned non-JSON response: {response.text}")
                    return False, {'error': 'Invalid JSON response from timer service'}
            else:
                logger.error(f"Timer cancellation check returned error status: {response.status_code}, body: {response.text}")
                return False, {'error': f"HTTP {response.status_code}: {response.text}"}
                
        except RequestException as e:
            logger.error(f"HTTP error polling timer cancellation: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error polling timer cancellation: {str(e)}", exc_info=True)
            return False, {'error': str(e)}

    def get_order(self, order_id):
        """
        Get order details from the Order Service
        
        Args:
            order_id (str): The ID of the order to fetch
            
        Returns:
            tuple: (success, order_data) - order_data is the order details or error dict
        """
        # Ensure order_id is a string
        if isinstance(order_id, uuid.UUID):
            order_id = str(order_id)
            
        order_url = f"{self.base_urls['order']}/getOrderDetails?orderId={order_id}"
        logger.info(f"Fetching order details from {order_url}")
        
        try:
            response = requests.get(
                order_url,
                headers={"Accept": "application/json"},
                timeout=HTTP_TIMEOUT
            )
            
            if 200 <= response.status_code < 300:
                try:
                    response_data = response.json()
                    logger.info(f"Successfully fetched order {order_id}, status: {response_data.get('orderStatus')}")
                    return True, response_data
                except ValueError:
                    logger.error(f"Order service returned non-JSON response: {response.text}")
                    return False, {'error': 'Invalid JSON response from order service'}
            else:
                logger.error(f"Order service returned error status: {response.status_code}, body: {response.text}")
                return False, {'error': f"HTTP {response.status_code}: {response.text}"}
                
        except RequestException as e:
            logger.error(f"HTTP error fetching order {order_id}: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error fetching order {order_id}: {str(e)}", exc_info=True)
            return False, {'error': str(e)}
            
    def cancel_timer(self, order_id):
        """
        Request cancellation of a timer via HTTP to the Timer Service.
        
        Args:
            order_id (str): The ID of the order whose timer should be cancelled.
            
        Returns:
            tuple: (success, response_data)
        """
        cancel_url = f"{self.base_urls['timer']}/CancelTimer"
        
        if isinstance(order_id, uuid.UUID):
            order_id = str(order_id)
            
        payload = {'OrderId': order_id}
        
        logger.info(f"Sending timer cancellation request to {cancel_url} for order {order_id}")
        
        try:
            response = requests.post(
                cancel_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=HTTP_TIMEOUT
            )
            
            if 200 <= response.status_code < 300:
                try:
                    response_data = response.json()
                    # Check the 'Success' field in the response based on API doc
                    if response_data.get("Success") is True:
                        logger.info(f"Timer cancellation successful for order {order_id}: {response_data.get('Message')}")
                        return True, response_data
                    else:
                        logger.error(f"Timer cancellation failed for order {order_id} according to response: {response_data.get('Message')}")
                        return False, {'error': response_data.get('Message', 'Cancellation failed')}
                except ValueError:
                    logger.warning(f"Timer cancellation returned non-JSON response: {response.text}")
                    # Assume success if status code was 2xx but response wasn't JSON? Or treat as failure?
                    # Let's treat non-JSON as potential failure for safety.
                    return False, {'error': 'Invalid response from timer service (non-JSON)'}
            else:
                logger.error(f"Timer cancellation returned error status: {response.status_code}, body: {response.text}")
                return False, {'error': f"HTTP {response.status_code}: {response.text}"}
                
        except RequestException as e:
            logger.error(f"HTTP error cancelling timer for order {order_id}: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error cancelling timer for order {order_id}: {str(e)}", exc_info=True)
            return False, {'error': str(e)}


# Global HTTP client instance
http_client = HttpClient()

def init_http_client(config=None):
    """
    Initialize the HTTP client with optional configuration
    
    Args:
        config (dict, optional): Configuration with base URLs. Defaults to None.
        
    Returns:
        HttpClient: The initialized HTTP client
    """
    global http_client
    
    if config:
        base_urls = {
            'timer': config.get('TIMER_SERVICE_URL', TIMER_SERVICE_URL)
        }
        http_client = HttpClient(base_urls)
    
    logger.info("HTTP client initialized")
    return http_client

"""
HTTP Client for the Create Order Saga Orchestrator

This module provides HTTP client functionality for services
that require HTTP communication instead of Kafka.
"""

import json
import logging
import os
import requests
from requests.exceptions import RequestException
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration - can be overridden with environment variables
TIMER_SERVICE_URL = os.getenv('TIMER_SERVICE_URL', 'http://timer-service:3000')
HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '5'))

class HttpClient:
    """HTTP client for external service communication"""
    
    def __init__(self, base_urls=None):
        """
        Initialize the HTTP client
        
        Args:
            base_urls (dict, optional): Dictionary of service URLs. Defaults to None.
        """
        self.base_urls = base_urls or {
            'timer': TIMER_SERVICE_URL
        }
        logger.info(f"Initialized HttpClient with base URLs: {self.base_urls}")
    
    def start_timer(self, order_id, customer_id, timeout_at, correlation_id):
        """
        Start a timer via HTTP request to the Timer Service
        
        Args:
            order_id (str): The ID of the order
            customer_id (str): The ID of the customer
            timeout_at (str): ISO8601 timestamp when the timer should trigger
            correlation_id (str): Correlation ID for tracking (saga_id)
            
        Returns:
            tuple: (success, response_data)
        """
        timer_url = f"{self.base_urls['timer']}/api/timers"
        
        payload = {
            'order_id': order_id,
            'customer_id': customer_id,
            'timeout_at': timeout_at,
            'saga_id': correlation_id
        }
        
        logger.info(f"Sending timer request to {timer_url} for order {order_id}")
        
        try:
            response = requests.post(
                timer_url,
                json=payload,
                timeout=HTTP_TIMEOUT
            )
            
            # Check for success
            response.raise_for_status()
            
            response_data = response.json()
            logger.info(f"Timer service response: {response_data}")
            
            return True, response_data
            
        except RequestException as e:
            logger.error(f"HTTP error starting timer for order {order_id}: {str(e)}")
            return False, {'error': str(e)}
        except ValueError as e:
            logger.error(f"Invalid JSON response from timer service: {str(e)}")
            return False, {'error': 'Invalid response from timer service'}
        except Exception as e:
            logger.error(f"Unexpected error starting timer for order {order_id}: {str(e)}", exc_info=True)
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

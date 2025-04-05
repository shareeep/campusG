"""
Test script for verifying the Notification Service API endpoints

This script:
1. Sends a test notification via the API
2. Retrieves notifications for a specific order
3. Retrieves the latest notification for an order

Usage:
    python test_api.py

Requirements:
    - Notification service running and accessible
    - Python packages: requests
"""
import json
import logging
import sys
import time
import uuid
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:3000"  # Change if needed

def send_test_notification():
    """Send a test notification via the API"""
    
    # Generate unique IDs for testing
    order_id = f"test-order-{uuid.uuid4()}"
    customer_id = f"test-customer-{uuid.uuid4()}"
    runner_id = f"test-runner-{uuid.uuid4()}"
    
    # Create notification payload
    notification_data = {
        "customerId": customer_id,
        "runnerId": runner_id,
        "orderId": order_id,
        "event": f"Test notification created at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    try:
        logger.info(f"Sending test notification: {notification_data}")
        response = requests.post(
            f"{API_BASE_URL}/send-notification", 
            json=notification_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            result = response.json()
            logger.info(f"Notification created successfully: {result['notification']['notificationId']}")
            return order_id, result['notification']['notificationId']
        else:
            logger.error(f"Failed to create notification: {response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return None, None

def get_notifications_for_order(order_id):
    """Get all notifications for a specific order"""
    
    try:
        logger.info(f"Getting all notifications for order: {order_id}")
        response = requests.get(f"{API_BASE_URL}/order/{order_id}")
        
        if response.status_code == 200:
            notifications = response.json()
            logger.info(f"Found {len(notifications)} notifications for order {order_id}")
            return notifications
        elif response.status_code == 404:
            logger.warning(f"No notifications found for order {order_id}")
            return []
        else:
            logger.error(f"Error retrieving notifications: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return None

def get_latest_notification(order_id):
    """Get the latest notification for a specific order"""
    
    try:
        logger.info(f"Getting latest notification for order: {order_id}")
        response = requests.get(f"{API_BASE_URL}/order/{order_id}/latest")
        
        if response.status_code == 200:
            notification = response.json()
            logger.info(f"Found latest notification: {notification['notificationId']}")
            return notification
        elif response.status_code == 404:
            logger.warning(f"No notifications found for order {order_id}")
            return None
        else:
            logger.error(f"Error retrieving latest notification: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting latest notification: {e}")
        return None

def check_health():
    """Check if the notification service is healthy"""
    
    try:
        logger.info("Checking notification service health")
        response = requests.get(f"{API_BASE_URL}/health")
        
        if response.status_code == 200:
            logger.info("Notification service is healthy")
            return True
        else:
            logger.error(f"Notification service health check failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking health: {e}")
        return False

def run_tests():
    """Run through a series of API tests"""
    
    # Check service health
    if not check_health():
        logger.error("Service health check failed, aborting tests")
        return False
    
    # Create test notification
    order_id, notification_id = send_test_notification()
    if not order_id:
        logger.error("Failed to create test notification, aborting tests")
        return False
    
    # Give the system a moment to process
    time.sleep(1)
    
    # Get all notifications for the order
    notifications = get_notifications_for_order(order_id)
    if notifications is None:
        logger.error("Failed to retrieve notifications, aborting tests")
        return False
    
    # Get latest notification for the order
    latest = get_latest_notification(order_id)
    if latest is None:
        logger.error("Failed to retrieve latest notification, aborting tests")
        return False
    
    # Verify latest notification matches what we expect
    if latest['notificationId'] != notification_id:
        logger.error(f"Latest notification ID mismatch: expected {notification_id}, got {latest['notificationId']}")
        return False
    
    logger.info("All API tests completed successfully!")
    return True

if __name__ == "__main__":
    if run_tests():
        sys.exit(0)
    else:
        sys.exit(1)

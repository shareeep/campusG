import requests
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ServiceClient:
    """Base class for service clients"""
    
    def __init__(self, service_url_config_key):
        self.service_url = current_app.config.get(service_url_config_key)
        if not self.service_url:
            raise ValueError(f"Missing configuration for {service_url_config_key}")
    
    def _handle_response(self, response, success_code=200):
        """Handle service response and return standardized result"""
        try:
            if response.status_code == success_code:
                return {'success': True, 'data': response.json()}
            else:
                logger.error(f"Service error: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            return {'success': False, 'error': str(e)}


class UserServiceClient(ServiceClient):
    """Client for interacting with User Service"""
    
    def __init__(self):
        super().__init__('USER_SERVICE_URL')
    
    def get_user(self, user_id):
        """Get user details including payment info"""
        try:
            response = requests.get(f"{self.service_url}/api/users/{user_id}")
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling User Service: {str(e)}")
            return {'success': False, 'error': f"Failed to reach User Service: {str(e)}"}


class OrderServiceClient(ServiceClient):
    """Client for interacting with Order Service"""
    
    def __init__(self):
        super().__init__('ORDER_SERVICE_URL')
    
    def create_order(self, customer_id, order_details):
        """Create a new order"""
        try:
            payload = {
                'customer_id': customer_id,
                'order_details': order_details
            }
            response = requests.post(f"{self.service_url}/api/orders", json=payload)
            return self._handle_response(response, 201)
        except Exception as e:
            logger.error(f"Error calling Order Service: {str(e)}")
            return {'success': False, 'error': f"Failed to reach Order Service: {str(e)}"}
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        try:
            payload = {'status': status}
            response = requests.put(f"{self.service_url}/api/orders/{order_id}/status", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Order Service: {str(e)}")
            return {'success': False, 'error': f"Failed to update order status: {str(e)}"}


class PaymentServiceClient(ServiceClient):
    """Client for interacting with Payment Service"""
    
    def __init__(self):
        super().__init__('PAYMENT_SERVICE_URL')
    
    def authorize_payment(self, order_id, customer_id, amount):
        """Authorize payment via Payment Service"""
        try:
            payload = {
                'orderId': order_id,
                'customerId': customer_id,
                'amount': amount
            }
            response = requests.post(f"{self.service_url}/api/payments/authorize", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Payment Service: {str(e)}")
            return {'success': False, 'error': f"Failed to authorize payment: {str(e)}"}
    
    def release_payment(self, order_id):
        """Release payment authorization"""
        try:
            payload = {'orderId': order_id}
            response = requests.post(f"{self.service_url}/api/payments/release", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Payment Service: {str(e)}")
            return {'success': False, 'error': f"Failed to release payment: {str(e)}"}


class EscrowServiceClient(ServiceClient):
    """Client for interacting with Escrow Service"""
    
    def __init__(self):
        super().__init__('ESCROW_SERVICE_URL')
    
    def hold_funds(self, order_id, customer_id, amount, food_fee, delivery_fee):
        """Hold funds in escrow"""
        try:
            payload = {
                'orderId': order_id,
                'customerId': customer_id,
                'amount': amount,
                'foodFee': food_fee,
                'deliveryFee': delivery_fee
            }
            response = requests.post(f"{self.service_url}/api/escrow/hold", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Escrow Service: {str(e)}")
            return {'success': False, 'error': f"Failed to hold funds in escrow: {str(e)}"}


class SchedulerServiceClient(ServiceClient):
    """Client for interacting with Scheduler Service"""
    
    def __init__(self):
        super().__init__('SCHEDULER_SERVICE_URL')
    
    def schedule_timeout(self, order_id, customer_id, scheduled_time):
        """Schedule an order timeout event"""
        try:
            payload = {
                'eventType': 'ORDER_TIMEOUT',
                'entityId': order_id,
                'scheduledTime': scheduled_time,
                'payload': {
                    'orderId': order_id,
                    'customerId': customer_id
                }
            }
            response = requests.post(f"{self.service_url}/api/schedule", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Scheduler Service: {str(e)}")
            return {'success': False, 'error': f"Failed to schedule timeout: {str(e)}"}


class NotificationServiceClient(ServiceClient):
    """Client for interacting with Notification Service"""
    
    def __init__(self):
        super().__init__('NOTIFICATION_SERVICE_URL')
    
    def send_notification(self, notification_type, user_id, data):
        """Send a notification through the Notification Service"""
        try:
            payload = {
                'type': notification_type,
                'userId': user_id,
                'data': data
            }
            response = requests.post(f"{self.service_url}/api/notifications", json=payload)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling Notification Service: {str(e)}")
            return {'success': False, 'error': f"Failed to send notification: {str(e)}"}

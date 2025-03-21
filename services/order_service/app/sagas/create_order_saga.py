import uuid
import json
import requests
from datetime import datetime, timedelta
from flask import current_app
from decimal import Decimal
from app.models.models import Order, OrderStatus
from app import db
from app.services.kafka_service import kafka_client

class CreateOrderSaga:
    """
    Create Order Saga
    
    This saga orchestrates the process of creating a new order following these steps:
    1. Get user data from User Service
    2. Create order record in Order Service (generate ID)
    3. Log pending payment to Kafka notification service
    4. Authorize payment via Payment Service (Stripe integration)
    5. Log payment authorization to Kafka notification service
    6. Hold funds in Escrow Service
    7. Log escrow placement to Kafka notification service
    8. Update order status to "created" in Order Service
    9. Log status update to Kafka notification service
    10. Start order timeout timer in Scheduler Service (30 min)
    11. Update UI with new order status
    """
    
    def __init__(self, customer_id, order_details):
        """
        Initialize the Create Order Saga
        
        Args:
            customer_id (str): ID of the customer placing the order
            order_details (dict): Details of the order (food items, delivery location, etc.)
        """
        self.customer_id = customer_id
        self.order_details = order_details
        self.payment_amount = self.calculate_total(order_details)
        self.order_id = None
        self.user_data = None
        
    def execute(self):
        """
        Start the create order saga
        
        Returns:
            dict: Result of the saga execution with success status and order ID or error
        """
        try:
            # Step 1: Get user data from User Service
            user_data = self.get_user_data()
            if not user_data['success']:
                return {'success': False, 'error': user_data['error']}
            
            self.user_data = user_data.get('data', {})
                
            # Step 2: Create order record in Order Service
            order_created = self.create_order_record()
            if not order_created['success']:
                return {'success': False, 'error': order_created['error']}
                
            # Step 3: Log pending payment to Notification Service
            self.log_to_notification_service('PENDING_PAYMENT', {
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'status': 'pendingPayment'
            })
                
            # Step 4: Authorize payment via Payment Service
            payment_authorized = self.authorize_payment()
            if not payment_authorized['success']:
                # Compensating transaction: update order status to failed
                self.update_order_status(OrderStatus.CANCELLED)
                return {'success': False, 'error': payment_authorized['error']}
                
            # Step 5: Log payment authorization to Notification Service
            self.log_to_notification_service('PAYMENT_AUTHORIZED', {
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'amount': float(self.payment_amount)
            })
                
            # Step 6: Hold funds in Escrow Service
            funds_held = self.hold_funds_in_escrow()
            if not funds_held['success']:
                # Compensating transaction: release payment authorization
                self.release_payment_authorization()
                self.update_order_status(OrderStatus.CANCELLED)
                return {'success': False, 'error': funds_held['error']}
                
            # Step 7: Log escrow placement to Notification Service
            self.log_to_notification_service('ESCROW_PLACED', {
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'amount': float(self.payment_amount)
            })
                
            # Step 8: Update order status to created
            status_updated = self.update_order_status(OrderStatus.CREATED)
            if not status_updated['success']:
                # This is not critical - we can still proceed but log the error
                current_app.logger.error(f"Failed to update order status: {status_updated['error']}")
                
            # Step 9: Log status update to Notification Service
            self.log_to_notification_service('ORDER_CREATED', {
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'status': 'created'
            })
                
            # Step 10: Start order timeout timer in Scheduler Service
            timer_started = self.start_order_timeout_timer()
            if not timer_started['success']:
                # This is not critical - we can still proceed but log the error
                current_app.logger.error(f"Failed to start order timeout timer: {timer_started['error']}")
            
            # Success - return order ID
            return {
                'success': True,
                'order_id': self.order_id
            }
            
        except Exception as e:
            current_app.logger.error(f"Error executing Create Order saga: {str(e)}")
            
            # Attempt to clean up if possible
            if self.order_id:
                self.update_order_status(OrderStatus.CANCELLED)
                
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
            
    def get_user_data(self):
        """
        Step 1: Get user data from User Service
        
        Returns:
            dict: Result of user validation with success status and optional error
        """
        try:
            response = requests.get(
                f"{current_app.config['USER_SERVICE_URL']}/api/users/{self.customer_id}"
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to retrieve customer: {response.text}"
                }
                
            customer = response.json()
            
            if not customer:
                return {'success': False, 'error': 'Customer not found'}
                
            if not customer.get('paymentDetails'):
                return {'success': False, 'error': 'Customer has no payment method'}
                
            return {
                'success': True,
                'data': customer
            }
        except Exception as e:
            current_app.logger.error(f"Error validating customer: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to validate customer: {str(e)}"
            }
            
    def create_order_record(self):
        """
        Step 2: Create the order record in the database
        
        Returns:
            dict: Result of order creation with success status and optional error
        """
        try:
            food_items = self.order_details.get('foodItems', [])
            delivery_location = self.order_details.get('deliveryLocation', '')
            
            food_fee = self.calculate_food_total(food_items)
            delivery_fee = self.calculate_delivery_fee(delivery_location)
            
            # Create a new order
            order = Order(
                order_id=str(uuid.uuid4()),
                cust_id=self.customer_id,
                order_description=json.dumps(food_items),
                food_fee=food_fee,
                delivery_fee=delivery_fee,
                delivery_location=delivery_location,
                order_status=OrderStatus.PENDING
            )
            
            # Save to database
            db.session.add(order)
            db.session.commit()
            
            # Store order ID
            self.order_id = order.order_id
            
            # Publish order created event
            kafka_client.publish('order-events', {
                'type': 'ORDER_CREATED',
                'payload': {
                    'orderId': order.order_id,
                    'customerId': self.customer_id,
                    'amount': float(food_fee + delivery_fee)
                }
            })
            
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating order: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to create order: {str(e)}"
            }
    
    def log_to_notification_service(self, event_type, payload):
        """
        Log event to Notification Service via Kafka
        
        Args:
            event_type (str): Type of event
            payload (dict): Event payload
        """
        try:
            kafka_client.publish('notification-events', {
                'type': event_type,
                'payload': payload,
                'timestamp': datetime.utcnow().isoformat()
            })
            current_app.logger.info(f"Published {event_type} event to notification service")
        except Exception as e:
            current_app.logger.error(f"Error publishing {event_type} event: {str(e)}")
            # We continue despite notification errors
            
    def authorize_payment(self):
        """
        Step 4: Authorize payment with payment service
        
        Returns:
            dict: Result of payment authorization with success status and optional error
        """
        try:
            response = requests.post(
                f"{current_app.config['PAYMENT_SERVICE_URL']}/api/payments/authorize",
                json={
                    'orderId': self.order_id,
                    'customerId': self.customer_id,
                    'amount': float(self.payment_amount)
                }
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Payment service error: {response.text}"
                }
                
            result = response.json()
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('message', 'Payment authorization failed')
                }
                
            # Payment service will handle updating the payment status internally
            return {'success': True}
        except Exception as e:
            current_app.logger.error(f"Error authorizing payment: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to authorize payment: {str(e)}"
            }
            
    def hold_funds_in_escrow(self):
        """
        Step 6: Hold funds in escrow
        
        Returns:
            dict: Result of escrow operation with success status and optional error
        """
        try:
            order = Order.query.get(self.order_id)
            
            if not order:
                return {'success': False, 'error': 'Order not found'}
                
            response = requests.post(
                f"{current_app.config['ESCROW_SERVICE_URL']}/api/escrow/hold",
                json={
                    'orderId': self.order_id,
                    'customerId': self.customer_id,
                    'amount': float(self.payment_amount),
                    'foodFee': float(order.food_fee),
                    'deliveryFee': float(order.delivery_fee)
                }
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Escrow service error: {response.text}"
                }
                
            result = response.json()
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('message', 'Failed to hold funds in escrow')
                }
                
            return {'success': True}
        except Exception as e:
            current_app.logger.error(f"Error holding funds in escrow: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to hold funds in escrow: {str(e)}"
            }
            
    def release_payment_authorization(self):
        """
        Release payment authorization (compensating transaction)
        """
        try:
            response = requests.post(
                f"{current_app.config['PAYMENT_SERVICE_URL']}/api/payments/release",
                json={'orderId': self.order_id}
            )
            
            if response.status_code != 200:
                current_app.logger.error(f"Failed to release payment: {response.text}")
                return False
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error releasing payment authorization: {str(e)}")
            return False
            # We log but don't raise as this is a compensating transaction
            
    def start_order_timeout_timer(self):
        """
        Step 10: Start order timeout timer
        
        Returns:
            dict: Result of timer creation with success status and optional error
        """
        try:
            # Schedule an event 30 minutes in the future
            timeout_at = datetime.utcnow() + timedelta(minutes=30)
            
            response = requests.post(
                f"{current_app.config['SCHEDULER_SERVICE_URL']}/api/schedule",
                json={
                    'eventType': 'ORDER_TIMEOUT',
                    'entityId': self.order_id,
                    'scheduledTime': timeout_at.isoformat(),
                    'payload': {
                        'orderId': self.order_id,
                        'customerId': self.customer_id
                    }
                }
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Scheduler service error: {response.text}"
                }
                
            result = response.json()
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('message', 'Failed to schedule timeout')
                }
                
            return {'success': True}
            
        except Exception as e:
            current_app.logger.error(f"Error scheduling order timeout: {str(e)}")
            return {
                'success': False, 
                'error': f"Error scheduling timeout: {str(e)}"
            }
            
    def update_order_status(self, status):
        """
        Update order status
        
        Args:
            status (OrderStatus): New status for the order
            
        Returns:
            dict: Result of status update with success status and optional error
        """
        try:
            order = Order.query.get(self.order_id)
            if order:
                order.order_status = status
                db.session.commit()
                
                # Publish order status updated event
                kafka_client.publish('order-events', {
                    'type': 'ORDER_STATUS_UPDATED',
                    'payload': {
                        'orderId': self.order_id,
                        'status': status.name
                    }
                })
                
                return {'success': True}
            else:
                return {'success': False, 'error': 'Order not found'}
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating order status to {status.name}: {str(e)}")
            return {'success': False, 'error': f"Error updating status: {str(e)}"}
            
    def calculate_total(self, order_details):
        """
        Calculate the total amount for the order
        
        Args:
            order_details (dict): Order details with food items and delivery location
            
        Returns:
            Decimal: Total order amount
        """
        food_total = self.calculate_food_total(order_details.get('foodItems', []))
        delivery_fee = self.calculate_delivery_fee(order_details.get('deliveryLocation', ''))
        return food_total + delivery_fee
        
    def calculate_food_total(self, food_items):
        """
        Calculate the food total
        
        Args:
            food_items (list): List of food items with price and quantity
            
        Returns:
            Decimal: Total food cost
        """
        total = Decimal('0.00')
        for item in food_items:
            total += Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 0)))
        return total
        
    def calculate_delivery_fee(self, location):
        """
        Calculate delivery fee based on location
        
        Args:
            location (str): Delivery location
            
        Returns:
            Decimal: Delivery fee
        """
        # In a real implementation, this would use distance or zones
        return Decimal('3.99')

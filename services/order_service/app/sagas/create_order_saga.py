import uuid
import json
import requests
from datetime import datetime, timedelta
from flask import current_app
from decimal import Decimal
from app.models.models import Order, OrderStatus, PaymentStatus
from app import db
from app.services.kafka_service import kafka_client

class CreateOrderSaga:
    """
    Create Order Saga
    
    This saga orchestrates the process of creating a new order:
    1. Validate customer details
    2. Create order record
    3. Authorize payment
    4. Hold funds in escrow
    5. Start order timeout timer
    6. Send notifications
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
        
    async def execute(self):
        """
        Start the create order saga
        
        Returns:
            dict: Result of the saga execution with success status and order ID or error
        """
        try:
            # Step 1: Validate customer
            customer_valid = await self.validate_customer()
            if not customer_valid['success']:
                return {'success': False, 'error': customer_valid['error']}
                
            # Step 2: Create order record
            order_created = await self.create_order()
            if not order_created['success']:
                return {'success': False, 'error': order_created['error']}
                
            # Step 3: Authorize payment
            payment_authorized = await self.authorize_payment()
            if not payment_authorized['success']:
                # Compensating transaction: update order status to failed
                await self.update_order_status(OrderStatus.CANCELLED)
                return {'success': False, 'error': payment_authorized['error']}
                
            # Step 4: Hold funds in escrow
            funds_held = await self.hold_funds_in_escrow()
            if not funds_held['success']:
                # Compensating transaction: release payment authorization
                await self.release_payment_authorization()
                await self.update_order_status(OrderStatus.CANCELLED)
                return {'success': False, 'error': funds_held['error']}
                
            # Step 5: Start order timeout timer
            await self.start_order_timeout_timer()
            
            # Step 6: Send notifications
            await self.send_notifications()
            
            # Update order status to ready for pickup
            await self.update_order_status(OrderStatus.READY_FOR_PICKUP)
            
            # Success
            return {
                'success': True,
                'order_id': self.order_id
            }
        except Exception as e:
            current_app.logger.error(f"Error executing Create Order saga: {str(e)}")
            
            # Attempt to clean up if possible
            if self.order_id:
                await self.update_order_status(OrderStatus.CANCELLED)
                
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
            
    async def validate_customer(self):
        """
        Validate that the customer exists and has a valid payment method
        
        Returns:
            dict: Result of validation with success status and optional error
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
                
            return {'success': True}
        except Exception as e:
            current_app.logger.error(f"Error validating customer: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to validate customer: {str(e)}"
            }
            
    async def create_order(self):
        """
        Create the order record in the database
        
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
                id=str(uuid.uuid4()),
                cust_id=self.customer_id,
                order_description=json.dumps(food_items),
                food_fee=food_fee,
                delivery_fee=delivery_fee,
                delivery_location=delivery_location,
                payment_status=PaymentStatus.PENDING,
                order_status=OrderStatus.CREATED,
                start_time=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(order)
            db.session.commit()
            
            # Store order ID
            self.order_id = order.id
            
            # Publish order created event
            kafka_client.publish('order-events', {
                'type': 'ORDER_CREATED',
                'payload': {
                    'orderId': order.id,
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
            
    async def authorize_payment(self):
        """
        Authorize payment with payment service
        
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
                
            # Update order payment status
            order = Order.query.get(self.order_id)
            if order:
                order.payment_status = PaymentStatus.AUTHORIZED
                db.session.commit()
                
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error authorizing payment: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to authorize payment: {str(e)}"
            }
            
    async def hold_funds_in_escrow(self):
        """
        Hold funds in escrow
        
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
            
    async def release_payment_authorization(self):
        """
        Release payment authorization (compensating transaction)
        """
        try:
            requests.post(
                f"{current_app.config['PAYMENT_SERVICE_URL']}/api/payments/release",
                json={'orderId': self.order_id}
            )
        except Exception as e:
            current_app.logger.error(f"Error releasing payment authorization: {str(e)}")
            # We log but don't raise as this is a compensating transaction
            
    async def start_order_timeout_timer(self):
        """
        Start order timeout timer
        """
        try:
            # Schedule an event 30 minutes in the future
            timeout_at = datetime.utcnow() + timedelta(minutes=30)
            
            requests.post(
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
        except Exception as e:
            current_app.logger.error(f"Error scheduling order timeout: {str(e)}")
            # We continue despite errors here, as the order can still be processed
            
    async def send_notifications(self):
        """
        Send notifications about order creation
        """
        try:
            requests.post(
                f"{current_app.config['NOTIFICATION_SERVICE_URL']}/api/notifications",
                json={
                    'recipientId': self.customer_id,
                    'recipientType': 'CUSTOMER',
                    'notificationType': 'ORDER_CREATED',
                    'title': 'Order Created',
                    'message': f"Your order #{self.order_id} has been created and is being processed.",
                    'data': {
                        'orderId': self.order_id
                    },
                    'channel': 'APP'
                }
            )
        except Exception as e:
            current_app.logger.error(f"Error sending notification: {str(e)}")
            # We continue despite notification errors
            
    async def update_order_status(self, status):
        """
        Update order status
        
        Args:
            status (OrderStatus): New status for the order
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
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating order status to {status.name}: {str(e)}")
            # Status update failure should not stop the flow
            
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

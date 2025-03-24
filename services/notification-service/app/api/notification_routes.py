from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime, timezone
from app.models.models import Notification, NotificationStatus
from app import db
from app.services.kafka_service import kafka_client

api = Blueprint('api', __name__)

@api.route('/send-notification', methods=['POST'])
def send_notification():
    """
    Send a notification to a user
    
    Request body should contain:
    {
        "customerId": "customer-123",
        "runnerId": "runner-456",  (may be null/empty)
        "orderId": "order-789",
        "event": "Your order has been placed" 
    }
    
    This endpoint creates a notification record and sends it to the appropriate channels.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        customer_id = data.get('customerId')
        runner_id = data.get('runnerId', '')  # May be empty
        order_id = data.get('orderId')
        event = data.get('event')
        
        if not customer_id or not order_id or not event:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Create notification record
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            customer_id=customer_id,
            runner_id=runner_id,
            order_id=order_id,
            event=event,
            status=NotificationStatus.CREATED,
            created_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        db.session.add(notification)
        db.session.commit()
        
        # Attempt to send via appropriate channels
        send_success = _send_notification_via_channels(notification)
        
        if send_success:
            # Update notification status
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            db.session.commit()
        
        # Publish notification event to Kafka
        kafka_client.publish('notification-events', {
            'type': 'NOTIFICATION_SENT',
            'payload': {
                'notificationId': notification.notification_id,
                'customerId': customer_id,
                'runnerId': runner_id,
                'orderId': order_id,
                'event': event,
                'status': notification.status.name
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Notification created successfully',
            'notification': notification.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating notification: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to create notification: {str(e)}"}), 500

@api.route('/send-notification/order-accepted', methods=['POST'])
def send_order_accepted_notification():
    """
    Send an order accepted notification via Twilio
    
    Request body should contain:
    {
        "customerId": "customer-123",
        "runnerId": "runner-456",
        "orderId": "order-789",
        "runnerName": "John Doe"
    }
    
    This endpoint sends an SMS notification to the customer that their order has been accepted.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        customer_id = data.get('customerId')
        runner_id = data.get('runnerId')
        order_id = data.get('orderId')
        runner_name = data.get('runnerName', 'A runner')
        
        if not customer_id or not runner_id or not order_id:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Construct the message
        event = f"Your order has been accepted by {runner_name}. They will pick up your order soon."
        
        # Create notification record
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            customer_id=customer_id,
            runner_id=runner_id,
            order_id=order_id,
            event=event,
            status=NotificationStatus.CREATED,
            created_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        db.session.add(notification)
        db.session.commit()
        
        # Attempt to send via Twilio
        send_success = _send_via_twilio(notification)
        
        if send_success:
            # Update notification status
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            db.session.commit()
        
        # Publish notification event to Kafka
        kafka_client.publish('notification-events', {
            'type': 'ORDER_ACCEPTED_NOTIFICATION',
            'payload': {
                'notificationId': notification.notification_id,
                'customerId': customer_id,
                'runnerId': runner_id,
                'orderId': order_id,
                'event': event,
                'status': notification.status.name
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Order accepted notification sent successfully',
            'notification': notification.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error sending order accepted notification: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to send notification: {str(e)}"}), 500

@api.route('/revert-notification', methods=['POST'])
def revert_notification():
    """
    Revert or update a previously sent notification
    
    Request body should contain:
    {
        "notificationId": "notification-123", (optional)
        "orderId": "order-789", (required if notificationId not provided)
        "event": "Update: Your order has been cancelled"
    }
    
    This endpoint creates a new notification that supersedes a previous one.
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        notification_id = data.get('notificationId')
        order_id = data.get('orderId')
        event = data.get('event')
        
        if not event:
            return jsonify({'success': False, 'message': 'Missing event message'}), 400
            
        if not notification_id and not order_id:
            return jsonify({'success': False, 'message': 'Must provide either notificationId or orderId'}), 400
            
        # Find the original notification
        if notification_id:
            original_notification = Notification.query.get(notification_id)
            if not original_notification:
                return jsonify({'success': False, 'message': 'Notification not found'}), 404
                
        else:
            # Find the most recent notification for this order
            original_notification = Notification.query.filter_by(order_id=order_id).order_by(Notification.created_at.desc()).first()
            if not original_notification:
                return jsonify({'success': False, 'message': 'No notifications found for order'}), 404
        
        # Create a new notification with the update
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            customer_id=original_notification.customer_id,
            runner_id=original_notification.runner_id,
            order_id=original_notification.order_id,
            event=event,
            status=NotificationStatus.CREATED,
            created_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        db.session.add(notification)
        db.session.commit()
        
        # Attempt to send via appropriate channels
        send_success = _send_notification_via_channels(notification)
        
        if send_success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            db.session.commit()
        
        # Publish notification reverted event to Kafka
        kafka_client.publish('notification-events', {
            'type': 'NOTIFICATION_REVERTED',
            'payload': {
                'originalNotificationId': original_notification.notification_id,
                'newNotificationId': notification.notification_id,
                'customerId': notification.customer_id,
                'orderId': notification.order_id,
                'event': event
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Notification reverted successfully',
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reverting notification: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to revert notification: {str(e)}"}), 500

@api.route('/notifications/<notification_id>', methods=['GET'])
def get_notification(notification_id):
    """Get a specific notification by ID"""
    try:
        notification = Notification.query.get(notification_id)
        
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
            
        return jsonify({
            'success': True,
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting notification {notification_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get notification: {str(e)}"}), 500

@api.route('/notifications', methods=['GET'])
def get_notifications():
    """Get notifications with optional filtering"""
    try:
        # Query parameters
        customer_id = request.args.get('customerId')
        runner_id = request.args.get('runnerId')
        order_id = request.args.get('orderId')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = Notification.query
        
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
            
        if runner_id:
            query = query.filter_by(runner_id=runner_id)
            
        if order_id:
            query = query.filter_by(order_id=order_id)
            
        if status and hasattr(NotificationStatus, status):
            query = query.filter_by(status=getattr(NotificationStatus, status))
            
        # Get notifications with limit and order by created_at desc
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'notifications': [notification.to_dict() for notification in notifications]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get notifications: {str(e)}"}), 500

def _send_notification_via_channels(notification):
    """
    Send a notification via all appropriate channels
    
    Args:
        notification (Notification): The notification to send
        
    Returns:
        bool: True if successfully sent via at least one channel
    """
    # In a real implementation, this would determine the best channel to use
    # For now, we'll log it and pretend it was sent
    current_app.logger.info(f"Sending notification {notification.notification_id} to customer {notification.customer_id}")
    current_app.logger.info(f"Notification content: {notification.event}")
    
    return True

def _send_via_twilio(notification):
    """
    Send a notification via Twilio SMS
    
    Args:
        notification (Notification): The notification to send
        
    Returns:
        bool: True if successfully sent
    """
    try:
        customer_id = notification.customer_id
        message = notification.event
        
        # In a real implementation, we would:
        # 1. Get the customer's phone number from User Service
        # 2. Send SMS via Twilio
        
        current_app.logger.info(f"TWILIO: Would send SMS to customer {customer_id}: {message}")
        
        # TWILIO INTEGRATION - COMMENTED OUT
        """
        from twilio.rest import Client
        
        # Get Twilio credentials
        account_sid = current_app.config['TWILIO_ACCOUNT_SID']
        auth_token = current_app.config['TWILIO_AUTH_TOKEN']
        twilio_phone = current_app.config['TWILIO_PHONE_NUMBER']
        
        # Get customer phone number from User Service
        response = requests.get(
            f"{current_app.config['USER_SERVICE_URL']}/api/users/{customer_id}"
        )
        
        if response.status_code != 200:
            current_app.logger.error(f"Failed to get customer info: {response.text}")
            return False
            
        customer = response.json().get('user', {})
        phone_number = customer.get('phoneNumber')
        
        if not phone_number:
            current_app.logger.error(f"Customer {customer_id} has no phone number")
            return False
            
        # Send SMS via Twilio
        client = Client(account_sid, auth_token)
        twilio_message = client.messages.create(
            body=message,
            from_=twilio_phone,
            to=phone_number
        )
        
        current_app.logger.info(f"Sent SMS to {phone_number}, SID: {twilio_message.sid}")
        """
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error sending SMS notification: {str(e)}")
        return False

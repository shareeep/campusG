from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
from app.models.models import Payment, PaymentStatus
from app import db
from app.services.kafka_service import kafka_client
import requests
import json
from app.services.stripe_service import StripeService
from sqlalchemy.exc import SQLAlchemyError
import os

api = Blueprint('api', __name__)

# Configure user service URL
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:3000")

@api.route('/payment/<order_id>/authorize', methods=['POST'])
def authorize_order_payment(order_id):
    """
    Customer makes payment to CampusG's account (escrow)
    
    Expected input:
    {
        "customer": {
            "clerkUserId": "user_123",
            "userStripeCard": {
                "payment_method_id": "pm_123"  // Optional if already stored
            }
        },
        "custpaymentId": "payment_123"  // Optional
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "description": "No data provided"}), 400
        
        # Extract customer data
        customer_data = data.get('customer')
        if not customer_data:
            return jsonify({"success": False, "description": "Missing customer data"}), 400
        
        # Custom payment ID (optional)
        cust_payment_id = data.get('custpaymentId')
        
        # Check for existing payment
        existing_payment = Payment.query.filter_by(order_id=order_id).first()
        if existing_payment:
            return jsonify({
                "success": False,
                "description": f"Payment already exists for order {order_id} with status {existing_payment.status.name}"
            }), 400
        
        # Get order details (normally you'd fetch from order service)
        # Here we're assuming the order info is passed or fetched elsewhere
        # For this example, we'll get it from an order service or mock it
        order_info = get_order_info(order_id)
        if not order_info:
            return jsonify({"success": False, "description": "Order not found"}), 404
        
        # Get customer ID and payment method
        clerk_user_id = customer_data.get('clerkUserId')
        payment_method_id = None
        
        # Check if payment method is provided directly
        if customer_data.get('userStripeCard') and customer_data['userStripeCard'].get('payment_method_id'):
            payment_method_id = customer_data['userStripeCard']['payment_method_id']
        
        # If not, fetch from user service
        if not payment_method_id and clerk_user_id:
            payment_method_id = get_user_payment_method(clerk_user_id)
            
        if not payment_method_id:
            return jsonify({
                "success": False, 
                "description": "No payment method available for this customer"
            }), 400
        
        # Create payment intent with escrow functionality
        result = StripeService.create_payment_intent(
            customer_id=clerk_user_id,
            order_id=order_id,
            amount=order_info['amount'],
            payment_method_id=payment_method_id,
            description=f"Order {order_id} - CampusG Escrow"
        )
        
        if result["success"]:
            # Use custom payment ID if provided
            if cust_payment_id:
                payment = Payment.query.get(result["payment_id"])
                if payment:
                    # Update ID to custom ID
                    payment.payment_id = cust_payment_id
                    db.session.commit()
                    result["payment_id"] = cust_payment_id
            
            # Update payment status in database
            payment = Payment.query.get(result["payment_id"])
            if payment:
                payment.status = PaymentStatus.AUTHORIZED
                db.session.commit()
            
            # Publish payment authorized event
            kafka_client.publish('payment-events', {
                'type': 'payment.authorized',
                'payload': {
                    'orderId': order_id,
                    'paymentId': result["payment_id"],
                    'customerId': clerk_user_id,
                    'amount': order_info['amount']
                }
            })
            
            return jsonify({
                "success": True,
                "description": "Payment authorized successfully and held in escrow",
                "paymentId": result["payment_id"],
                "paymentIntentId": result["payment_intent_id"],
                "status": "AUTHORIZED"
            }), 200
        else:
            return jsonify({
                "success": False,
                "description": result["message"],
                "error": result["error"]
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in authorize_payment: {str(e)}")
        return jsonify({
            "success": False,
            "description": f"Server error: {str(e)}"
        }), 500

@api.route('/payment/<order_id>/revert', methods=['POST'])
def revert_order_payment(order_id):
    """
    CampusG account reverts payment authorization and initiates a refund
    
    Expected input (optional):
    {
        "reason": "order_canceled"
    }
    """
    try:
        data = request.json or {}
        reason = data.get('reason', 'requested_by_customer')
        
        # Find payment by order ID
        payment = Payment.query.filter_by(order_id=order_id).first()
        if not payment:
            return jsonify({"success": False, "description": "Payment not found"}), 404
            
        # Check if payment can be reverted
        if payment.status not in [PaymentStatus.AUTHORIZED, PaymentStatus.INESCROW]:
            return jsonify({
                "success": False,
                "description": f"Payment cannot be reverted in status: {payment.status.name}"
            }), 400
            
        # Revert payment via service
        result = StripeService.revert_payment(
            payment_id=payment.payment_id,
            reason=reason
        )
        
        if result["success"]:
            # Update payment status
            payment.status = PaymentStatus.FAILED
            db.session.commit()
            
            # Publish payment reverted event
            kafka_client.publish('payment-events', {
                'type': 'payment.reverted',
                'payload': {
                    'orderId': order_id,
                    'paymentId': payment.payment_id,
                    'customerId': payment.customer_id,
                    'amount': float(payment.amount),
                    'reason': reason
                }
            })
            
            return jsonify({
                "success": True,
                "description": "Payment reverted successfully",
                "status": "FAILED"
            }), 200
        else:
            return jsonify({
                "success": False,
                "description": result["message"],
                "error": result["error"] 
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in revert_payment: {str(e)}")
        return jsonify({
            "success": False,
            "description": f"Server error: {str(e)}"
        }), 500

@api.route('/payment/<order_id>/release', methods=['POST'])
def release_order_payment(order_id):
    """
    CampusG account releases funds to the runner on order completion
    
    Expected input:
    {
        "runnerId": "user_456"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "description": "No data provided"}), 400
            
        runner_id = data.get('runnerId')
        if not runner_id:
            return jsonify({"success": False, "description": "Missing runnerId"}), 400
            
        # Find payment by order ID
        payment = Payment.query.filter_by(order_id=order_id).first()
        if not payment:
            return jsonify({"success": False, "description": "Payment not found"}), 404
            
        # Check if payment can be released
        if payment.status not in [PaymentStatus.AUTHORIZED, PaymentStatus.INESCROW]:
            return jsonify({
                "success": False,
                "description": f"Payment cannot be released in status: {payment.status.name}"
            }), 400
            
        # Release funds via service
        result = StripeService.release_funds(
            payment_id=payment.payment_id,
            runner_id=runner_id
        )
        
        if result["success"]:
            # Update payment status and runner ID
            payment.status = PaymentStatus.RELEASED
            payment.runner_id = runner_id
            db.session.commit()
            
            # Publish payment released event
            kafka_client.publish('payment-events', {
                'type': 'payment.released',
                'payload': {
                    'orderId': order_id,
                    'paymentId': payment.payment_id,
                    'customerId': payment.customer_id,
                    'runnerId': runner_id,
                    'amount': float(payment.amount)
                }
            })
            
            return jsonify({
                "success": True,
                "description": "Funds released to runner successfully",
                "status": "RELEASED",
                "runnerId": runner_id
            }), 200
        else:
            return jsonify({
                "success": False,
                "description": result["message"],
                "error": result["error"] 
            }), 400 if result["error"] != "not_found" else 404
            
    except Exception as e:
        current_app.logger.error(f"Error in release_payment: {str(e)}")
        return jsonify({
            "success": False,
            "description": f"Server error: {str(e)}"
        }), 500

def get_user_payment_method(clerk_user_id):
    """
    Get the payment method ID from the user service
    """
    try:
        response = requests.get(f"{USER_SERVICE_URL}/api/user/{clerk_user_id}/payment")
        if response.status_code == 200:
            data = response.json()
            payment_info = data.get('payment_info', {})
            return payment_info.get('payment_method_id')
        return None
    except Exception as e:
        current_app.logger.error(f"Error getting user payment method: {str(e)}")
        return None

def get_order_info(order_id):
    """
    Get order information from the order service
    
    This is a placeholder - in a real implementation, you would call the Order Service
    """
    try:
        # In a real implementation, you would make an API call to the order service
        # For now, we'll mock the response
        
        # Example API call:
        # response = requests.get(f"{ORDER_SERVICE_URL}/api/orders/{order_id}")
        # if response.status_code == 200:
        #     return response.json()
        # return None
        
        # Mock response for testing
        return {
            'orderId': order_id,
            'amount': 1999,  # $19.99 in cents
            'description': f"Food delivery order {order_id}"
        }
    except Exception as e:
        current_app.logger.error(f"Error fetching order info: {str(e)}")
        return None

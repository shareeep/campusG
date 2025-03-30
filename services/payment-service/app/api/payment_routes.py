from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
from app.models.models import Payment, PaymentStatus
from app import db
from app.services.kafka_service import kafka_client
import json
from app.services.stripe_service import StripeService
from sqlalchemy.exc import SQLAlchemyError
import os

api = Blueprint('api', __name__)

@api.route('/payment/<order_id>/authorize', methods=['POST'])
def authorize_order_payment(order_id):
    """
    Customer makes payment to CampusG's account (escrow)
    
    Expected input:
    {
        "customer": {
            "clerkUserId": "user_123",
            "userStripeCard": {
                "payment_method_id": "pm_123"  // Required for payment
            }
        },
        "order": {
            "amount": 1000,  // Amount in cents
            "description": "Order description"  // Optional
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
        
        # Extract order data
        order_data = data.get('order')
        if not order_data or 'amount' not in order_data:
            return jsonify({"success": False, "description": "Missing order data or amount"}), 400
        
        # Custom payment ID (optional)
        cust_payment_id = data.get('custpaymentId')
        
        # Check for existing payment
        existing_payment = Payment.query.filter_by(order_id=order_id).first()
        if existing_payment:
            return jsonify({
                "success": False,
                "description": f"Payment already exists for order {order_id} with status {existing_payment.status.name}"
            }), 400
        
        # Get customer ID and payment method
        clerk_user_id = customer_data.get('clerkUserId')
        if not clerk_user_id:
            return jsonify({"success": False, "description": "Missing customer ID"}), 400
            
        # Get payment method ID directly from request
        payment_method_id = None
        if customer_data.get('userStripeCard') and customer_data['userStripeCard'].get('payment_method_id'):
            payment_method_id = customer_data['userStripeCard']['payment_method_id']
        
        if not payment_method_id:
            return jsonify({
                "success": False, 
                "description": "No payment method provided for this customer"
            }), 400
        
        # Create payment intent with escrow functionality
        description = order_data.get('description', f"Order {order_id} - CampusG Escrow")
        result = StripeService.create_payment_intent(
            customer_id=clerk_user_id,
            order_id=order_id,
            amount=order_data['amount'],
            payment_method_id=payment_method_id,
            description=description
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
                payment.status = PaymentStatus.AUTHORIZED.name
                db.session.commit()
            
            # Publish payment authorized event
            kafka_client.publish('payment-events', {
                'type': 'payment.authorized',
                'payload': {
                    'orderId': order_id,
                    'paymentId': result["payment_id"],
                    'customerId': clerk_user_id,
                    'amount': order_data['amount']
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
        if payment.status not in [PaymentStatus.AUTHORIZED.name, PaymentStatus.INESCROW.name]:
            return jsonify({
                "success": False,
                "description": f"Payment cannot be reverted in status: {payment.status}"
            }), 400
            
        # Revert payment via service
        result = StripeService.revert_payment(
            payment_id=payment.payment_id,
            reason=reason
        )
        
        if result["success"]:
            # Update payment status
            payment.status = PaymentStatus.FAILED.name
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
        if payment.status not in [PaymentStatus.AUTHORIZED.name, PaymentStatus.INESCROW.name]:
            return jsonify({
                "success": False,
                "description": f"Payment cannot be released in status: {payment.status}"
            }), 400
            
        # Release funds via service
        result = StripeService.release_funds(
            payment_id=payment.payment_id,
            runner_id=runner_id
        )
        
        if result["success"]:
            # Update payment status and runner ID
            payment.status = PaymentStatus.RELEASED.name
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

@api.route('/payment/<order_id>/status', methods=['GET'])
def get_payment_status(order_id):
    """
    Check the status of a payment for a specific order
    """
    try:
        # Find payment by order ID
        payment = Payment.query.filter_by(order_id=order_id).first()
        if not payment:
            return jsonify({"success": False, "description": "Payment not found"}), 404
            
        # Return payment details
        return jsonify({
            "success": True,
            "payment": payment.to_dict()
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting payment status: {str(e)}")
        return jsonify({
            "success": False,
            "description": f"Server error: {str(e)}"
        }), 500

@api.route('/payment/<payment_id>/details', methods=['GET'])
def get_payment_details(payment_id):
    """
    Get detailed information about a specific payment
    """
    try:
        # Find payment by payment ID
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"success": False, "description": "Payment not found"}), 404
            
        # Return payment details
        return jsonify({
            "success": True,
            "payment": payment.to_dict()
        }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting payment details: {str(e)}")
        return jsonify({
            "success": False,
            "description": f"Server error: {str(e)}"
        }), 500
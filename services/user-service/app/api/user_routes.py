from flask import Blueprint, request, jsonify, current_app
import uuid
import json
import traceback
import os
from sqlalchemy.exc import IntegrityError
from app.models.models import User
from app import db
from datetime import datetime, timezone

# Import for environment variable access
from dotenv import load_dotenv

# Load environment variables at module level (as backup)
load_dotenv()

api = Blueprint('api', __name__)

@api.route('/user/<clerk_user_id>', methods=['GET'])
def get_user(clerk_user_id):
    """
    Get user information by ID
    
    This endpoint retrieves all of the user's information 
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        # Include payment details by default
        include_payment_details = request.args.get('includePaymentDetails', 'true').lower() == 'true'
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_payment_details=include_payment_details)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve user: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/payment', methods=['GET'])
def get_payment_info(clerk_user_id):
    """
    Get only the user's payment information
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        if not user.user_stripe_card:
            return jsonify({'success': False, 'message': 'User has no payment method'}), 400
            
        return jsonify({
            'success': True,
            'payment_info': user.user_stripe_card
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving payment info for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve payment information: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/payment', methods=['PUT'])
def update_payment_info(clerk_user_id):
    """
    Update user payment information with Stripe PaymentMethod
    
    Request body should contain:
    {
        "paymentMethodId": "pm_1234567890"
    }
    
    Or the traditional format:
    {
        "stripeToken": "tok_visa",
        "cardLast4": "4242",
        "cardType": "Visa",
        "expiryMonth": "12",
        "expiryYear": "2025"
    }
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # Check if using the new PaymentMethod format
        if 'paymentMethodId' in data:
            payment_method_id = data.get('paymentMethodId')
            
            try:
                # Import Stripe here to avoid global import issues
                import stripe
                
                # Get Stripe API key from environment variables
                # First try to get from Flask config, then from env vars as backup
                stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')
                
                if not stripe_api_key:
                    raise ValueError("Stripe API key not found in environment variables")
                    
                stripe.api_key = stripe_api_key
                
                # Retrieve the payment method details from Stripe
                payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
                
                # Store the relevant details
                user.user_stripe_card = {
                    'payment_method_id': payment_method_id,
                    'last4': payment_method.card.last4,
                    'brand': payment_method.card.brand,
                    'exp_month': payment_method.card.exp_month,
                    'exp_year': payment_method.card.exp_year,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
            except Exception as stripe_error:
                current_app.logger.error(f"Stripe API error: {str(stripe_error)}")
                # Fallback to simple storage if Stripe API fails
                user.user_stripe_card = {
                    'payment_method_id': payment_method_id,
                    'last4': '4242',  # Fallback
                    'brand': 'Visa',  # Fallback
                    'exp_month': '12',  # Fallback
                    'exp_year': '2025',  # Fallback
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
        else:
            # Handle the traditional format
            user.user_stripe_card = {
                'last4': data.get('cardLast4', ''),
                'brand': data.get('cardType', ''),
                'exp_month': data.get('expiryMonth', ''),
                'exp_year': data.get('expiryYear', ''),
                'token': data.get('stripeToken', '')
            }
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment information updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating payment info for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update payment information: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/payment', methods=['DELETE'])
def delete_payment_info(clerk_user_id):
    """
    Delete a user's payment information
    
    This endpoint removes the stored payment method for a user.
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        if not user.user_stripe_card:
            return jsonify({'success': False, 'message': 'User has no payment method to delete'}), 400
            
        # Clear the payment information
        user.user_stripe_card = None
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment information deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting payment info for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to delete payment information: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/update-customer-rating', methods=['POST'])
def update_customer_rating(clerk_user_id):
    """
    Update the customer rating
    
    Request body should contain:
    {
        "rating": 4.5
    }
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data or 'rating' not in data:
            return jsonify({'success': False, 'message': 'Rating not provided'}), 400
            
        # Update the rating
        user.customer_rating = data['rating']
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer rating updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating customer rating for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update customer rating: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/update-runner-rating', methods=['POST'])
def update_runner_rating(clerk_user_id):
    """
    Update the runner rating
    
    Request body should contain:
    {
        "rating": 4.5
    }
    """
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data or 'rating' not in data:
            return jsonify({'success': False, 'message': 'Rating not provided'}), 400
            
        # Update the rating
        user.runner_rating = data['rating']
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Runner rating updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating runner rating for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update runner rating: {str(e)}"}), 500

@api.route('/user/list-users', methods=['GET'])
def list_user_ids():
    """
    Get a list of all user IDs
    
    This endpoint returns all user IDs in the system.
    Useful for testing and development purposes.
    """
    try:
        # Query just the clerk_user_id column for efficiency
        user_ids = [user.clerk_user_id for user in User.query.with_entities(User.clerk_user_id).all()]
        
        if not user_ids:
            return jsonify({
                'success': True,
                'userIds': [],
                'message': 'No users found in the system'
            }), 200
        
        return jsonify({
            'success': True,
            'userIds': user_ids
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving user IDs: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve user IDs: {str(e)}"}), 500

@api.route('/webhook/clerk', methods=['POST'])
def clerk_webhook():
    """
    Handle webhooks from Clerk
    
    This endpoint processes user-related events from Clerk:
    - user.created: Creates a new user
    - user.updated: Updates user information
    - user.deleted: Handles user deletion
    """
    try:
        # Get the raw request data for logging
        request_data = request.get_data()
        
        # Parse the JSON data
        data = request.json
        
        if not data or 'type' not in data or 'data' not in data:
            current_app.logger.error(f"Invalid webhook payload: {request_data}")
            return jsonify({'success': False, 'message': 'Invalid webhook payload'}), 400
            
        event_type = data['type']
        
        current_app.logger.info(f"Received Clerk webhook: {event_type}")
        
        # Process based on event type
        if event_type == 'user.created':
            handle_user_created(data['data'])
        elif event_type == 'user.updated':
            handle_user_updated(data['data'])
        elif event_type == 'user.deleted':
            handle_user_deleted(data['data'])
        else:
            current_app.logger.info(f"Unhandled event type: {event_type}")
            
        # Always return success to Clerk to acknowledge receipt
        return jsonify({'success': True, 'message': f'Processed {event_type} event'}), 200
        
    except json.JSONDecodeError:
        current_app.logger.error("Invalid JSON in webhook payload")
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400
    except Exception as e:
        current_app.logger.error(f"Error processing Clerk webhook: {str(e)}\n{traceback.format_exc()}")
        # Still return 200 to Clerk to acknowledge receipt
        return jsonify({'success': False, 'message': f"Error processing webhook: {str(e)}"}), 200

def extract_user_data(user_data):
    """Extract relevant user data from Clerk's user object"""
    try:
        # Get primary email
        primary_email = None
        if user_data.get('email_addresses') and len(user_data['email_addresses']) > 0:
            primary_email = user_data['email_addresses'][0].get('email_address')
            
        # Get primary phone
        primary_phone = None
        if user_data.get('phone_numbers') and len(user_data['phone_numbers']) > 0:
            primary_phone = user_data['phone_numbers'][0].get('phone_number')
        
        # Get timestamps if available
        created_at = None
        if user_data.get('created_at'):
            try:
                # Handle ISO format string
                if isinstance(user_data['created_at'], str):
                    created_at = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                # Handle Unix timestamp (integer)
                elif isinstance(user_data['created_at'], (int, float)):
                    created_at = datetime.fromtimestamp(user_data['created_at'], tz=timezone.utc)
                else:
                    created_at = datetime.now(timezone.utc)
            except (ValueError, TypeError):
                created_at = datetime.now(timezone.utc)
                
        updated_at = None
        if user_data.get('updated_at'):
            try:
                # Handle ISO format string
                if isinstance(user_data['updated_at'], str):
                    updated_at = datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00'))
                # Handle Unix timestamp (integer)
                elif isinstance(user_data['updated_at'], (int, float)):
                    updated_at = datetime.fromtimestamp(user_data['updated_at'], tz=timezone.utc)
                else:
                    updated_at = datetime.now(timezone.utc)
            except (ValueError, TypeError):
                updated_at = datetime.now(timezone.utc)
            
        return {
            'clerk_user_id': user_data.get('id'),
            'email': primary_email,
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'phone_number': primary_phone,
            'username': user_data.get('username'),
            'created_at': created_at,
            'updated_at': updated_at
        }
    except Exception as e:
        current_app.logger.error(f"Error extracting user data: {str(e)}")
        # Return minimal data
        return {
            'clerk_user_id': user_data.get('id'),
            'email': '',
            'first_name': '',
            'last_name': '',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }

def handle_user_created(user_data):
    """Handle user.created event from Clerk"""
    try:
        # Log the raw user data for debugging
        current_app.logger.debug(f"User data from Clerk: {json.dumps(user_data, default=str)}")
        
        # Extract user data
        data = extract_user_data(user_data)
        
        if not data['clerk_user_id']:
            current_app.logger.error("Clerk user ID missing from user.created event")
            return
            
        # Check if user already exists with this clerk_user_id
        existing_user = User.query.filter_by(clerk_user_id=data['clerk_user_id']).first()
        if existing_user:
            current_app.logger.info(f"User with Clerk ID {data['clerk_user_id']} already exists")
            return
            
        # If we have an email, check if user exists by emai
        if data['email']:
            existing_email_user = User.query.filter_by(email=data['email']).first()
            if existing_email_user:
                # Update the existing user with the Clerk ID
                existing_email_user.clerk_user_id = data['clerk_user_id']
                db.session.commit()
                current_app.logger.info(f"Updated existing user with Clerk ID {data['clerk_user_id']}")
                return
        else:
            # Generate a placeholder email if none provided
            current_app.logger.warning("Email missing from user.created event, using placeholder")
            data['email'] = f"temp_{data['clerk_user_id']}@placeholder.com"
            
        # Create new user
        user = User(
            clerk_user_id=data['clerk_user_id'],
            email=data['email'],
            first_name=data['first_name'] or "",
            last_name=data['last_name'] or "",
            phone_number=data['phone_number'],
            username=data['username'],  # Added username field
            created_at=data['created_at'] or datetime.now(timezone.utc),
            updated_at=data['updated_at'] or datetime.now(timezone.utc)
        )
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"Created new user from Clerk with ID {data['clerk_user_id']}")
        
    except IntegrityError as ie:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating user from Clerk event: {str(ie)}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling user.created: {str(e)}")

def handle_user_updated(user_data):
    """Handle user.updated event from Clerk"""
    try:
        # Log the raw user data for debugging
        current_app.logger.debug(f"User update data from Clerk: {json.dumps(user_data, default=str)}")
        
        # Extract user data
        data = extract_user_data(user_data)
        
        if not data['clerk_user_id']:
            current_app.logger.error("Clerk user ID missing from user.updated event")
            return
            
        # Find user by clerk_user_id
        user = User.query.filter_by(clerk_user_id=data['clerk_user_id']).first()
        if not user:
            # If not found by Clerk ID, try by email
            if data['email']:
                user = User.query.filter_by(email=data['email']).first()
                
            if not user:
                current_app.logger.warning(f"User not found for update: Clerk ID {data['clerk_user_id']}")
                # Create the user if they don't exist
                current_app.logger.info(f"Attempting to create missing user: {data['clerk_user_id']}")
                handle_user_created(user_data)
                return
            else:
                # Update the clerk_user_id since we found by email
                user.clerk_user_id = data['clerk_user_id']
        
        # Update fields if provided
        if data['email']:
            user.email = data['email']
        if data['first_name'] is not None:
            user.first_name = data['first_name']
        if data['last_name'] is not None:
            user.last_name = data['last_name']
        if data['phone_number'] is not None:
            user.phone_number = data['phone_number']
        
        # Update username if provided
        if data['username'] is not None:
            user.username = data['username']
            current_app.logger.info(f"Updated username to {data['username']} for user {user.clerk_user_id}")
        
        # Update the timestamp using Clerk's timestamp if available
        user.updated_at = data['updated_at'] or datetime.now(timezone.utc)
        db.session.commit()
        
        current_app.logger.info(f"Updated user from Clerk: {user.clerk_user_id}")
        
    except IntegrityError as ie:
        db.session.rollback()
        current_app.logger.error(f"Integrity error updating user from Clerk event: {str(ie)}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling user.updated: {str(e)}")

def handle_user_deleted(user_data):
    """Handle user.deleted event from Clerk"""
    try:
        clerk_user_id = user_data.get('id')
        if not clerk_user_id:
            current_app.logger.error("Clerk user ID missing from user.deleted event")
            return
            
        user = User.query.filter_by(clerk_user_id=clerk_user_id).first()
        if not user:
            current_app.logger.warning(f"User not found for deletion: Clerk ID {clerk_user_id}")
            return
            
        # You might want to mark users as inactive rather than deleting them // not decided/can ignore
        # For example, add an 'is_active' field to your User model
        
        # For now, just log the deletion request
        current_app.logger.info(f"Received deletion request for user with Clerk ID {clerk_user_id}")
        
        # If you want to actually delete:
        # db.session.delete(user)
        # db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling user.deleted: {str(e)}")

@api.route('/user/<clerk_user_id>/payment-methods', methods=['POST'])
def add_payment_method(clerk_user_id):
    """Add a payment method to a user's profile"""
    try:
        data = request.json
        payment_method_id = data.get('payment_method_id')
        
        if not payment_method_id:
            return jsonify({"success": False, "description": "Missing payment method ID"}), 400
            
        user = User.query.get(clerk_user_id)
        if not user:
            return jsonify({"success": False, "description": "User not found"}), 404
        
        # Import Stripe here to avoid global import issues
        import stripe
        
        # Get Stripe API key from environment variables
        stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')
        
        if not stripe_api_key:
            return jsonify({"success": False, "description": "Stripe API key not configured"}), 500
            
        stripe.api_key = stripe_api_key
        
        # Create or retrieve Stripe customer
        if not user.stripe_customer_id:
            # Create a new Stripe customer
            customer = stripe.Customer.create(
                metadata={'clerk_user_id': clerk_user_id},
                email=user.email,
                name=f"{user.first_name} {user.last_name}"
            )
            user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Attach payment method to customer
        try:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Could not attach payment method: {str(e)}")
            return jsonify({"success": False, "description": f"Payment method error: {str(e)}"}), 400
        
        # Retrieve payment method details
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        
        # Store card details in user profile
        card_data = {
            'payment_method_id': payment_method_id,
            'brand': payment_method.card.brand,
            'last4': payment_method.card.last4,
            'exp_month': payment_method.card.exp_month,
            'exp_year': payment_method.card.exp_year,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        user.user_stripe_card = card_data
        db.session.commit()
        
        return jsonify({
            "success": True,
            "description": "Payment method added successfully",
            "payment_info": card_data  # Changed from "card" to "payment_info" for consistency
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding payment method: {str(e)}")
        return jsonify({"success": False, "description": f"Server error: {str(e)}"}), 500

from flask import Blueprint, request, jsonify, current_app
import uuid
import json
import traceback
from sqlalchemy.exc import IntegrityError
from app.models.models import User
from app import db
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    Get user information by ID
    
    This endpoint retrieves a user's information including their profile and payment data.
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        # Include payment details by default
        include_payment_details = request.args.get('includePaymentDetails', 'true').lower() == 'true'
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_payment_details=include_payment_details)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve user: {str(e)}"}), 500

@api.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user
    
    Request body should contain:
    {
        "email": "user@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "phoneNumber": "+1234567890" (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['email', 'firstName', 'lastName']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f"Missing required field: {field}"}), 400
                
        # Create new user
        user = User(
            user_id=str(uuid.uuid4()),
            email=data['email'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            phone_number=data.get('phoneNumber')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Email already exists'}), 409
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to create user: {str(e)}"}), 500

@api.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Update user information
    
    Request body should contain fields to update:
    {
        "firstName": "New First Name",
        "lastName": "New Last Name",
        "phoneNumber": "+1234567890"
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # Update fields
        if 'firstName' in data:
            user.first_name = data['firstName']
            
        if 'lastName' in data:
            user.last_name = data['lastName']
            
        if 'phoneNumber' in data:
            user.phone_number = data['phoneNumber']
            
        # Update timestamp
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update user: {str(e)}"}), 500

@api.route('/users/<user_id>/payment', methods=['PUT'])
def update_payment_info(user_id):
    """
    Update user payment information
    
    Request body should contain:
    {
        "stripeToken": "tok_visa",
        "cardLast4": "4242",
        "cardType": "Visa",
        "expiryMonth": "12",
        "expiryYear": "2025"
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # In a real implementation, this would call Stripe to save the payment method
        # For now, we'll just store the details in the user_stripe_card field
        
        user.user_stripe_card = {
            'last4': data.get('cardLast4', ''),
            'brand': data.get('cardType', ''),
            'exp_month': data.get('expiryMonth', ''),
            'exp_year': data.get('expiryYear', ''),
            'token': data.get('stripeToken', '')
        }
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment information updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating payment info for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update payment information: {str(e)}"}), 500

@api.route('/users/<user_id>/payment-info', methods=['GET'])
def get_payment_info(user_id):
    """
    Get user's payment information
    
    This endpoint is used by other services (like Payment Service) to retrieve payment method info.
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        if not user.user_stripe_card:
            return jsonify({'success': False, 'message': 'User has no payment method'}), 400
            
        return jsonify({
            'success': True,
            'payment_info': user.user_stripe_card
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving payment info for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve payment information: {str(e)}"}), 500

@api.route('/users/<user_id>/update-customer-rating', methods=['POST'])
def update_customer_rating(user_id):
    """
    Update the customer rating
    
    Request body should contain:
    {
        "rating": 4.5
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data or 'rating' not in data:
            return jsonify({'success': False, 'message': 'Rating not provided'}), 400
            
        # Update the rating
        user.customer_rating = data['rating']
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer rating updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating customer rating for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update customer rating: {str(e)}"}), 500

@api.route('/users/<user_id>/update-runner-rating', methods=['POST'])
def update_runner_rating(user_id):
    """
    Update the runner rating
    
    Request body should contain:
    {
        "rating": 4.5
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data or 'rating' not in data:
            return jsonify({'success': False, 'message': 'Rating not provided'}), 400
            
        # Update the rating
        user.runner_rating = data['rating']
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Runner rating updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating runner rating for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update runner rating: {str(e)}"}), 500

@api.route('/list-users', methods=['GET'])
def list_user_ids():
    """
    Get a list of all user IDs
    
    This endpoint returns all user IDs in the system.
    Useful for testing and development purposes.
    """
    try:
        # Query just the user_id column for efficiency
        user_ids = [user.user_id for user in User.query.with_entities(User.user_id).all()]
        
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

@api.route('/users/clerk/<clerk_user_id>', methods=['GET'])
def get_user_by_clerk_id(clerk_user_id):
    """
    Get user information by Clerk ID
    
    This endpoint retrieves a user's information by their Clerk ID.
    """
    try:
        user = User.query.filter_by(clerk_user_id=clerk_user_id).first()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        # Include payment details by default
        include_payment_details = request.args.get('includePaymentDetails', 'true').lower() == 'true'
        
        return jsonify({
            'success': True,
            'user': user.to_dict(include_payment_details=include_payment_details)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving user with Clerk ID {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve user: {str(e)}"}), 500

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

# def clerk_webhook():
#     print("Webhook received!")
#     print(request.headers)
#     print(request.get_json())
#     return jsonify({"status": "success"}), 200

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
            
        return {
            'clerk_user_id': user_data.get('id'),
            'email': primary_email,
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'phone_number': primary_phone
        }
    except Exception as e:
        current_app.logger.error(f"Error extracting user data: {str(e)}")
        # Return minimal data
        return {
            'clerk_user_id': user_data.get('id'),
            'email': '',
            'first_name': '',
            'last_name': ''
        }

def handle_user_created(user_data):
    """Handle user.created event from Clerk"""
    try:
        # Extract user data
        data = extract_user_data(user_data)
        
        if not data['email']:
            current_app.logger.error("Email missing from user.created event")
            return
            
        # Check if user already exists with this clerk_user_id
        existing_user = User.query.filter_by(clerk_user_id=data['clerk_user_id']).first()
        if existing_user:
            current_app.logger.info(f"User with Clerk ID {data['clerk_user_id']} already exists")
            return
            
        # Also check by email to prevent duplicates
        existing_email_user = User.query.filter_by(email=data['email']).first()
        if existing_email_user:
            # Update the existing user with the Clerk ID
            existing_email_user.clerk_user_id = data['clerk_user_id']
            db.session.commit()
            current_app.logger.info(f"Updated existing user {existing_email_user.user_id} with Clerk ID {data['clerk_user_id']}")
            return
            
        # Create new user
        user = User(
            user_id=str(uuid.uuid4()),
            clerk_user_id=data['clerk_user_id'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data['phone_number']
        )
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"Created new user from Clerk: {user.user_id} with Clerk ID {data['clerk_user_id']}")
        
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating user from Clerk event")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling user.created: {str(e)}")

def handle_user_updated(user_data):
    """Handle user.updated event from Clerk"""
    try:
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
        
        # Update the timestamp
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f"Updated user from Clerk: {user.user_id} with Clerk ID {data['clerk_user_id']}")
        
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error(f"Integrity error updating user from Clerk event")
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
            
        # You might want to mark users as inactive rather than deleting them
        # For example, add an 'is_active' field to your User model
        
        # For now, just log the deletion request
        current_app.logger.info(f"Received deletion request for user {user.user_id} with Clerk ID {clerk_user_id}")
        
        # If you want to actually delete:
        # db.session.delete(user)
        # db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling user.deleted: {str(e)}")

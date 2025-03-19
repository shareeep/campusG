from flask import Blueprint, request, jsonify, current_app
import uuid
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

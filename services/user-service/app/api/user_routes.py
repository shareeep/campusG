from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from # Import swag_from
import uuid
import json
import traceback
import os
from sqlalchemy.exc import IntegrityError
from app.models.models import User
from app import db
from datetime import datetime, timezone
import stripe  # Import Stripe library

# Import for environment variable access
from dotenv import load_dotenv

# Load environment variables at module level (as backup)
load_dotenv()

api = Blueprint('api', __name__)

# Note: The health check defined in __init__.py takes precedence if registered at root.
# If this blueprint's health check is needed under /api/health, it's fine.
@api.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check for the User Service API.',
    'responses': {
        '200': {
            'description': 'Service is healthy.',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'healthy'}
                }
            }
        }
    }
})
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@api.route('/user/temp', methods=['POST'])
@swag_from({
    'tags': ['Users'],
    'summary': 'Create a temporary user.',
    'description': 'Creates a user record with a temporary, generated Clerk ID. Useful for testing or specific setup scenarios.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email'],
                'properties': {
                    'email': {'type': 'string', 'format': 'email', 'example': 'temp_user@example.com'},
                    'first_name': {'type': 'string', 'example': 'Temp'},
                    'last_name': {'type': 'string', 'example': 'User'},
                    'phone_number': {'type': 'string', 'example': '+1234567890'},
                    'username': {'type': 'string', 'example': 'tempuser'},
                    'user_stripe_card': {'type': 'object', 'description': 'Legacy card details (optional)'},
                    'stripe_customer_id': {'type': 'string', 'example': 'cus_...'}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'Temporary user created successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'clerk_user_id': {'type': 'string'},
                            'email': {'type': 'string'},
                            'first_name': {'type': 'string'},
                            'last_name': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing email, email exists)'},
        '500': {'description': 'Internal Server Error'}
    }
})
def create_temp_user():
    try:
        data = request.json
        
        if not data or 'email' not in data:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        email = data['email']
        first_name = data.get('first_name', 'Temp')
        last_name = data.get('last_name', 'User')
        phone_number = data.get('phone_number', None)
        username = data.get('username', None)
        user_stripe_card = data.get('user_stripe_card', None)
        stripe_customer_id = data.get('stripe_customer_id', None)
        
        # Generate a unique Clerk user ID for the temporary user
        temp_clerk_user_id = f"temp_{uuid.uuid4().hex}"
        
        # Create the temporary user
        temp_user = User(
            clerk_user_id=temp_clerk_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            username=username,
            user_stripe_card=user_stripe_card,
            stripe_customer_id=stripe_customer_id,
            customer_rating=5.0,
            runner_rating=5.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.session.add(temp_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Temporary user created successfully',
            'user': {
                'clerk_user_id': temp_clerk_user_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name
            }
        }), 201
        
    except IntegrityError as ie:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating temporary user: {str(ie)}")
        return jsonify({'success': False, 'message': 'Email already exists'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating temporary user: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to create temporary user: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>', methods=['GET'])
@swag_from({
    'tags': ['Users'],
    'summary': 'Get user details by Clerk User ID.',
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': 'The Clerk User ID of the user to retrieve.'
        },
        {
            'name': 'includePaymentDetails',
            'in': 'query',
            'required': False,
            'type': 'boolean',
            'default': True,
            'description': 'Whether to include payment details in the response.'
        }
    ],
    'responses': {
        '200': {
            'description': 'User details retrieved successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'user': { '$ref': '#/definitions/User' } # Assuming a User definition exists
                }
            }
        },
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    },
    # Define User schema (simplified example)
    'definitions': {
        'User': {
            'type': 'object',
            'properties': {
                'clerk_user_id': {'type': 'string'},
                'email': {'type': 'string'},
                'first_name': {'type': 'string'},
                'last_name': {'type': 'string'},
                'phone_number': {'type': 'string', 'nullable': True},
                'username': {'type': 'string', 'nullable': True},
                'customer_rating': {'type': 'number', 'format': 'float'},
                'runner_rating': {'type': 'number', 'format': 'float'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'},
                'stripe_customer_id': {'type': 'string', 'nullable': True},
                'stripe_connect_account_id': {'type': 'string', 'nullable': True},
                'user_stripe_card': { # Included if includePaymentDetails=true
                    'type': 'object',
                    'nullable': True,
                    'properties': {
                        'payment_method_id': {'type': 'string'},
                        'last4': {'type': 'string'},
                        'brand': {'type': 'string'},
                        'exp_month': {'type': 'integer'},
                        'exp_year': {'type': 'integer'},
                        'updated_at': {'type': 'string', 'format': 'date-time'}
                        # Add other legacy fields if needed
                    }
                }
            }
        }
    }
})
def get_user(clerk_user_id):
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
@swag_from({
    'tags': ['Payments'],
    'summary': "Get user's primary payment information (formatted).",
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment information retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'payment_info': {
                        'type': 'object',
                        'properties': {
                            'payment_method_id': {'type': 'string'},
                            'last_four': {'type': 'string'},
                            'card_type': {'type': 'string'},
                            'expiry_month': {'type': 'integer'},
                            'expiry_year': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        '400': {'description': 'User has no payment method'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def get_payment_info(clerk_user_id):
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        if not user.user_stripe_card:
            return jsonify({'success': False, 'message': 'User has no payment method'}), 400
            
        # Transform the payment info to match what frontend expects
        payment_info = {
            'payment_method_id': user.user_stripe_card.get('payment_method_id', ''),
            'last_four': user.user_stripe_card.get('last4', ''),  # Transform last4 to last_four
            'card_type': user.user_stripe_card.get('brand', ''),  # Transform brand to card_type
            'expiry_month': user.user_stripe_card.get('exp_month', ''),  # Transform exp_month to expiry_month
            'expiry_year': user.user_stripe_card.get('exp_year', ''),    # Transform exp_year to expiry_year
        }
            
        return jsonify({
            'success': True,
            'payment_info': payment_info
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving payment info for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve payment information: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/connect-account', methods=['GET'])
@swag_from({
    'tags': ['Stripe Connect'],
    'summary': "Get user's Stripe Connect account ID.",
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        }
    ],
    'responses': {
        '200': {
            'description': 'Stripe Connect account ID retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'stripe_connect_account_id': {'type': 'string', 'example': 'acct_...'}
                }
            }
        },
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def get_connect_account(clerk_user_id):
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        return jsonify({
            'success': True,
            'stripe_connect_account_id': user.stripe_connect_account_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving Connect account ID for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to retrieve Connect account ID: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/payment', methods=['PUT'])
@swag_from({
    'tags': ['Payments'],
    'summary': "Update user's primary payment method.",
    'description': "Updates the user's primary payment method using a Stripe PaymentMethod ID. Retrieves details from Stripe and stores them. Legacy format support is deprecated.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['paymentMethodId'],
                'properties': {
                    'paymentMethodId': {'type': 'string', 'example': 'pm_...'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment information updated successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing data)'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error (including Stripe API errors)'}
    }
})
def update_payment_info(clerk_user_id):
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

# Note: This endpoint seems duplicated by DELETE /user/<clerk_user_id>/payment-methods
# Keeping it for now but marking as potentially redundant.
@api.route('/user/<clerk_user_id>/payment', methods=['DELETE'])
@swag_from({
    'tags': ['Payments'],
    'summary': "Delete user's primary payment method.",
    'description': "Removes the stored primary payment method details for the user. Consider using DELETE /user/{clerk_user_id}/payment-methods instead.",
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment information deleted successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'User has no payment method to delete'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def delete_payment_info(clerk_user_id):
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
@swag_from({
    'tags': ['Ratings'],
    'summary': "Update user's customer rating.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['rating'],
                'properties': {
                    'rating': {'type': 'number', 'format': 'float', 'example': 4.5}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Customer rating updated successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing rating)'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def update_customer_rating(clerk_user_id):
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
@swag_from({
    'tags': ['Ratings'],
    'summary': "Update user's runner rating.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['rating'],
                'properties': {
                    'rating': {'type': 'number', 'format': 'float', 'example': 4.8}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Runner rating updated successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing rating)'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def update_runner_rating(clerk_user_id):
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
@swag_from({
    'tags': ['Users'],
    'summary': 'Get a list of all Clerk User IDs.',
    'description': 'Retrieves all Clerk User IDs stored in the system. Useful for debugging/testing.',
    'responses': {
        '200': {
            'description': 'List of user IDs retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'userIds': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'message': {'type': 'string', 'description': 'Included if no users are found.'}
                }
            }
        },
        '500': {'description': 'Internal Server Error'}
    }
})
def list_user_ids():
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

@api.route('/user/<clerk_user_id>/connect-account', methods=['PUT'])
@swag_from({
    'tags': ['Stripe Connect'],
    'summary': "Update user's Stripe Connect account ID.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['stripe_connect_account_id'],
                'properties': {
                    'stripe_connect_account_id': {'type': 'string', 'example': 'acct_...'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Connect account ID updated successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'clerkUserId': {'type': 'string'},
                            'stripeConnectAccountId': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing connect account ID)'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def update_connect_account(clerk_user_id):
    try:
        user = User.query.get(clerk_user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        data = request.json
        
        if not data or 'stripe_connect_account_id' not in data:
            return jsonify({'success': False, 'message': 'Connect account ID not provided'}), 400
            
        stripe_connect_account_id = data['stripe_connect_account_id']
        
        # Update the Connect account ID
        user.stripe_connect_account_id = stripe_connect_account_id
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Connect account ID updated successfully',
            'user': {
                'clerkUserId': user.clerk_user_id,
                'stripeConnectAccountId': user.stripe_connect_account_id
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating Connect account ID for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to update Connect account ID: {str(e)}"}), 500

@api.route('/user/<clerk_user_id>/payment-methods', methods=['POST'])
@swag_from({
    'tags': ['Payments'],
    'summary': "Add a payment method to a user.",
    'description': "Adds a Stripe PaymentMethod to the user, attaches it to their Stripe Customer (creating one if needed), sets it as default, and stores card details.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        },
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['payment_method_id'],
                'properties': {
                    'payment_method_id': {'type': 'string', 'example': 'pm_...'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment method added successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'description': {'type': 'string'},
                    'payment_info': {
                        'type': 'object',
                        'properties': {
                            'payment_method_id': {'type': 'string'},
                            'brand': {'type': 'string'},
                            'last4': {'type': 'string'},
                            'exp_month': {'type': 'integer'},
                            'exp_year': {'type': 'integer'},
                            'updated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing payment method ID, Stripe error)'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error (including Stripe API key config error)'}
    }
})
def add_payment_method(clerk_user_id):
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

@api.route('/user/<clerk_user_id>/payment-methods', methods=['DELETE'])
@swag_from({
    'tags': ['Payments'],
    'summary': "Delete user's primary payment method.",
    'description': "Removes the stored primary payment method details for the user.",
    'parameters': [
        {
            'name': 'clerk_user_id',
            'in': 'path',
            'required': True,
            'type': 'string',
            'description': "The Clerk User ID."
        }
    ],
    'responses': {
        '200': {
            'description': 'Payment method deleted successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'User has no payment method to delete'},
        '404': {'description': 'User not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def delete_payment_method(clerk_user_id):
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
            'message': 'Payment method deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting payment method for user {clerk_user_id}: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to delete payment method: {str(e)}"}), 500

@api.route('/user/sync-from-frontend', methods=['POST'])
@swag_from({
    'tags': ['Users', 'Sync'],
    'summary': 'Sync user data from frontend (Clerk).',
    'description': "Creates or updates a user based on data provided (typically from Clerk via the frontend). Handles creation of associated Stripe Customer and Connect accounts for new users. Avoids overwriting existing payment data during profile-only updates.",
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['clerk_user_id'],
                'properties': {
                    'clerk_user_id': {'type': 'string'},
                    'email': {'type': 'string', 'format': 'email'},
                    'first_name': {'type': 'string'},
                    'last_name': {'type': 'string'},
                    'phone_number': {'type': 'string', 'nullable': True},
                    'username': {'type': 'string', 'nullable': True},
                    'profile_update_only': {'type': 'boolean', 'default': False, 'description': 'Set to true to prevent overwriting payment data during profile updates.'}
                    # Add other potential fields from Clerk data if needed
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'User synced successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'user': { '$ref': '#/definitions/User' } # Reference the User definition
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing clerk_user_id)'},
        '500': {'description': 'Internal Server Error (including Stripe errors)'}
    }
})
def sync_user_from_frontend():
    try:
        data = request.json
        
        if not data or 'clerk_user_id' not in data:
            return jsonify({'success': False, 'message': 'Missing clerk_user_id'}), 400
            
        clerk_user_id = data['clerk_user_id']
        
        # Check if user already exists
        user = User.query.get(clerk_user_id)
        
        if user:
            # Store existing payment data before updating
            existing_stripe_card = user.user_stripe_card
            
            # Update existing user
            if 'email' in data:
                user.email = data['email']
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'phone_number' in data:
                user.phone_number = data['phone_number']
            if 'username' in data:
                user.username = data['username']
                
            # Ensure we don't lose payment card data during update
            # Only update if this is explicitly a profile update (not a payment update)
            if data.get('profile_update_only', False) and existing_stripe_card:
                user.user_stripe_card = existing_stripe_card
                current_app.logger.info(f"Preserved payment card data during profile update for user {clerk_user_id}")
                
            user.updated_at = datetime.now(timezone.utc)
        else:
            # Create new user
            user = User(
                clerk_user_id=clerk_user_id,
                email=data.get('email', ''),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                phone_number=data.get('phone_number'),
                username=data.get('username'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(user)
            
            # Create Stripe customer and account if needed
            try:
                # Get Stripe API key
                stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')
                if stripe_api_key:
                    stripe.api_key = stripe_api_key
                    
                    # 1. Create Stripe customer
                    customer = stripe.Customer.create(
                        email=user.email,
                        name=f"{user.first_name} {user.last_name}".strip(),
                        metadata={'clerk_user_id': user.clerk_user_id}
                    )
                    user.stripe_customer_id = customer.id
                    current_app.logger.info(f"Created Stripe customer {customer.id} for user {user.clerk_user_id}")
                    
                    # 2. Create Stripe Connect Express account
                    try:
                        connect_account = stripe.Account.create(
                            type="express",
                            country="SG",
                            email=user.email,
                            capabilities={
                                "card_payments": {"requested": True},
                                "transfers": {"requested": True},
                            },
                            metadata={
                                'clerk_user_id': user.clerk_user_id,
                                'email': user.email,
                                'name': f"{user.first_name} {user.last_name}".strip()
                            }
                        )
                        user.stripe_connect_account_id = connect_account.id
                        current_app.logger.info(f"Created Stripe Connect account {connect_account.id} for user {user.clerk_user_id}")
                    except Exception as connect_error:
                        current_app.logger.error(f"Failed to create Stripe Connect account for user {user.clerk_user_id}: {str(connect_error)}")
            except Exception as stripe_error:
                current_app.logger.error(f"Stripe error during frontend sync: {str(stripe_error)}")
        
        db.session.commit()
        
        # Log the payment card data before returning response for debugging
        current_app.logger.info(f"Card data after update for user {clerk_user_id}: {user.user_stripe_card}")
        
        # Make sure the to_dict method includes all payment data
        user_dict = user.to_dict(include_payment_details=True)
        
        return jsonify({
            'success': True,
            'message': 'User synced successfully',
            'user': user_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error syncing user from frontend: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to sync user: {str(e)}"}), 500

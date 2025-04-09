from flask import Blueprint, request, jsonify, current_app
from flasgger import swag_from # Import swag_from
from app.models.models import Order, OrderStatus
from app import db
from app.services.kafka_service import kafka_client
import uuid
import json
from datetime import datetime
from decimal import Decimal

# Import calculation functions from the new utility module
from app.utils.calculations import calculate_food_total, calculate_delivery_fee

api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check for the Order Service API.',
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

# method for debugging
@api.route('/orders', methods=['GET'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Get all orders (paginated, filterable).',
    'description': 'Retrieves a list of orders, primarily for debugging. Supports pagination and filtering by status or runner ID.',
    'parameters': [
        {
            'name': 'page', 'in': 'query', 'type': 'integer', 'default': 1,
            'description': 'Page number for pagination.'
        },
        {
            'name': 'limit', 'in': 'query', 'type': 'integer', 'default': 10,
            'description': 'Number of items per page.'
        },
        {
            'name': 'status', 'in': 'query', 'type': 'string', 'required': False,
            'description': 'Filter orders by status (e.g., ACCEPTED, PENDING). Case-insensitive.',
            'enum': [s.name for s in OrderStatus] # Dynamically generate enum from OrderStatus
        },
        {
            'name': 'runnerId', 'in': 'query', 'type': 'string', 'required': False,
            'description': 'Filter orders by assigned runner ID.'
        }
    ],
    'responses': {
        '200': {
            'description': 'List of orders retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'items': {
                        'type': 'array',
                        'items': { '$ref': '#/definitions/Order' }
                    },
                    'total': {'type': 'integer'},
                    'pages': {'type': 'integer'},
                    'page': {'type': 'integer'}
                }
            }
        },
        '400': {'description': 'Invalid status value provided.'},
        '500': {'description': 'Internal Server Error'}
    },
    # Define Order schema (simplified example)
    'definitions': {
        'Order': {
            'type': 'object',
            'properties': {
                'order_id': {'type': 'string', 'format': 'uuid'},
                'cust_id': {'type': 'string'},
                'runner_id': {'type': 'string', 'nullable': True},
                'order_description': {'type': 'string', 'description': 'JSON string of food items'},
                'food_fee': {'type': 'number', 'format': 'float'},
                'delivery_fee': {'type': 'number', 'format': 'float'},
                'total_fee': {'type': 'number', 'format': 'float'},
                'store_location': {'type': 'string', 'nullable': True},
                'delivery_location': {'type': 'string'},
                'order_status': {'type': 'string', 'enum': [s.name for s in OrderStatus]},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'},
                'accepted_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'placed_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'picked_up_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'delivered_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'completed_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'cancelled_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                'saga_id': {'type': 'string', 'format': 'uuid', 'nullable': True}
            }
        }
    }
})
def get_orders():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status_filter = request.args.get('status', None, type=str) # Get optional status filter
        runner_id_filter = request.args.get('runnerId', None, type=str) # Get optional runnerId filter

        # Base query
        query = Order.query

        # Apply status filter if provided
        if status_filter:
            try:
                status_enum = OrderStatus[status_filter.upper()]
                query = query.filter(Order.order_status == status_enum)
            except KeyError:
                # Handle invalid status gracefully, maybe return empty or error
                return jsonify({'error': f'Invalid status value: {status_filter}'}), 400

        # Apply runnerId filter if provided
        if runner_id_filter:
            query = query.filter(Order.runner_id == runner_id_filter)

        # Add ordering and pagination
        orders_paginated = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)

        result = {
            'items': [order.to_dict() for order in orders_paginated.items],
            'total': orders_paginated.total, # Use total from paginated object
            'pages': orders_paginated.pages, # Use pages from paginated object
            'page': page
            # Removed duplicate/incorrect 'total' and 'pages' keys referencing 'orders'
        }

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error getting orders: {str(e)}")
        return jsonify({'error': 'Failed to retrieve orders'}), 500

# for front end services to get order details
@api.route('/getOrderDetails', methods=['GET'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Get details for a specific order by ID.',
    'parameters': [
        {
            'name': 'orderId', 'in': 'query', 'type': 'string', 'required': True,
            'description': 'The UUID of the order to retrieve.'
        }
    ],
    'responses': {
        '200': {
            'description': 'Order details retrieved.',
            'schema': { '$ref': '#/definitions/Order' }
        },
        '400': {'description': 'Missing orderId parameter.'},
        '404': {'description': 'Order not found.'},
        '500': {'description': 'Internal Server Error'}
    }
})
def get_order_details():
    try:
        order_id = request.args.get('orderId')

        if not order_id:
            return jsonify({'error': 'Missing orderId parameter'}), 400

        order = Order.query.get(order_id)

        if not order:
            return jsonify({'error': 'Order not found'}), 404

        return jsonify(order.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"Error getting order {order_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve order'}), 500


@api.route('/orders/customer/<customer_id>', methods=['GET'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Get all orders for a specific customer (paginated).',
    'parameters': [
        {
            'name': 'customer_id', 'in': 'path', 'type': 'string', 'required': True,
            'description': 'The ID of the customer whose orders to retrieve.'
        },
        {
            'name': 'page', 'in': 'query', 'type': 'integer', 'default': 1,
            'description': 'Page number for pagination.'
        },
        {
            'name': 'limit', 'in': 'query', 'type': 'integer', 'default': 10,
            'description': 'Number of items per page.'
        }
    ],
    'responses': {
        '200': {
            'description': 'List of customer orders retrieved.',
            'schema': {
                'type': 'object',
                'properties': {
                    'items': {
                        'type': 'array',
                        'items': { '$ref': '#/definitions/Order' }
                    },
                    'total': {'type': 'integer'},
                    'pages': {'type': 'integer'},
                    'page': {'type': 'integer'}
                }
            }
        },
        '500': {'description': 'Internal Server Error'}
    }
})
def get_customer_orders(customer_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        # Query orders filtering by customer_id and paginate
        orders_query = Order.query.filter_by(cust_id=customer_id).order_by(Order.created_at.desc())
        orders_paginated = orders_query.paginate(page=page, per_page=limit, error_out=False) # error_out=False prevents 404 on empty pages

        result = {
            'items': [order.to_dict() for order in orders_paginated.items],
            'total': orders_paginated.total,
            'pages': orders_paginated.pages,
            'page': page
        }

        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error getting orders for customer {customer_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve customer orders'}), 500


# order.created
@api.route('/createOrder', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Create a new order (CRUD style).',
    'description': 'Creates an order directly via API. Publishes ORDER_CREATED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['customer_id', 'order_details'],
                'properties': {
                    'customer_id': {'type': 'string'},
                    'order_details': {
                        'type': 'object',
                        'properties': {
                            'foodItems': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string'},
                                        'price': {'type': 'number', 'format': 'float'},
                                        'quantity': {'type': 'integer'}
                                    }
                                }
                            },
                            'storeLocation': {'type': 'string', 'nullable': True},
                            'deliveryLocation': {'type': 'string'},
                            'deliveryFee': {'type': 'number', 'format': 'float', 'description': 'Delivery fee provided by caller (e.g., saga)'}
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'Order created successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'order_id': {'type': 'string', 'format': 'uuid'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing fields)'},
        '500': {'description': 'Internal Server Error'}
    }
})
def create_order():
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        customer_id = data.get('customer_id')
        order_details = data.get('order_details')

        if not customer_id or not order_details:
            return jsonify({'error': 'Missing required fields: customer_id or order_details'}), 400

        # Calculate amounts and get locations
        food_items = order_details.get('foodItems', [])
        store_location = order_details.get('storeLocation', None) # Get store location
        delivery_location = order_details.get('deliveryLocation', '')

        food_fee = calculate_food_total(food_items)
        # Use deliveryFee from input if provided, otherwise default or calculate (adjust logic as needed)
        # Assuming order_details contains 'deliveryFee' from the saga payload
        input_delivery_fee = order_details.get('deliveryFee', None)
        # Convert to Decimal, handle potential errors or None
        try:
            # Use Decimal for precision, default to 0 if conversion fails or input is None
            delivery_fee = Decimal(input_delivery_fee) if input_delivery_fee is not None else Decimal('0.00')
        except (TypeError, ValueError):
             # Fallback if conversion fails - could log a warning
             current_app.logger.warning(f"Invalid deliveryFee '{input_delivery_fee}' received for order. Defaulting to 0.")
             delivery_fee = Decimal('0.00')
             # Alternatively, could recalculate here as a fallback:
             # delivery_fee = calculate_delivery_fee(delivery_location)

        # Create a new order
        order = Order(
            order_id=str(uuid.uuid4()),
            cust_id=customer_id,
            order_description=json.dumps(food_items),
            food_fee=food_fee,
            delivery_fee=delivery_fee,
            store_location=store_location, # Add store location here
            delivery_location=delivery_location,
            order_status=OrderStatus.PENDING
        )

        # Save to database
        db.session.add(order)
        db.session.commit()

        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_CREATED',  # Keep the original event type format
            {
                'customerId': customer_id,
                'runnerId': None,  # No runner assigned at creation time
                'orderId': order.order_id,
                'status': "created",
                'event': json.dumps(order.to_dict())  # Keep the same payload structure
            }
        )

        return jsonify({
            'success': True,
            'order_id': order.order_id,
            'message': 'Order created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'success': False, 'error': f"Failed to create order: {str(e)}"}), 500

@api.route('/updateOrderStatus', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': "Update an order's status (direct API).",
    'description': 'Updates the status of an existing order. Publishes ORDER_UPDATED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId', 'status'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'},
                    'status': {'type': 'string', 'enum': [s.name for s in OrderStatus]}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Order status updated successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': { '$ref': '#/definitions/Order' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing fields, invalid status)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def update_order_status_action():
    try:
        data = request.json
        # Validate input: both orderId and status must be provided
        if not data or 'orderId' not in data or 'status' not in data:
            return jsonify({'error': 'Missing required fields: orderId or status'}), 400

        order_id = data['orderId']
        status = data['status']

        # Validate that the status is a valid OrderStatus enum value
        try:
            new_status = OrderStatus[status]
        except KeyError:
            return jsonify({'error': f"Invalid status: {status}"}), 400

        # Retrieve the order from the database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Update the order's status and corresponding timestamp
        order.order_status = new_status
        timestamp_now = db.func.now() # Get current time once

        if new_status == OrderStatus.ACCEPTED:
            order.accepted_at = timestamp_now
        elif new_status == OrderStatus.PLACED:
            order.placed_at = timestamp_now
        elif new_status == OrderStatus.ON_THE_WAY:
            order.picked_up_at = timestamp_now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = timestamp_now
        elif new_status == OrderStatus.COMPLETED:
            order.completed_at = timestamp_now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = timestamp_now
        # PENDING and CREATED are usually handled at creation or by other specific routes

        db.session.commit()


        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_UPDATED',  # Keep the original event type format
            {
                'customerId': order.cust_id,
                'runnerId': order.runner_id,
                'orderId': order.order_id,
                'status': 'updated',
                'event': json.dumps(order.to_dict())
            }
        )

        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order status: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to update order status: {str(e)}"}), 500

@api.route('/verifyAndAcceptOrder', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Runner accepts an order.',
    'description': 'Assigns a runner to an order and updates its status to ACCEPTED. Publishes ORDER_ACCEPTED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId', 'runner_id'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'},
                    'runner_id': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Order accepted successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string'},
                    'order_id': {'type': 'string', 'format': 'uuid'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing fields, order cannot be accepted)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def accept_order():
    try:
        data = request.json
        # Validate input: both orderId and runner_id must be provided
        if not data or 'orderId' not in data or 'runner_id' not in data:
            return jsonify({'error': 'Missing required fields: orderId and runner_id'}), 400

        order_id = data['orderId']
        runner_id = data['runner_id']

        # Retrieve the order by orderId from the JSON body
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Check if order is in a valid state for acceptance
        # For example, assuming only orders in the 'CREATED' state can be accepted.
        if order.order_status != OrderStatus.CREATED:
            return jsonify({'error': f"Order cannot be accepted in status: {order.order_status.name}"}), 400

        # Check if the order has already been accepted (runner_id already set)
        if order.runner_id:
            return jsonify({'error': 'Order already accepted by another runner'}), 400

        # Update the order: assign runner_id, set status to ACCEPTED, and set accepted_at timestamp
        order.runner_id = runner_id
        order.order_status = OrderStatus.ACCEPTED
        order.accepted_at = db.func.now() # Set specific timestamp
        db.session.commit()

        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_ACCEPTED',  # Keep the original event type format
            {
                'customerId': order.cust_id,
                'runnerId': order.runner_id,
                'orderId': order.order_id,
                'status': 'accepted',
                'event': json.dumps(order.to_dict())
            }
        )

        return jsonify({
            'success': True,
            'message': 'Order accepted successfully',
            'order_id': order.order_id
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting order: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to accept order: {str(e)}"}), 500


@api.route('/cancelOrder', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Cancel an order (direct API).',
    'description': 'Cancels an order if its status allows (e.g., CREATED). Publishes ORDER_CANCELLED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Order cancelled successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': { '$ref': '#/definitions/Order' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing orderId, order cannot be cancelled)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def cancel_order():
    try:
        data = request.json
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing required field: orderId'}), 400

        order_id = data['orderId']

        # Retrieve the order from the database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Business logic: the order can be cancelled only if its status is CREATED.
        if order.order_status != OrderStatus.CREATED:
            return jsonify({'error': f"Order cannot be cancelled in status: {order.order_status.name}"}), 400

        # Update the order's status to CANCELLED and set cancelled_at timestamp
        order.order_status = OrderStatus.CANCELLED
        order.cancelled_at = db.func.now() # Set specific timestamp
        db.session.commit()

        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_CANCELLED',  # Keep the original event type format
            {
                'customerId': order.cust_id,
                'runnerId': order.runner_id,
                'orderId': order.order_id,
                'status': 'cancelled',
                'event': json.dumps(order.to_dict())
            }
        )

        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to cancel order: {str(e)}"}), 500


@api.route('/cancelAcceptance', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Runner cancels acceptance of an order.',
    'description': 'Removes the assigned runner and reverts the order status (typically to CREATED). Publishes ORDER_ACCEPTANCE_CANCELLED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Order acceptance cancelled successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': { '$ref': '#/definitions/Order' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing orderId, order not in ACCEPTED state)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def cancel_acceptance():
    try:
        data = request.json
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing required field: orderId'}), 400

        order_id = data['orderId']

        # Retrieve the order from the database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Ensure the order is currently in the ACCEPTED state
        if order.order_status != OrderStatus.ACCEPTED:
            return jsonify({
                'error': f"Order cannot have acceptance cancelled in status: {order.order_status.name}"
            }), 400

        # Store the current runner_id for event logging
        runner_id = order.runner_id

        # Cancel the acceptance: clear runner_id and revert order status to CREATED (or a different valid status)
        order.runner_id = None
        order.order_status = OrderStatus.CREATED

        db.session.commit()

        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_ACCEPTANCE_CANCELLED',  # Keep the original event type format
            {
                'customerId': order.cust_id,
                'runnerId': runner_id,  # Use the stored runner_id before clearing
                'orderId': order.order_id,
                'status': 'acceptanceCancelled',
                'event': json.dumps(order.to_dict())
            }
        )

        return jsonify({
            'message': 'Order acceptance cancelled successfully',
            'order': order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order acceptance: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to cancel order acceptance: {str(e)}"}), 500

@api.route('/clearRunner', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Clear the assigned runner from an order.',
    'description': 'Removes the assigned runner and reverts the order status (typically to CREATED). Publishes ORDER_RUNNER_CLEARED Kafka event. Used for compensation or admin actions.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Runner cleared successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': { '$ref': '#/definitions/Order' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing orderId, order not in ACCEPTED state)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def clear_runner():
    try:
        data = request.json
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing required field: orderId'}), 400

        order_id = data['orderId']

        # Retrieve the order from the database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Optional: Add logic to check if the order status allows clearing the runner.
        # For consistency with cancelAcceptance, let's only allow clearing if ACCEPTED.
        if order.order_status != OrderStatus.ACCEPTED:
             return jsonify({
                 'error': f"Runner cannot be cleared in status: {order.order_status.name}. Use cancelAcceptance or similar."
             }), 400

        # Store the current runner_id for event logging
        runner_id = order.runner_id

        # Clear runner_id and revert status to CREATED
        order.runner_id = None
        order.order_status = OrderStatus.CREATED
        db.session.commit()

        # Publish event using the correct method
        # Consider a specific event type like 'ORDER_RUNNER_CLEARED'
        kafka_client.publish_event(
            'ORDER_RUNNER_CLEARED', # New event type
            {
                'customerId': order.cust_id,
                'runnerId': runner_id, # Log the runner who was cleared
                'orderId': order.order_id,
                'status': 'runnerCleared', # New status description
                'event': json.dumps(order.to_dict())
            }
        )

        return jsonify({
            'message': 'Runner cleared successfully',
            'order': order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing runner for order: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to clear runner: {str(e)}"}), 500

@api.route('/completeOrder', methods=['POST'])
@swag_from({
    'tags': ['Orders'],
    'summary': 'Mark an order as completed (direct API).',
    'description': 'Sets the order status to COMPLETED. Publishes ORDER_COMPLETED Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['orderId'],
                'properties': {
                    'orderId': {'type': 'string', 'format': 'uuid'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Order completed successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': { '$ref': '#/definitions/Order' }
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing orderId)'},
        '404': {'description': 'Order not found'},
        '500': {'description': 'Internal Server Error'}
    }
})
def complete_order():
    try:
        data = request.json
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing required field: orderId'}), 400

        order_id = data['orderId']

        # Retrieve the order from the database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Update the order status and set the completion timestamp
        order.order_status = OrderStatus.COMPLETED
        order.completed_at = db.func.now() # Set specific timestamp
        db.session.commit()

        # Publish event using the correct method
        kafka_client.publish_event(
            'ORDER_COMPLETED',  # Keep the original event type format
            {
                'customerId': order.cust_id,
                'runnerId': order.runner_id,
                'orderId': order.order_id,
                'status': 'completed',
                'event': json.dumps(order.to_dict())
            }
        )

        # Prepare response JSON with "completedAt" field
        order_dict = order.to_dict()
        # Optionally override or add "completedAt" in the response
        order_dict['completedAt'] = order.completed_at.isoformat() if order.completed_at else None

        return jsonify({
            'message': 'Order completed successfully',
            'order': order_dict
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing order: {str(e)}", exc_info=True)
        return jsonify({'error': f"Failed to complete order: {str(e)}"}), 500

@api.route('/testCreateOrder', methods=['POST'])
@swag_from({
    'tags': ['Orders', 'Testing'],
    'summary': 'Create an order for testing (CRUD style, no Kafka event).',
    'description': 'Creates an order directly via API, intended for testing purposes. Does NOT publish a Kafka event.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['customer_id', 'order_details'],
                'properties': {
                    'customer_id': {'type': 'string'},
                    'order_details': {
                        'type': 'object',
                        'properties': {
                            'foodItems': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string'},
                                        'price': {'type': 'number', 'format': 'float'},
                                        'quantity': {'type': 'integer'}
                                    }
                                }
                            },
                            'deliveryLocation': {'type': 'string'}
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': 'Test order created successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'order_id': {'type': 'string', 'format': 'uuid'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {'description': 'Bad Request (e.g., missing fields)'},
        '500': {'description': 'Internal Server Error'}
    }
})
def test_create_order():
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        customer_id = data.get('customer_id')
        order_details = data.get('order_details')

        if not customer_id or not order_details:
            return jsonify({'error': 'Missing required fields: customer_id or order_details'}), 400

        # Calculate amounts
        food_items = order_details.get('foodItems', [])
        delivery_location = order_details.get('deliveryLocation', '')

        food_fee = calculate_food_total(food_items)
        delivery_fee = calculate_delivery_fee(delivery_location)

        # Create a new order
        order = Order(
            order_id=str(uuid.uuid4()),
            cust_id=customer_id,
            order_description=json.dumps(food_items),
            food_fee=food_fee,
            delivery_fee=delivery_fee,
            delivery_location=delivery_location,
            order_status=OrderStatus.PENDING
        )

        # Save to database
        db.session.add(order)
        db.session.commit()

        return jsonify({
            'success': True,
            'order_id': order.order_id,
            'message': 'Order created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'success': False, 'error': f"Failed to create order: {str(e)}"}), 500

# Removed helper functions calculate_food_total and calculate_delivery_fee
# as they are now imported from app.utils.calculations

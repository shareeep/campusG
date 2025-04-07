from flask import Blueprint, request, jsonify, current_app
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
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# method for debugging
@api.route('/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # Get orders with pagination
        orders = Order.query.paginate(page=page, per_page=limit)
        
        result = {
            'items': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'page': page
        }
        
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error getting orders: {str(e)}")
        return jsonify({'error': 'Failed to retrieve orders'}), 500

# for front end services to get order details
@api.route('/getOrderDetails', methods=['GET'])
def get_order_details():
    """Get a specific order by ID"""
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

# order.created
@api.route('/createOrder', methods=['POST'])
def create_order():
    """Create a new order - simple CRUD without saga orchestration"""
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
def update_order_status_action():
    """
    Update an order's status (action-based API).
    
    Expected JSON input:
    {
        "orderId": "order-uuid",
        "status": "ACCEPTED"  // Must be a valid OrderStatus enum value
    }
    
    Returns:
    {
        "message": "Order status updated successfully",
        "order": {order object}
    }
    """
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

        # Update the order's status
        order.order_status = new_status
        
        # If the new status is COMPLETED, update the completed_at timestamp
        if new_status == OrderStatus.COMPLETED:
            order.completed_at = db.func.now()

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
def accept_order():
    """
    Runner accepts an order.
    
    Expected JSON input:
    {
        "orderId": "order-uuid",
        "runner_id": "runner-uuid"
    }
    
    Returns:
    {
        "success": true,
        "message": "Order accepted successfully",
        "order_id": "order-uuid"
    }
    """
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

        # Update the order: assign runner_id and set status to ACCEPTED
        order.runner_id = runner_id
        order.order_status = OrderStatus.ACCEPTED
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
def cancel_order():
    """
    Cancel an existing order.
    
    Expected JSON input:
    {
        "orderId": "order-uuid"
    }
    
    Returns:
    {
        "message": "Order cancelled successfully",
        "order": {order object}
    }
    """
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

        # Update the order's status to CANCELLED
        order.order_status = OrderStatus.CANCELLED
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
def cancel_acceptance():
    """
    Runner cancels their acceptance of an order.
    
    Expected JSON input:
    {
        "orderId": "order-uuid"
    }
    
    Returns:
    {
        "message": "Order acceptance cancelled successfully",
        "order": {order object}
    }
    """
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


@api.route('/completeOrder', methods=['POST'])
def complete_order():
    """
    Complete an order.

    Expected JSON input:
    {
      "orderId": "order-uuid"
    }

    On success, updates the order status to COMPLETED, sets the completed_at timestamp,
    and returns the order details with "completedAt" in the JSON.
    """
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
        order.completed_at = db.func.now()
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
def test_create_order():
    """Create a new order - simple CRUD without saga orchestration"""
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


# Helper functions for calculating amounts
def calculate_food_total(food_items):
    """Calculate the food total"""
    total = Decimal('0.00')
    for item in food_items:
        price = Decimal(str(item.get('price', 0)))
        quantity = Decimal(str(item.get('quantity', 0)))
        total += price * quantity
    return total

def calculate_delivery_fee(location):
    """Calculate delivery fee based on location"""
    # In a real implementation, this would use distance or zones
    return Decimal('3.99')
# Removed helper functions calculate_food_total and calculate_delivery_fee
# as they are now imported from app.utils.calculations

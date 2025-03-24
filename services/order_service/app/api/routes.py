from flask import Blueprint, request, jsonify, current_app
from app.models.models import Order, OrderStatus
from app import db
from app.services.kafka_service import kafka_client
import uuid
import json
from datetime import datetime
from decimal import Decimal

api = Blueprint('api', __name__)

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

@api.route('/orders', methods=['POST'])
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
        
        # Publish order created event
        kafka_client.publish('order-events', {
            'type': 'order.created',
            'payload': {
                'orderId': order.order_id,
                'customerId': customer_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
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
def update_order_status():
    """Update the status of an order"""
    try:
        data = request.json
        
        if not data or 'orderId' not in data or 'status' not in data:
            return jsonify({'error': 'Missing required fields: orderId or status'}), 400
            
        order_id = data['orderId']
        status = data['status']
        
        # Validate status is a valid OrderStatus
        try:
            new_status = OrderStatus[status]
        except KeyError:
            return jsonify({'error': f"Invalid status: {status}"}), 400
            
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Update the status
        order.order_status = new_status
        db.session.commit()
        
        # Publish order.updated and order.statusUpdated events
        kafka_client.publish('order-events', {
            'type': 'order.updated',
            'payload': {
                'orderId': order.id,
                'status': new_status.name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        kafka_client.publish('order-events', {
            'type': 'order.statusUpdated',
            'payload': {
                'orderId': order.id,
                'status': new_status.name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order status: {str(e)}")
        return jsonify({'error': 'Failed to update order status'}), 500

@api.route('/orders/<order_id>/accept', methods=['POST'])
def accept_order():
    """Accept an order - simple CRUD without saga orchestration"""
    try:
        data = request.json
        
        if not data or 'runner_id' not in data:
            return jsonify({'error': 'Missing required field: runner_id'}), 400
            
        runner_id = data['runner_id']
        
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order is in the correct state
        if order.order_status != OrderStatus.CREATED:
            return jsonify({
                'success': False, 
                'error': f"Order cannot be accepted in status: {order.order_status.name}"
            }), 400
            
        # Check if order already has a runner
        if order.runner_id:
            return jsonify({
                'success': False, 
                'error': 'Order already accepted by another runner'
            }), 400
            
        # Update the order
        order.runner_id = runner_id
        order.order_status = OrderStatus.ACCEPTED
        db.session.commit()
        
        # Publish event
        kafka_client.publish('order-events', {
            'type': 'order.accepted',
            'payload': {
                'orderId': order.order_id,
                'runnerId': runner_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Order accepted successfully',
            'order_id': order.order_id
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting order: {str(e)}")
        return jsonify({'success': False, 'error': f"Failed to accept order: {str(e)}"}), 500

@api.route('/cancelOrder', methods=['POST'])
def cancel_order():
    """Cancel an order"""
    try:
        data = request.json
        
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing orderId field'}), 400
            
        order_id = data['orderId']
        
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order can be cancelled
        if order.order_status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.TIMED_OUT]:
            return jsonify({'error': f"Order cannot be cancelled in status: {order.order_status.name}"}), 400
            
        # Update the order
        order.order_status = OrderStatus.CANCELLED
        db.session.commit()
        
        # Publish order.cancelled event
        kafka_client.publish('order-events', {
            'type': 'order.cancelled',
            'payload': {
                'orderId': order.id,
                'previousStatus': order.order_status.name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({'error': 'Failed to cancel order'}), 500

@api.route('/cancelAcceptance', methods=['POST'])
def cancel_acceptance():
    """Reverts acceptance of an order (runner cancels)"""
    try:
        data = request.json
        
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing orderId field'}), 400
            
        order_id = data['orderId']
        
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order is in ACCEPTED state
        if order.order_status != OrderStatus.ACCEPTED:
            return jsonify({'error': f"Order cannot have acceptance cancelled in status: {order.order_status.name}"}), 400
            
        # Store runner_id before clearing it for the event
        runner_id = order.runner_id
        
        # Update the order
        order.runner_id = None
        order.order_status = OrderStatus.READY_FOR_PICKUP
        db.session.commit()
        
        # Publish order.acceptanceCancelled event
        kafka_client.publish('order-events', {
            'type': 'order.acceptanceCancelled',
            'payload': {
                'orderId': order.id,
                'runnerId': runner_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'message': 'Order acceptance cancelled successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order acceptance: {str(e)}")
        return jsonify({'error': 'Failed to cancel order acceptance'}), 500

@api.route('/orders/<order_id>/status', methods=['PUT'])
def update_order_status():
    """Update order status - simple CRUD without saga orchestration"""
    try:
        data = request.json
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Missing required field: status'}), 400
            
        status = data['status']
        
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Validate and update the order status
        try:
            new_status = OrderStatus[status]
        except KeyError:
            return jsonify({'success': False, 'error': f"Invalid status: {status}"}), 400
            
        # Update the order
        order.order_status = new_status
        if new_status == OrderStatus.COMPLETED:
            order.end_time = db.func.now()
        db.session.commit()
        
        # Publish order status updated event
        kafka_client.publish('order-events', {
            'type': 'order.statusUpdated',
            'payload': {
                'orderId': order.order_id,
                'status': new_status.name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Order status updated successfully',
            'order_id': order.order_id
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order status: {str(e)}")
        return jsonify({'success': False, 'error': f"Failed to update order status: {str(e)}"}), 500

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

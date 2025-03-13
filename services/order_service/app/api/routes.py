from flask import Blueprint, request, jsonify, current_app
from app.models.models import Order, OrderStatus
from app import db
from app.sagas.create_order_saga import CreateOrderSaga
import uuid

api = Blueprint('api', __name__)

@api.route('/orders', methods=['GET'])
async def get_orders():
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

@api.route('/orders/<order_id>', methods=['GET'])
async def get_order(order_id):
    """Get a specific order by ID"""
    try:
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        return jsonify(order.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"Error getting order {order_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve order'}), 500

@api.route('/orders', methods=['POST'])
async def create_order():
    """Create a new order"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        customer_id = data.get('customerId')
        order_details = data.get('orderDetails')
        
        if not customer_id or not order_details:
            return jsonify({'error': 'Missing required fields: customerId or orderDetails'}), 400
            
        # Create and execute the saga
        saga = CreateOrderSaga(customer_id, order_details)
        result = await saga.execute()
        
        if not result['success']:
            return jsonify({'error': result['error']}), 400
            
        # Get the created order
        order = Order.query.get(result['order_id'])
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'Failed to create order'}), 500

@api.route('/orders/<order_id>/status', methods=['PATCH'])
async def update_order_status(order_id):
    """Update the status of an order"""
    try:
        data = request.json
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Missing status field'}), 400
            
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
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order status: {str(e)}")
        return jsonify({'error': 'Failed to update order status'}), 500

@api.route('/orders/<order_id>/accept', methods=['POST'])
async def accept_order(order_id):
    """Accept an order (runner)"""
    try:
        data = request.json
        
        if not data or 'runnerId' not in data:
            return jsonify({'error': 'Missing runnerId field'}), 400
            
        runner_id = data['runnerId']
        
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order is in the correct state
        if order.order_status != OrderStatus.READY_FOR_PICKUP:
            return jsonify({'error': f"Order cannot be accepted in status: {order.order_status.name}"}), 400
            
        # Check if order already has a runner
        if order.runner_id:
            return jsonify({'error': 'Order already accepted by another runner'}), 400
            
        # Update the order
        order.runner_id = runner_id
        order.order_status = OrderStatus.ACCEPTED
        db.session.commit()
        
        # Here we would typically call the Accept Order Saga
        # For now, we'll just return success
        
        return jsonify({
            'message': 'Order accepted successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting order: {str(e)}")
        return jsonify({'error': 'Failed to accept order'}), 500

@api.route('/orders/<order_id>/cancel', methods=['POST'])
async def cancel_order(order_id):
    """Cancel an order"""
    try:
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
        
        # Here we would typically handle refunds, notifications, etc.
        # For now, we'll just return success
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({'error': 'Failed to cancel order'}), 500

@api.route('/orders/<order_id>/complete', methods=['POST'])
async def complete_order(order_id):
    """Complete an order (delivered and payment captured)"""
    try:
        # Get the order
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order is in the right state
        if order.order_status != OrderStatus.DELIVERED:
            return jsonify({'error': f"Order cannot be completed in status: {order.order_status.name}"}), 400
            
        # Update the order
        order.order_status = OrderStatus.COMPLETED
        order.end_time = db.func.now()
        db.session.commit()
        
        # Here we would typically call the Complete Order Saga
        # For now, we'll just return success
        
        return jsonify({
            'message': 'Order completed successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing order: {str(e)}")
        return jsonify({'error': 'Failed to complete order'}), 500

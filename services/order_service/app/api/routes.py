from flask import Blueprint, request, jsonify, current_app
from app.models.models import Order, OrderStatus
from app import db
from app.sagas.create_order_saga import CreateOrderSaga
from app.services.kafka_service import kafka_client
import uuid
from datetime import datetime

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

@api.route('/getOrderDetails', methods=['GET'])
async def get_order_details():
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

@api.route('/createOrder', methods=['POST'])
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
        
        # Publish order.created event
        kafka_client.publish('order-events', {
            'type': 'order.created',
            'payload': {
                'orderId': order.id,
                'customerId': order.cust_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'Failed to create order'}), 500

@api.route('/updateOrderStatus', methods=['POST'])
async def update_order_status():
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

@api.route('/verifyAndAcceptOrder', methods=['POST'])
async def verify_and_accept_order():
    """Verifies order availability and accepts it (runner)"""
    try:
        data = request.json
        
        if not data or 'orderId' not in data or 'runnerId' not in data:
            return jsonify({'error': 'Missing required fields: orderId or runnerId'}), 400
            
        order_id = data['orderId']
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
        # For now, we'll publish the order.accepted event
        kafka_client.publish('order-events', {
            'type': 'order.accepted',
            'payload': {
                'orderId': order.id,
                'runnerId': runner_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        return jsonify({
            'message': 'Order accepted successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting order: {str(e)}")
        return jsonify({'error': 'Failed to accept order'}), 500

@api.route('/cancelOrder', methods=['POST'])
async def cancel_order():
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
async def cancel_acceptance():
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

@api.route('/completeOrder', methods=['POST'])
async def complete_order():
    """Complete an order (delivered and payment captured)"""
    try:
        data = request.json
        
        if not data or 'orderId' not in data:
            return jsonify({'error': 'Missing orderId field'}), 400
            
        order_id = data['orderId']
        
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
        
        # Publish order.completed event
        kafka_client.publish('order-events', {
            'type': 'order.completed',
            'payload': {
                'orderId': order.id,
                'customerId': order.cust_id,
                'runnerId': order.runner_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        # Here we would typically call the Complete Order Saga
        
        return jsonify({
            'message': 'Order completed successfully',
            'order': order.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing order: {str(e)}")
        return jsonify({'error': 'Failed to complete order'}), 500

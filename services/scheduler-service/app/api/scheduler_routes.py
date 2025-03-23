from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import uuid
from app.models.models import ScheduledEvent
from app import db

api = Blueprint('api', __name__)

@api.route('/schedule', methods=['POST'])
def schedule_event():
    """
    Schedule a new event to be triggered at a specific time
    
    Request body should contain:
    {
        "eventType": "ORDER_TIMEOUT", // Type of event
        "entityId": "order-123", // ID of the entity this event is for
        "scheduledTime": "2023-01-01T12:00:00Z", // ISO format timestamp
        "payload": {
            // Any event-specific data
            "orderId": "order-123",
            "customerId": "customer-456"
        }
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        event_type = data.get('eventType')
        entity_id = data.get('entityId')
        scheduled_time_str = data.get('scheduledTime')
        payload = data.get('payload', {})
        
        if not event_type or not entity_id or not scheduled_time_str:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid scheduled time format'}), 400
            
        # Create a new scheduled event
        event = ScheduledEvent(
            scheduler_id=str(uuid.uuid4()),
            event_type=event_type,
            entity_id=entity_id,
            scheduled_time=scheduled_time,
            payload=payload,
            processed=False
        )
        
        # Save to database
        db.session.add(event)
        db.session.commit()
        
        current_app.logger.info(f"Scheduled {event_type} event for {entity_id} at {scheduled_time}")
        
        return jsonify({
            'success': True,
            'message': 'Event scheduled successfully',
            'eventId': event.scheduler_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error scheduling event: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to schedule event: {str(e)}"}), 500

@api.route('/events/<event_id>/cancel', methods=['POST'])
def cancel_event(event_id):
    """Cancel a scheduled event"""
    try:
        event = ScheduledEvent.query.filter_by(scheduler_id=event_id).first()
        
        if not event:
            return jsonify({'success': False, 'message': 'Event not found'}), 404
            
        # Check if event can be cancelled
        if event.processed:
            return jsonify({'success': False, 'message': "Event has already been processed and cannot be cancelled"}), 400
            
        # Update the event to processed (cancelled)
        event.processed = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event cancelled successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling event: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to cancel event: {str(e)}"}), 500

@api.route('/events', methods=['GET'])
def get_events():
    """Get all scheduled events with optional filtering"""
    try:
        # Query parameters
        event_type = request.args.get('eventType')
        entity_id = request.args.get('entityId')
        processed = request.args.get('processed')
        
        # Build query
        query = ScheduledEvent.query
        
        if event_type:
            query = query.filter_by(event_type=event_type)
            
        if entity_id:
            query = query.filter_by(entity_id=entity_id)
            
        if processed is not None:
            processed_bool = processed.lower() == 'true'
            query = query.filter_by(processed=processed_bool)
            
        # Get events
        events = query.all()
        
        return jsonify({
            'success': True,
            'events': [event.to_dict() for event in events]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting events: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to get events: {str(e)}"}), 500

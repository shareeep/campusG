from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class ScheduledEvent(db.Model):
    """
    Model for scheduled events
    
    This model represents an event that should be triggered at a specific time.
    The scheduler service will periodically check for events that are due and
    trigger the appropriate actions.
    """
    __tablename__ = 'scheduled_events'
    
    id = db.Column(db.String(36), primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.String(36), nullable=False, index=True)
    scheduled_time = db.Column(db.DateTime, nullable=False, index=True)
    payload = db.Column(JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    triggered_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ScheduledEvent {self.id}: {self.event_type} for {self.entity_id} at {self.scheduled_time}>"
        
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'id': self.id,
            'eventType': self.event_type,
            'entityId': self.entity_id,
            'scheduledTime': self.scheduled_time.isoformat(),
            'payload': self.payload,
            'status': self.status,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
            'triggeredAt': self.triggered_at.isoformat() if self.triggered_at else None
        }

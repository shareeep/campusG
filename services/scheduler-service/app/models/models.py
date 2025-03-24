from app import db
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy.dialects.postgresql import JSONB

class EventType(enum.Enum):
    """Event type enum"""
    ORDER_TIMEOUT = "ORDER_TIMEOUT"
    PAYMENT_AUTHORIZATION_EXPIRY = "PAYMENT_AUTHORIZATION_EXPIRY"
    DELIVERY_REMINDER = "DELIVERY_REMINDER"
    ESCROW_TIMEOUT = "ESCROW_TIMEOUT"

class ScheduledEvent(db.Model):
    """
    Model for scheduled events
    
    This model represents an event that should be triggered at a specific time.
    The scheduler service will periodically check for events that are due and
    trigger the appropriate actions.
    """
    __tablename__ = 'scheduled_events'
    
    scheduler_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = db.Column(db.Enum(EventType), nullable=False, index=True)
    entity_id = db.Column(db.String(36), nullable=False, index=True)
    scheduled_time = db.Column(db.DateTime, nullable=False, index=True)
    processed = db.Column(db.Boolean, nullable=False, default=False, index=True)
    payload = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ScheduledEvent {self.scheduler_id}: {self.event_type.name} for {self.entity_id}>"
        
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'schedulerId': self.scheduler_id,
            'eventType': self.event_type.name,
            'entityId': self.entity_id,
            'scheduledTime': self.scheduled_time.isoformat(),
            'processed': self.processed,
            'payload': self.payload,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

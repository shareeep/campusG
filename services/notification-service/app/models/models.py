from app import db
from datetime import datetime
import uuid
import json

class KafkaOffsets(db.Model):
    """Track Kafka consumer offsets."""
    __tablename__ = "kafka_offsets"
    
    topic = db.Column(db.String(255), primary_key=True)
    partition = db.Column(db.Integer, primary_key=True)
    offset = db.Column(db.BigInteger, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KafkaOffset {self.topic}:{self.partition}={self.offset}>"

class Notifications(db.Model):
    """Database model for notifications."""
    __tablename__ = "notifications"
    
    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(255), nullable=True, index=True, default="")  # Allow empty customer ID for system events
    runner_id = db.Column(db.String(255), nullable=True, index=True)  # Optional runner ID
    order_id = db.Column(db.String(255), nullable=True, index=True, default="")  # Allow empty order ID for non-order events
    event = db.Column(db.Text, nullable=False)  # JSON or stringified object containing the full event
    status = db.Column(db.String(50), nullable=False, default="pending")  # Status of the notification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for creation
    
    # Additional fields for Kafka metadata
    source_topic = db.Column(db.String(255), nullable=True)  # The Kafka topic that the message came from
    event_type = db.Column(db.String(255), nullable=True)  # The type of event (from the message)
    correlation_id = db.Column(db.String(255), nullable=True)  # The correlation ID (if any)
    source_service = db.Column(db.String(255), nullable=True)  # The source service that sent the message

    def to_dict(self):
        """Convert the model to a dictionary."""
        # Try to parse event JSON if it's a string
        event_data = self.event
        try:
            if isinstance(self.event, str):
                event_data = json.loads(self.event)
        except:
            # Keep as is if it can't be parsed
            pass
            
        return {
            "notificationId": self.notification_id,
            "customerId": self.customer_id,
            "runnerId": self.runner_id,
            "orderId": self.order_id,
            "event": event_data,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "sourceTopic": self.source_topic,
            "eventType": self.event_type,
            "correlationId": self.correlation_id,
            "sourceService": self.source_service
        }

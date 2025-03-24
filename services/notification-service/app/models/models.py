from app import db
from datetime import datetime, timezone
import enum
import uuid

class NotificationStatus(enum.Enum):
    """Status of the notification"""
    CREATED = "CREATED"
    SENT = "SENT"

class Notification(db.Model):
    """Model for notifications sent to users"""
    __tablename__ = 'notifications'

    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=False, index=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    event = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(NotificationStatus), nullable=False, default=NotificationStatus.CREATED, index=True)
    sent_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification {self.notification_id} for order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'notificationId': self.notification_id,
            'customerId': self.customer_id,
            'runnerId': self.runner_id,
            'orderId': self.order_id,
            'event': self.event,
            'status': self.status.name,
            'sentAt': self.sent_at.isoformat() if self.sent_at else None,
            'createdAt': self.created_at.isoformat()
        }

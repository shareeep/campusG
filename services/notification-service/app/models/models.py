from app import db
from datetime import datetime
import enum
import uuid
from sqlalchemy.dialects.postgresql import JSONB

class RecipientType(enum.Enum):
    """Type of notification recipient"""
    CUSTOMER = "CUSTOMER"
    RUNNER = "RUNNER"

class NotificationType(enum.Enum):
    """Type of notification"""
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    DELIVERY_UPDATE = "DELIVERY_UPDATE"
    SYSTEM_ALERT = "SYSTEM_ALERT"

class Notification(db.Model):
    """Model for notifications sent to users"""
    __tablename__ = 'notifications'

    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = db.Column(db.String(36), nullable=False, index=True)
    recipient_type = db.Column(db.Enum(RecipientType), nullable=False, index=True)
    type = db.Column(db.Enum(NotificationType), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(JSONB, nullable=True)
    read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification {self.notification_id} to {self.recipient_type.name} {self.recipient_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'notificationId': self.notification_id,
            'recipientId': self.recipient_id,
            'recipientType': self.recipient_type.name,
            'type': self.type.name,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'read': self.read,
            'sentAt': self.sent_at.isoformat() if self.sent_at else None,
            'createdAt': self.created_at.isoformat()
        }

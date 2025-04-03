from app import db
from datetime import datetime
import uuid

class Notifications(db.Model):
    """Database model for notifications."""
    __tablename__ = "notifications"
    
    notification_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=True, index=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    event = db.Column(db.Text, nullable=False)  # JSON or stringified object
    status = db.Column(db.String(50), nullable=False, default="pending")  # Status of the notification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for creation

    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            "notificationId": self.notification_id,
            "customerId": self.customer_id,
            "runnerId": self.runner_id,
            "orderId": self.order_id,
            "event": self.event,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
        }     
from app import db
from datetime import datetime
import uuid

class Timer(db.Model):
    """Model for tracking time-based events related to orders"""
    __tablename__ = 'timers'

    timer_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=False, index=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    runner_accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(datetime.UTC))

    def __repr__(self):
        return f"<Timer {self.timer_id} for order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'timerId': self.timer_id,
            'customerId': self.customer_id,
            'runnerId': self.runner_id,
            'orderId': self.order_id,
            'runnerAccepted': self.runner_accepted,
            'createdAt': self.created_at.isoformat()
        }

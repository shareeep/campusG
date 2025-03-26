from app import db
from datetime import datetime, timezone, timedelta
import uuid

class Timer(db.Model):
    """Model for tracking time-based events related to orders"""
    __tablename__ = 'timers'

    timer_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=True, index=True)  # Can be null initially
    order_id = db.Column(db.String(36), nullable=False, index=True)
    runner_accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)  # When the timer expires
    
    def __init__(self, **kwargs):
        # Auto-calculate expiration time (30 minutes from creation)
        if 'expires_at' not in kwargs:
            kwargs['expires_at'] = datetime.now(timezone.utc) + timedelta(minutes=30)
        super(Timer, self).__init__(**kwargs)

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
            'createdAt': self.created_at.isoformat(),
            'expiresAt': self.expires_at.isoformat()
        }

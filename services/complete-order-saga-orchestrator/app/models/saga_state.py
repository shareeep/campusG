import uuid
from datetime import datetime
import enum
from app import db

class SagaStatus(enum.Enum):
    """Possible statuses for a saga process."""
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"

class SagaStep(enum.Enum):
    """Steps in the Complete Order Saga."""
    COMPLETE_ORDER = "COMPLETE_ORDER"

class CompleteOrderSagaState(db.Model):
    """Model for tracking the state of a complete order saga."""
    __tablename__ = 'complete_order_saga_states'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.Enum(SagaStatus), nullable=False, default=SagaStatus.STARTED)
    current_step = db.Column(db.Enum(SagaStep), nullable=True, default=SagaStep.COMPLETE_ORDER)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def update_status(self, status, step=None, error=None):
        """Update the status of this complete order saga state."""
        self.status = status
        if step:
            self.current_step = step
        if error:
            self.error = error
        self.updated_at = datetime.utcnow()
        if status == SagaStatus.COMPLETED:
            self.completed_at = datetime.utcnow()

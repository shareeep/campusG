import uuid
from datetime import datetime
import enum
from app import db

class SagaStatus(enum.Enum):
    """Status of a saga process"""
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"

class SagaStep(enum.Enum):
    """Steps in the Create Order Saga"""
    GET_USER_DATA = "GET_USER_DATA"
    CREATE_ORDER = "CREATE_ORDER"
    AUTHORIZE_PAYMENT = "AUTHORIZE_PAYMENT"
    HOLD_FUNDS = "HOLD_FUNDS"
    UPDATE_ORDER_STATUS = "UPDATE_ORDER_STATUS"
    START_TIMER = "START_TIMER"
    NOTIFY_USER = "NOTIFY_USER"

class CreateOrderSagaState(db.Model):
    """Model for tracking the state of a create order saga"""
    __tablename__ = 'create_order_saga_states'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), nullable=False)
    order_id = db.Column(db.String(36), nullable=True)  # Will be null until order is created
    status = db.Column(db.Enum(SagaStatus), nullable=False, default=SagaStatus.STARTED)
    current_step = db.Column(db.Enum(SagaStep), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    order_details = db.Column(db.JSON, nullable=False)  # Original order request
    payment_amount = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def update_status(self, status, step=None, error=None):
        """Update the status of this saga state"""
        self.status = status
        if step:
            self.current_step = step
        if error:
            self.error = error
        self.updated_at = datetime.utcnow()
        
        if status == SagaStatus.COMPLETED:
            self.completed_at = datetime.utcnow()

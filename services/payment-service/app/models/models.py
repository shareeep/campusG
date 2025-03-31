from app import db
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Numeric

class PaymentStatus(enum.Enum):
    """Status of the payment"""
    INITIATING = "INITIATING"
    AUTHORIZED = "AUTHORIZED"
    RELEASED = "RELEASED"    # Payment released to runner
    REVERTED = "REVERTED"    # Payment reverted/refunded to customer
    FAILED = "FAILED"

class Payment(db.Model):
    """Model for payment transactions"""
    __tablename__ = 'payments'

    # Primary key - can be referenced as both id and payment_id
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Store Stripe payment intent ID
    payment_intent_id = db.Column(db.String(255), nullable=True)
    
    # Order and user info
    # Order ID should be unique for each payment
    order_id = db.Column(db.String(36), nullable=False, index=True, unique=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=True)
    
    # Payment details
    amount = db.Column(Numeric(10, 2), nullable=False)
    # Use SQLAlchemy's Enum type for better type safety and potential DB-level constraints
    status = db.Column(db.Enum(PaymentStatus, name='payment_status_enum', create_type=False), nullable=False, default=PaymentStatus.INITIATING, index=True)
    description = db.Column(db.String(255), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Payment {self.id} for order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'paymentId': self.payment_id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'runnerId': self.runner_id,
            'amount': float(self.amount),
            'status': self.status.value, # Return the enum's value (string)
            'description': self.description,
            'paymentIntentId': self.payment_intent_id,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

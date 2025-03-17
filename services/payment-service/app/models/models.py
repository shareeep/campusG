from app import db
from datetime import datetime
import enum

class PaymentStatus(enum.Enum):
    """Payment status enum"""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Payment(db.Model):
    """
    Model for payment records
    
    This model represents a payment record with Stripe integration.
    Each payment is associated with an order and has a status indicating
    where it is in the payment lifecycle.
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    captured_at = db.Column(db.DateTime, nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Payment {self.id}: {self.amount} for order {self.order_id}>"
        
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'id': self.id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'amount': self.amount,
            'stripePaymentIntentId': self.stripe_payment_intent_id,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
            'capturedAt': self.captured_at.isoformat() if self.captured_at else None,
            'refundedAt': self.refunded_at.isoformat() if self.refunded_at else None
        }

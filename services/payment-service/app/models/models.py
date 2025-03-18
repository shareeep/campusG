from app import db
from datetime import datetime
import enum
import uuid

class PaymentStatus(enum.Enum):
    """Payment status enum"""
    INITIATING = "INITIATING"
    AUTHORIZED = "AUTHORIZED"
    INESCROW = "INESCROW"
    FAILED = "FAILED"

class Payment(db.Model):
    """
    Model for payment records
    
    This model represents a payment record with Stripe integration.
    Each payment is associated with an order and has a status indicating
    where it is in the payment lifecycle.
    """
    __tablename__ = 'payments'
    
    payment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), nullable=False, index=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.INITIATING, index=True)
    payment_method = db.Column(db.String(50), nullable=False)
    stripe_payment_id = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Payment {self.payment_id}: {self.amount} for order {self.order_id}>"
        
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'paymentId': self.payment_id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'amount': float(self.amount),
            'status': self.status.name,
            'paymentMethod': self.payment_method,
            'stripePaymentId': self.stripe_payment_id,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

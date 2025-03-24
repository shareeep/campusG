from app import db
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Numeric

class PaymentStatus(enum.Enum):
    """Status of the payment"""
    INITIATING = "INITIATING"
    AUTHORIZED = "AUTHORIZED"
    INESCROW = "INESCROW"
    FAILED = "FAILED"

class Payment(db.Model):
    """Model for payment transactions"""
    __tablename__ = 'payments'

    payment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), nullable=False, index=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    amount = db.Column(Numeric(5, 2), nullable=False)
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.INITIATING, index=True)
    customer_stripe_card = db.Column(db.String(255), nullable=True)
    stripe_payment_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Payment {self.payment_id} for order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'paymentId': self.payment_id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'amount': float(self.amount),
            'status': self.status.name,
            'customerStripeCard': self.customer_stripe_card,
            'stripePaymentId': self.stripe_payment_id,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

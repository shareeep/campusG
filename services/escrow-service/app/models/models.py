from app import db
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Numeric

class EscrowStatus(enum.Enum):
    """Status of an escrow transaction"""
    PENDING = "PENDING"
    HELD = "HELD"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"

class Escrow(db.Model):
    """Model for escrow transactions"""
    __tablename__ = 'escrows'

    escrow_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), nullable=False, index=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=True, index=True)  # May be null initially
    amount = db.Column(Numeric(10, 2), nullable=False)
    food_fee = db.Column(Numeric(10, 2), nullable=False)
    delivery_fee = db.Column(Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum(EscrowStatus), nullable=False, default=EscrowStatus.PENDING, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<Escrow {self.escrow_id} for order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'escrowId': self.escrow_id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'runnerId': self.runner_id,
            'amount': float(self.amount),
            'foodFee': float(self.food_fee),
            'deliveryFee': float(self.delivery_fee),
            'status': self.status.name,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

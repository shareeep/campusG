from app import db
from datetime import datetime
import enum

class TransactionType(enum.Enum):
    """Transaction type enum"""
    HOLD = "HOLD"
    RELEASE = "RELEASE"

class TransactionStatus(enum.Enum):
    """Transaction status enum"""
    PENDING = "PENDING"
    HELD = "HELD"
    RELEASED = "RELEASED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class EscrowTransaction(db.Model):
    """
    Model for escrow transactions
    
    This model represents an escrow transaction. There are two types of transactions:
    1. HOLD: When funds are placed in escrow
    2. RELEASE: When funds are released from escrow to a recipient
    
    The HOLD transaction serves as the parent record for any associated RELEASE transactions.
    """
    __tablename__ = 'escrow_transactions'
    
    id = db.Column(db.String(36), primary_key=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    customer_id = db.Column(db.String(36), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    food_fee = db.Column(db.Float, nullable=False, default=0)
    delivery_fee = db.Column(db.Float, nullable=False, default=0)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False, index=True)
    status = db.Column(db.Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING, index=True)
    recipient_type = db.Column(db.String(50), nullable=True)  # RESTAURANT or RUNNER for RELEASE transactions
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EscrowTransaction {self.id}: {self.transaction_type.value} for order {self.order_id}>"
        
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'id': self.id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'amount': self.amount,
            'foodFee': self.food_fee,
            'deliveryFee': self.delivery_fee,
            'transactionType': self.transaction_type.value,
            'status': self.status.value,
            'recipientType': self.recipient_type,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

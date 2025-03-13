from app import db
from datetime import datetime
import enum
from sqlalchemy.dialects.postgresql import JSON

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"

class OrderStatus(enum.Enum):
    CREATED = "CREATED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    ACCEPTED = "ACCEPTED"
    COLLECTED = "COLLECTED"
    ON_THE_WAY = "ON_THE_WAY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.String(36), primary_key=True)
    cust_id = db.Column(db.String(36), nullable=False)
    runner_id = db.Column(db.String(36), nullable=True)
    order_description = db.Column(db.Text, nullable=False)
    food_fee = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_location = db.Column(db.String(255), nullable=False)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    order_status = db.Column(db.Enum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'custId': self.cust_id,
            'runnerId': self.runner_id,
            'orderDescription': self.order_description,
            'foodFee': float(self.food_fee),
            'deliveryFee': float(self.delivery_fee),
            'deliveryLocation': self.delivery_location,
            'paymentStatus': self.payment_status.name,
            'orderStatus': self.order_status.name,
            'startTime': self.start_time.isoformat() if self.start_time else None,
            'endTime': self.end_time.isoformat() if self.end_time else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

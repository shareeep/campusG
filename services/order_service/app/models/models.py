from app import db
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Enum as SQLAlchemyEnum

class OrderStatus(enum.Enum):
    """Order status enum"""
    PENDING = "PENDING"
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    PLACED = "PLACED"
    ON_THE_WAY = "ON_THE_WAY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Order(db.Model):
    """Model for orders"""
    __tablename__ = 'orders'

    order_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cust_id = db.Column(db.String(36), nullable=False, index=True)
    runner_id = db.Column(db.String(36), nullable=True, index=True)
    order_description = db.Column(db.Text, nullable=False)
    food_fee = db.Column(db.Numeric(5, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(5, 2), nullable=False)
    delivery_location = db.Column(db.String(255), nullable=False)
    order_status = db.Column(SQLAlchemyEnum(OrderStatus, native_enum=False), nullable=False, default=OrderStatus.PENDING, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Order {self.order_id}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'orderId': self.order_id,
            'custId': self.cust_id,
            'runnerId': self.runner_id,
            'orderDescription': self.order_description,
            'foodFee': float(self.food_fee),
            'deliveryFee': float(self.delivery_fee),
            'deliveryLocation': self.delivery_location,
            'orderStatus': self.order_status.name,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat(),
            'completedAt': self.completed_at.isoformat() if self.completed_at else None
        }

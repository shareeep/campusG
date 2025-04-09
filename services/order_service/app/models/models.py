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
    store_location = db.Column(db.String(255), nullable=True) # Added store location
    delivery_location = db.Column(db.String(255), nullable=False)
    order_status = db.Column(SQLAlchemyEnum(OrderStatus, native_enum=False), nullable=False, default=OrderStatus.PENDING, index=True)
    saga_id = db.Column(db.String(36), nullable=True, index=True) # Added saga_id column
    # Use db.func.now() to ensure the database sets the timestamp at the time of creation/update
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())
    # Timestamps for specific status changes
    accepted_at = db.Column(db.DateTime, nullable=True)
    placed_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True) # Corresponds to ON_THE_WAY
    delivered_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True) # Added for cancelled status

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
            'storeLocation': self.store_location, # Added store location
            'deliveryLocation': self.delivery_location,
            'orderStatus': self.order_status.name,
            'sagaId': self.saga_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            # Add new timestamps to dict, handling None values
            'acceptedAt': self.accepted_at.isoformat() if self.accepted_at else None,
            'placedAt': self.placed_at.isoformat() if self.placed_at else None,
            'pickedUpAt': self.picked_up_at.isoformat() if self.picked_up_at else None,
            'deliveredAt': self.delivered_at.isoformat() if self.delivered_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'cancelledAt': self.cancelled_at.isoformat() if self.cancelled_at else None
        }

from app import db
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Numeric

class User(db.Model):
    """Model for users (both customers and runners)"""
    __tablename__ = 'users'

    clerk_user_id = db.Column(db.String(255), primary_key=True, index=True)
    username = db.Column(db.String(100), nullable=True, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    user_stripe_card = db.Column(JSONB, nullable=True)
    customer_rating = db.Column(Numeric, nullable=False, default=5.0, index=True)
    runner_rating = db.Column(Numeric, nullable=False, default=5.0, index=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self, include_payment_details=False):
        """Convert the model to a dictionary"""
        data = {
            'clerkUserId': self.clerk_user_id,
            'username': self.username,
            'email': self.email,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'phoneNumber': self.phone_number,
            'customerRating': float(self.customer_rating),
            'runnerRating': float(self.runner_rating),
            'stripeCustomerId': self.stripe_customer_id,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }
        
        if include_payment_details and self.user_stripe_card:
            data['userStripeCard'] = self.user_stripe_card
            
        return data

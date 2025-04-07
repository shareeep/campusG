import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@complete-order-saga-db:5432/complete_order_saga_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

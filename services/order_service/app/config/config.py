import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost:5432/order_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Kafka configuration
    KAFKA_BROKERS = os.environ.get('KAFKA_BROKERS') or 'localhost:9092'
    KAFKA_CLIENT_ID = 'order-service'
    KAFKA_GROUP_ID = 'order-service-group'
    
    # Service URLs
    USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL') or 'http://localhost:3001'
    PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL') or 'http://localhost:3003'
    ESCROW_SERVICE_URL = os.environ.get('ESCROW_SERVICE_URL') or 'http://localhost:3004'
    SCHEDULER_SERVICE_URL = os.environ.get('SCHEDULER_SERVICE_URL') or 'http://localhost:3005'
    NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL') or 'http://localhost:3006'

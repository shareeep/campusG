from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import logging

# Initialize SQLAlchemy instance first (without binding to app yet)
db = SQLAlchemy()
migrate = Migrate()

def create_app(config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/payment_db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        STRIPE_API_KEY=os.environ.get('STRIPE_API_KEY', 'sk_test_your_key'),
        STRIPE_WEBHOOK_SECRET=os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_your_secret'),
    )
    
    # Load custom config if provided
    if config:
        app.config.from_mapping(config)
    
    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.api.payment_routes import api as payment_api
    app.register_blueprint(payment_api, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Import and register blueprints
    from app.api.webhook_routes import webhook
    app.register_blueprint(webhook, url_prefix='/api')
    
    # Setup database
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import models
        
        # Configure real Stripe service instead of placeholder
        from app.services.stripe_service import StripeService
        
        # Set Stripe API key directly through the official SDK
        import stripe
        stripe.api_key = app.config.get('STRIPE_API_KEY', 'sk_test_your_key')
        
        # Safe database initialization - check if tables exist first
        from app.models.models import Payment
        inspector = db.inspect(db.engine)
        if not inspector.has_table('payments'):
            try:
                db.create_all()
                app.logger.info("Database tables created successfully")
            except Exception as e:
                app.logger.warning(f"Error during db.create_all(): {e}")
        else:
            app.logger.info("Database tables already exist - skipping creation")
    
    return app

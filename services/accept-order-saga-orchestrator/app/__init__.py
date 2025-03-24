from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Initialize extensions
db = SQLAlchemy()

def create_app(config_class=None):
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@accept-order-saga-db:5432/accept_order_saga_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Set other configurations from environment variables
    app.config['USER_SERVICE_URL'] = 'http://user-service:3000'
    app.config['ORDER_SERVICE_URL'] = 'http://order-service:3000'
    app.config['NOTIFICATION_SERVICE_URL'] = 'http://notification-service:3000'
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Log configuration
    app.logger.info(f"Running with database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Import and register blueprints later when implementing
    # from app.api.routes import api as api_blueprint
    # app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Create all database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

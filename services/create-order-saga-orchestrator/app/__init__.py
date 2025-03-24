from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize SQLAlchemy without binding to an app
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """
    Application factory function to create and configure the Flask app
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/create_order_saga_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['USER_SERVICE_URL'] = os.getenv('USER_SERVICE_URL', 'http://localhost:3001')
    app.config['ORDER_SERVICE_URL'] = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    app.config['PAYMENT_SERVICE_URL'] = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:3003')
    app.config['ESCROW_SERVICE_URL'] = os.getenv('ESCROW_SERVICE_URL', 'http://localhost:3004')
    app.config['SCHEDULER_SERVICE_URL'] = os.getenv('SCHEDULER_SERVICE_URL', 'http://localhost:3005')
    app.config['NOTIFICATION_SERVICE_URL'] = os.getenv('NOTIFICATION_SERVICE_URL', 'http://localhost:3006')
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.api.routes import saga_bp
    app.register_blueprint(saga_bp)
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    return app

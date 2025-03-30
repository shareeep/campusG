from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
    app.config['KAFKA_BOOTSTRAP_SERVERS'] = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import and initialize Kafka and Orchestrator 
    from app.services.kafka_service import init_kafka, kafka_client
    from app.services.saga_orchestrator import init_orchestrator
    
    # Kafka is now a global instance, but we still initialize it
    app.logger.info("Initializing Kafka service...")
    init_kafka()  # This initializes the global kafka_client
    
    # Set the kafka_service property to the global instance for compatibility
    app.kafka_service = kafka_client
    
    if app.kafka_service and app.kafka_service.producer:
        app.logger.info("Kafka service initialized successfully.")
        app.logger.info("Initializing saga orchestrator...")
        app.orchestrator = init_orchestrator()
        if app.orchestrator:
             app.logger.info("Saga orchestrator initialized.")
        else:
             app.logger.error("Failed to initialize saga orchestrator.")
    else:
        app.logger.error("Failed to initialize Kafka service. Orchestrator initialization skipped.")
        app.orchestrator = None # Ensure orchestrator is None if Kafka failed
    
    # Register blueprints
    from app.api.routes import saga_bp
    app.register_blueprint(saga_bp)
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    return app

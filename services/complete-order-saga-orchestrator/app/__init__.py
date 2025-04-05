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

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """
    Application factory function to create and configure the Flask app for the Complete Order Saga.
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/complete_order_saga_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ORDER_SERVICE_URL'] = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    app.config['PAYMENT_SERVICE_URL'] = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:3003')
    app.config['USER_SERVICE_URL'] = os.getenv('USER_SERVICE_URL', 'http://localhost:3001')
    # Include other service URLs as necessary, e.g., Timer Service, if needed.
    app.config['KAFKA_BOOTSTRAP_SERVERS'] = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import and initialize Kafka and the Complete Order Saga orchestrator
    from app.services.kafka_service import init_complete_order_kafka, complete_order_kafka_client
    from app.services.complete_order_saga_orchestrator import init_complete_order_orchestrator
    
    app.logger.info("Initializing Kafka service for Complete Order Saga...")
    init_complete_order_kafka()  # This initializes the global complete_order_kafka_client
    app.kafka_service = complete_order_kafka_client
    
    if app.kafka_service and app.kafka_service.producer:
        app.logger.info("Kafka service initialized successfully.")
        app.logger.info("Initializing Complete Order Saga orchestrator...")
        app.orchestrator = init_complete_order_orchestrator()
        if app.orchestrator:
            app.logger.info("Complete Order Saga orchestrator initialized.")
        else:
            app.logger.error("Failed to initialize Complete Order Saga orchestrator.")
    else:
        app.logger.error("Failed to initialize Kafka service. Orchestrator initialization skipped.")
        app.orchestrator = None  # Ensure orchestrator is None if Kafka failed
    
    # Register blueprints for the Complete Order Saga endpoints
    from app.api.routes import complete_order_saga_bp
    app.register_blueprint(complete_order_saga_bp, url_prefix='/saga/complete')
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200
    
    return app

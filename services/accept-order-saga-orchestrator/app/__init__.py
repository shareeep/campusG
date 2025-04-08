# API package initialization
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize SQLAlchemy and Migrate without binding to an app
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """
    Application factory function to create and configure the Flask app for the Accept Order Saga.
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/accept_order_saga_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ORDER_SERVICE_URL'] = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    app.config['TIMER_SERVICE_URL'] = os.getenv('TIMER_SERVICE_URL', 'http://localhost:3003')
    app.config['KAFKA_BOOTSTRAP_SERVERS'] = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    app.config['KAFKA_TOPIC_ORDER_EVENTS'] = os.getenv('KAFKA_TOPIC_ORDER_EVENTS', 'order-events')
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize CORS
    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}}, # Allow frontend origin
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"], # Allow necessary headers
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"] # Allow necessary methods
    )

    # Initialize Kafka and Accept Order Saga orchestrator
    from app.services.kafka_service import init_accept_order_kafka, accept_order_kafka_client
    from app.services.saga_orchestrator import init_accept_order_orchestrator
    
    app.logger.info("Initializing Kafka service...")
    init_accept_order_kafka()  # This initializes the global kafka_client
    app.kafka_service = accept_order_kafka_client

    if app.kafka_service and app.kafka_service.producer:
        app.logger.info("Kafka service initialized successfully.")
        app.logger.info("Initializing Accept Order Saga orchestrator...")
        app.accept_order_orchestrator = init_accept_order_orchestrator()
        if app.accept_order_orchestrator:
            app.logger.info("Accept Order Saga orchestrator initialized.")
        else:
            app.logger.error("Failed to initialize Accept Order Saga orchestrator.")
    else:
        app.logger.error("Failed to initialize Kafka service. Accept Order Saga orchestrator initialization skipped.")
        app.accept_order_orchestrator = None

    # Register the Accept Order Saga blueprint
    from app.api.routes import accept_order_saga_bp
    app.register_blueprint(accept_order_saga_bp, url_prefix='/saga/accept')

    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200

    return app

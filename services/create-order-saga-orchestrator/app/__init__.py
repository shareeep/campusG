from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
import os
import logging
import atexit # Import atexit for shutdown hook

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
    CORS(app, resources={r"/orders*": {"origins": "http://localhost:5173"}}) # Initialize CORS for /orders endpoint from frontend origin
    
    # Import and initialize Kafka and Orchestrator 
    from app.services.kafka_service import init_kafka, kafka_client
    from app.services.saga_orchestrator import init_orchestrator
    
    # Kafka is now a global instance, but we still initialize it
    app.logger.info("Initializing Kafka service...")
    init_kafka(app)  # This initializes the global kafka_client and passes the Flask app context
    
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
    from app.api.timer_routes import timer_bp
    
    app.register_blueprint(saga_bp)
    app.register_blueprint(timer_bp)
    
    @app.route('/health')
    def health_check():
        # Disable request logging for health checks to reduce log spam
        return {'status': 'healthy'}, 200

    # Start the scheduler after app initialization
    if app.orchestrator:
        try:
            # Start polling every 60 seconds (adjust interval as needed)
            # Pass the 'app' instance to the scheduler start function
            app.orchestrator.start_scheduler(app, interval_seconds=60)
            
            # Register scheduler shutdown hook
            def shutdown_scheduler():
                app.logger.info("Flask app shutting down, stopping scheduler...")
                if app.orchestrator:
                    app.orchestrator.stop_scheduler()
            
            atexit.register(shutdown_scheduler)
            app.logger.info("Registered scheduler shutdown hook.")
            
        except Exception as e:
            app.logger.error(f"Failed to start or register scheduler: {str(e)}", exc_info=True)
    else:
        app.logger.warning("Orchestrator not available, scheduler not started.")

    return app

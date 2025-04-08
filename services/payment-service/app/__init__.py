import logging
import os
import stripe

from flask import Flask
from flask_cors import CORS # Import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Configure logging early
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize extensions first
db = SQLAlchemy()
migrate = Migrate()

# Import models AFTER db is defined but before create_app to potentially break circular dependency
from app import models

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    logger.info("Creating Flask app instance...")

    # --- Initialize CORS ---
    # Allow requests specifically from the frontend development server origin
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}) 
    logger.info(f"CORS configured for origin: http://localhost:5173")

    # --- Configuration Loading ---
    app.config.from_mapping(
        # Default settings
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'), # Use a more descriptive default
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@payment-db:5432/payment_db'), # Default to service name 'payment-db'
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Kafka settings (ensure these match environment variables set in docker-compose)
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        # Stripe settings
        STRIPE_SECRET_KEY=os.environ.get('STRIPE_SECRET_KEY'), # No default for secret key
        STRIPE_PUBLISHABLE_KEY=os.environ.get('STRIPE_PUBLISHABLE_KEY'), # Add publishable key
        STRIPE_WEBHOOK_SECRET=os.environ.get('STRIPE_WEBHOOK_SECRET'), # No default for webhook secret
    )

    # Validate essential config
    if not app.config.get('STRIPE_SECRET_KEY'):
        logger.critical("FATAL ERROR: STRIPE_SECRET_KEY is not configured!")
    if not app.config.get('STRIPE_WEBHOOK_SECRET'):
         logger.critical("FATAL ERROR: STRIPE_WEBHOOK_SECRET is not configured!")

    # Load custom config if provided (e.g., for testing)
    if config:
        app.config.from_mapping(config)
        logger.info("Applied custom configuration mapping.")

    # --- Initialize Extensions ---
    db.init_app(app)
    logger.info("SQLAlchemy initialized.")
    migrate.init_app(app, db)
    logger.info("Flask-Migrate initialized.")

    # --- Set Stripe API Key ---
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
    if stripe.api_key:
        logger.info("Stripe API key configured.")
    else:
        logger.error("Stripe API key is MISSING.") # Already logged critical, but reiterate

    # --- Register Blueprints ---
    from app.api.payment_routes import api as payment_api_blueprint
    # Register payment API blueprint at the root
    app.register_blueprint(payment_api_blueprint) 
    logger.info("Registered payment API blueprint at root.")

    from app.api.webhook_routes import webhook as webhook_blueprint
    # Register webhook blueprint at the root
    app.register_blueprint(webhook_blueprint) 
    logger.info("Registered webhook blueprint at root.")

    # --- Application Context Setup ---
    with app.app_context():
        logger.info("Entering application context for setup...")
        # Models are already imported at the module level now

        # --- Database Initialization ---
        # Consider moving DB creation/migration to a separate CLI command (flask db init/migrate/upgrade)
        # For simplicity here, we check and create if needed.
        try:
            # Explicitly import Payment here to potentially reveal import errors in models.py
            from app.models.models import Payment
            inspector = db.inspect(db.engine)
            if not inspector.has_table(Payment.__tablename__):
                logger.info(f"Table '{Payment.__tablename__}' not found. Attempting db.create_all().")
                # This might fail if migrations haven't defined the enum type in the DB
                try:
                    db.create_all()
                    logger.info("Database tables created successfully via db.create_all().")
                except Exception as create_err:
                     logger.error(f"Error during db.create_all(): {create_err}. Manual migration might be needed ('flask db migrate/upgrade').", exc_info=True)
            else:
                logger.info(f"Database table '{models.Payment.__tablename__}' already exists.")
        except Exception as inspect_err:
             logger.error(f"Error inspecting database: {inspect_err}. Database might not be accessible.", exc_info=True)


        # --- Kafka Initialization and Command Handler Registration ---
        try:
            # Import Kafka client instance and init function
            from app.services.kafka_service import kafka_client, init_kafka
            # Import the command handler functions
            from app.services.stripe_service import handle_authorize_payment_command, handle_release_payment_command, handle_revert_payment_command

            # Register the handlers BEFORE starting the consumer
            kafka_client.register_command_handler('authorize_payment', handle_authorize_payment_command)
            kafka_client.register_command_handler('release_payment', handle_release_payment_command)
            kafka_client.register_command_handler('revert_payment', handle_revert_payment_command)

            # Store the app instance in the KafkaService
            kafka_client.app = app
            
            # Initialize Kafka (connects, starts consumer thread, no teardown registration needed now)
            init_kafka(app) 
            logger.info("Kafka client initialized and consumer started.")
            
            # Make kafka_client available to the application
            app.kafka_client = kafka_client

        except Exception as kafka_init_err:
            logger.error(f"Failed to initialize Kafka service: {kafka_init_err}", exc_info=True)
            # The application might still run but won't process Kafka messages.

        logger.info("Application context setup finished.")

    logger.info("Flask app creation completed.")
    return app

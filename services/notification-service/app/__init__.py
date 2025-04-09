from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
from flasgger import Swagger # Import Swagger
import os

# Initialize SQLAlchemy without binding to a specific app
db = SQLAlchemy()
migrate = Migrate()

def create_app(config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Initialize CORS - Allow requests from frontend origin with explicit methods/headers
    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        methods=["GET", "POST", "OPTIONS"], # Allow relevant methods + OPTIONS
        allow_headers=["Content-Type", "Authorization"], # Allow common headers
        supports_credentials=True # Allow cookies if needed
    )
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/notification_db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        TWILIO_ACCOUNT_SID=os.environ.get('TWILIO_ACCOUNT_SID', ''),
        TWILIO_AUTH_TOKEN=os.environ.get('TWILIO_AUTH_TOKEN', ''),
        TWILIO_PHONE_NUMBER=os.environ.get('TWILIO_PHONE_NUMBER', ''),
    )
    
    # Load custom config if provided
    if config:
        app.config.from_mapping(config)
    
    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    swagger = Swagger(app) # Initialize Flasgger
    app.logger.info("Flasgger initialized for Swagger UI at /apidocs/")
    
    # Register blueprints
    from app.api.notification_routes import api as notification_api
    # Register blueprint at root
    app.register_blueprint(notification_api) 
    
    # Register CLI commands
    from app import cli
    cli.init_app(app)
    
    # Removed redundant /health route (it's defined in api/notification_routes.py now)
    
    # Setup database
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import models
        
        # Create tables if they don't exist
        # Use try-except to handle the case where enum types already exist
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Error during db.create_all(): {str(e)}")
            
            # If there's an error with duplicate types, try to create tables individually
            # This approach will skip the enum type creation but still create tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # Get all table names from the models
            model_tables = db.metadata.tables.keys()
            
            # Get existing tables in the database
            existing_tables = inspector.get_table_names()
            
            # Create only tables that don't exist yet
            for table_name in model_tables:
                if table_name not in existing_tables:
                    app.logger.info(f"Creating table {table_name}")
                    try:
                        # Create just this table
                        db.metadata.tables[table_name].create(db.engine)
                    except Exception as table_error:
                        app.logger.error(f"Failed to create table {table_name}: {str(table_error)}")
    
    return app

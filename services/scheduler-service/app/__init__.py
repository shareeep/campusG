from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize SQLAlchemy without binding to a specific app
db = SQLAlchemy()
migrate = Migrate()

def create_app(config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/scheduler_db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    )
    
    # Load custom config if provided
    if config:
        app.config.from_mapping(config)
    
    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.api.scheduler_routes import api as scheduler_api
    app.register_blueprint(scheduler_api, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200
    
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

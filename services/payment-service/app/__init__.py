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
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/payment_db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        STRIPE_API_KEY=os.environ.get('STRIPE_API_KEY', 'sk_test_your_key'),
        STRIPE_WEBHOOK_SECRET=os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_your_secret'),
    )
    
    # Load custom config if provided
    if config:
        app.config.from_mapping(config)
    
    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register middlewares
    from app.middleware.tracing import TracingMiddleware
    tracing_middleware = TracingMiddleware()
    tracing_middleware.init_app(app)
    
    # Register blueprints
    from app.api.payment_routes import api as payment_api
    app.register_blueprint(payment_api, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Create log API blueprint and register it
    from flask import Blueprint
    from app.models.system_log import SystemLog
    from flask import jsonify, request
    
    log_api = Blueprint('logs', __name__)
    
    @log_api.route('/logs', methods=['GET'])
    def get_logs():
        """Get system logs with optional filtering"""
        # Query parameters
        level = request.args.get('level')
        trace_id = request.args.get('traceId')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = SystemLog.query
        
        if level:
            query = query.filter_by(level=level)
            
        if trace_id:
            query = query.filter_by(trace_id=trace_id)
        
        # Get logs with limit
        logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs]
        })
    
    @log_api.route('/logs/trace/<trace_id>', methods=['GET'])
    def get_logs_by_trace(trace_id):
        """Get all logs for a specific trace"""
        logs = SystemLog.query.filter_by(trace_id=trace_id).order_by(SystemLog.timestamp).all()
        
        return jsonify({
            'success': True,
            'traceId': trace_id,
            'logs': [log.to_dict() for log in logs]
        })
    
    app.register_blueprint(log_api, url_prefix='/api')
    
    # Setup database
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import models
        from app.models import system_log
        
        # Configure stripe placeholder API key
        from app.utils import stripe_placeholder as stripe
        stripe.api_key = app.config.get('STRIPE_API_KEY', 'sk_test_your_key')
        
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
    
    # Start log consumer in a background thread if in production
    if not app.debug:
        from app.services.log_consumer import start_log_consumer_thread
        start_log_consumer_thread(app)
    
    return app

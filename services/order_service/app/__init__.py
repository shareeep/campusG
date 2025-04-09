from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS # Import CORS
from flask_migrate import Migrate # Uncomment Migrate import
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate() # Uncomment Migrate initialization

# Import config here to avoid circular imports
from app.config.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db) # Uncomment Migrate initialization with app

    # Initialize CORS - Allow requests from frontend origin with specific headers/methods
    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        supports_credentials=True, # Allow cookies if needed in the future
        allow_headers=["Content-Type", "Authorization"], # Explicitly allow required headers
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"] # Allow standard methods + OPTIONS for preflight
    )

    # Register blueprints
    from app.api.routes import api as api_blueprint
    # Register blueprint at root
    app.register_blueprint(api_blueprint) 
    
    # Removed redundant /health route (it's defined in api/routes.py now)
    
    # Log configuration
    app.logger.info(f"Running with database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.logger.info(f"Mock services enabled: {app.config.get('MOCK_SERVICES', False)}")

    return app

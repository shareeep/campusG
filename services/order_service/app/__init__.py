from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Initialize extensions
db = SQLAlchemy()
# migrate = Migrate()

# Import config here to avoid circular imports
from app.config.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    # migrate.init_app(app, db)

    # Register blueprints
    from app.api.routes import api as api_blueprint
    # Register blueprint at root
    app.register_blueprint(api_blueprint) 
    
    # Removed redundant /health route (it's defined in api/routes.py now)
    
    # Log configuration
    app.logger.info(f"Running with database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.logger.info(f"Mock services enabled: {app.config.get('MOCK_SERVICES', False)}")

    return app

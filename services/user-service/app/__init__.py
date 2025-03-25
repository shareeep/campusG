# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
import logging
import sys

# Configure logging first
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@user-db:5432/user_service_db')  # Updated database name
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure CORS
    # Allow requests from your frontend development server
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",  # Vite dev server
                "http://localhost:3000",   # Next.js dev server
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
                # Add your production domain when deployed
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    logger.info("CORS configured for API routes")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models to ensure they're known to Flask-Migrate
    from app.models import models

    # Register blueprints
    from app.api.user_routes import api as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Initialize the database if it doesn't exist
    with app.app_context():
        try:
            # Check if tables exist by querying one
            db.session.execute("SELECT 1 FROM users LIMIT 1")
            logger.info("Database tables already exist")
        except Exception as e:
            logger.info(f"Creating database tables: {str(e)}")
            db.create_all()
            logger.info("Database tables created successfully")

    @app.route('/health', methods=['GET'])
    def health_check():
        logger.info("Health check endpoint accessed")
        return {'status': 'healthy'}, 200
    

    return app
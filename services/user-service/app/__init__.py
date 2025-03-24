# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from clerk_backend_api import Clerk

db = SQLAlchemy()
migrate = Migrate()
clerk_client = None  # Initialize Clerk client as None

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres-user:5432/user_service_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize Clerk
    clerk_secret_key = os.environ.get("CLERK_SECRET_KEY")
    if not clerk_secret_key:
        raise ValueError("CLERK_SECRET_KEY environment variable not set.")
    global clerk_client
    clerk_client = Clerk(secret_key=clerk_secret_key)

    # Store the Clerk client in the Flask app's extensions for easy access
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['clerk'] = clerk_client

    # Import models to ensure they're known to Flask-Migrate
    from app.models import models

    # Register blueprints
    from app.api.user_routes import api as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy'}, 200

    return app
from flask import Flask
# from flask_sqlalchemy import SQLAlchemy # Removed as DB is not needed
from config import Config

# db = SQLAlchemy() # Removed as DB is not needed

def create_app():
    # This function might not be actively used if api_trigger.py and worker.py run independently
    app = Flask(__name__)
    app.config.from_object(Config)
    # db.init_app(app) # Removed as DB is not needed

    # with app.app_context(): # Removed as DB is not needed
        # from . import models # This import will likely fail now anyway as models.py doesn't exist
        # db.create_all()  # Create tables

    return app

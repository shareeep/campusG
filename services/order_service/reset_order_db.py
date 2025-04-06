import sys
import os

# Add the parent directory (services/order_service) to the Python path
# This allows importing 'app' from the correct location
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
# Import models to ensure they are registered with SQLAlchemy
from app.models import models

# Create a Flask app instance to work with the database context
app = create_app()

def reset_database():
    """Drops all tables and recreates them based on current models."""
    with app.app_context():
        print("Dropping all database tables...")
        try:
            db.drop_all()
            print("Tables dropped successfully.")
        except Exception as e:
            print(f"Error dropping tables: {e}")
            # Attempt to drop the enum type manually if drop_all failed due to it
            try:
                print("Attempting to drop orderstatus enum manually...")
                # Note: Enum type name might vary based on SQLAlchemy/PostgreSQL version
                # Common names are 'orderstatus' or 'order_status'
                db.session.execute(db.text("DROP TYPE IF EXISTS orderstatus CASCADE;"))
                db.session.commit()
                print("Manual enum drop attempted. Retrying drop_all...")
                db.drop_all()
                print("Tables dropped successfully after manual enum drop.")
            except Exception as e_manual:
                print(f"Error during manual enum drop or second drop_all: {e_manual}")
                print("Proceeding to create_all, but schema might be inconsistent.")


        print("\nCreating all database tables based on current models...")
        try:
            db.create_all()
            print("Tables created successfully.")
            print("\nDatabase reset complete. The schema should now match your models.")
        except Exception as e:
            print(f"Error creating tables: {e}")
            print("\nDatabase reset failed during table creation.")

if __name__ == "__main__":
    reset_database()

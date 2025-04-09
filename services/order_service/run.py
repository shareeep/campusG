from app import create_app, db
from app.services.kafka_service import init_kafka
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = create_app()

from sqlalchemy.exc import IntegrityError
from psycopg2 import errors # Import specific psycopg2 errors if needed

# Create tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created or verified.")
    except IntegrityError as e:
        # Check if the error is specifically about duplicate objects (like types/tables)
        # This check might need adjustment based on the exact error details/database driver
        # For psycopg2, UniqueViolation is a common error code for this.
        # We can make this check more specific if needed, but catching IntegrityError is often sufficient.
        # if isinstance(e.orig, errors.UniqueViolation) or "already exists" in str(e).lower():
        logging.warning(f"Database objects likely already exist, skipping creation: {e}")
        db.session.rollback() # Rollback the failed transaction
        # else:
        #     # Re-raise other integrity errors
        #     raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred during DB initialization: {e}")
        db.session.rollback() # Rollback on other errors too
        # Optionally re-raise or handle differently
        raise e


# Initialize Kafka service
init_kafka(app)
logging.info("Kafka service initialized")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)

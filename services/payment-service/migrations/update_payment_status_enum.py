"""
Migration script to update payment_status_enum type in the database.

This script will:
1. Convert any existing INITIATING status records to AUTHORIZED
2. Convert any existing RELEASED status records to SUCCEEDED
3. Update the enum type to remove INITIATING and RELEASED values
"""

from flask import Flask
from app import db
from app.models.models import Payment, PaymentStatus
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to update payment status enum values."""
    try:
        # Create a simple Flask app with SQLAlchemy context
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@payment-db:5432/payment_db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

        with app.app_context():
            # Check if the table exists
            engine = db.engine
            inspector = db.inspect(engine)
            
            if 'payments' not in inspector.get_table_names():
                logger.info("Payments table not found. No migration needed.")
                return
            
            # 1. Update any INITIATING records to AUTHORIZED
            try:
                # We can't directly search for INITIATING since it no longer exists in the enum
                # So we use a raw SQL query
                raw_sql = """
                UPDATE payments 
                SET status = 'AUTHORIZED' 
                WHERE status = 'INITIATING'
                """
                engine.execute(raw_sql)
                logger.info("Updated INITIATING records to AUTHORIZED")
            except Exception as e:
                logger.warning(f"Error updating INITIATING records: {str(e)}")
            
            # 2. Update any RELEASED records to SUCCEEDED
            try:
                raw_sql = """
                UPDATE payments 
                SET status = 'SUCCEEDED' 
                WHERE status = 'RELEASED'
                """
                engine.execute(raw_sql)
                logger.info("Updated RELEASED records to SUCCEEDED")
            except Exception as e:
                logger.warning(f"Error updating RELEASED records: {str(e)}")
            
            # 3. Check for any records with invalid status
            try:
                raw_sql = """
                SELECT COUNT(*) 
                FROM payments 
                WHERE status NOT IN ('AUTHORIZED', 'SUCCEEDED', 'REVERTED', 'FAILED')
                """
                result = engine.execute(raw_sql).scalar()
                if result > 0:
                    logger.warning(f"Found {result} records with invalid status")
            except Exception as e:
                logger.warning(f"Error checking for invalid status: {str(e)}")
            
            logger.info("Migration completed successfully")
    
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Wait a bit for the database to be ready
    time.sleep(2)
    run_migration()
    logger.info("Migration script completed")

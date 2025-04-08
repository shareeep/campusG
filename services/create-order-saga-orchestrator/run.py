from app import create_app, db
import os
import logging
from flask_migrate import Migrate, upgrade
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create app
app = create_app()

# # Wait for PostgreSQL to be ready (useful in containerized environments)
# def wait_for_postgres():
#     with app.app_context():
#         retries = 10
#         while retries > 0:
#             try:
#                 # Try to connect
#                 db.engine.connect()
#                 logger.info("Successfully connected to PostgreSQL database")
#                 return True
#             except Exception as e:
#                 retries -= 1
#                 logger.warning(f"Could not connect to PostgreSQL. {e}. Retrying in 5 seconds... ({retries} retries left)")
#                 time.sleep(5)
# # Wait for PostgreSQL to be ready (useful in containerized environments)
# def wait_for_postgres():
#     with app.app_context():
#         retries = 10
#         while retries > 0:
#             try:
#                 # Try to connect
#                 db.engine.connect()
#                 logger.info("Successfully connected to PostgreSQL database")
#                 return True
#             except Exception as e:
#                 retries -= 1
#                 logger.warning(f"Could not connect to PostgreSQL. {e}. Retrying in 5 seconds... ({retries} retries left)")
#                 time.sleep(5)
        
#         logger.error("Could not connect to PostgreSQL after multiple retries")
#         return False
#         logger.error("Could not connect to PostgreSQL after multiple retries")
#         return False

# # Run database migrations automatically
# def run_migrations():
#     try:
#         logger.info("Running database migrations...")
#         with app.app_context():
#             # Initialize migrations directory path
#             migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
# # Run database migrations automatically
# def run_migrations():
#     try:
#         logger.info("Running database migrations...")
#         with app.app_context():
#             # Initialize migrations directory path
#             migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            
#             if not os.path.exists(migrations_dir):
#                 logger.error(f"Migrations directory not found at {migrations_dir}")
#                 return False
#             if not os.path.exists(migrations_dir):
#                 logger.error(f"Migrations directory not found at {migrations_dir}")
#                 return False
            
#             # Create migration object
#             migrate = Migrate(app, db, directory=migrations_dir)
#             # Create migration object
#             migrate = Migrate(app, db, directory=migrations_dir)
            
#             # Run migrations
#             upgrade(directory=migrations_dir)
#             # Run migrations
#             upgrade(directory=migrations_dir)
            
#             logger.info("Database migrations completed successfully")
#             return True
#     except Exception as e:
#         logger.error(f"Error running migrations: {e}")
#         return False

# if __name__ == '__main__':
#     # Ensure database is available
#     if wait_for_postgres():
#         # Run migrations
#         if run_migrations():
#             # Start the application
#             logger.info("Starting Create Order Saga Orchestrator service...")
#             app.run(host='0.0.0.0', port=3000)
#         else:
#             logger.error("Failed to run migrations. Application not started.")
#     else:
#         logger.error("Could not connect to database. Application not started.")
        
        
        
if __name__ == '__main__':
    # Ensure database is available
    with app.app_context():
        db.create_all()
    # if wait_for_postgres():
    #     # Run migrations
    #     if run_migrations():
    #         # Start the application
    #         logger.info("Starting Create Order Saga Orchestrator service...")
    app.run(host='0.0.0.0', port=3000)
    #     else:
    #         logger.error("Failed to run migrations. Application not started.")
    # else:
    #     logger.error("Could not connect to database. Application not started.")

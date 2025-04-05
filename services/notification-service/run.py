"""
Notification Service - Entry point for the Flask application.
"""
from app import create_app, db
import threading
import logging
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
)

logger = logging.getLogger(__name__)

app = create_app()

# Initialize database
with app.app_context():
    db.create_all()
    logger.info("Database tables created (if they didn't exist)")

# Start the Kafka poller in a separate thread if enabled
if os.environ.get('ENABLE_KAFKA_POLLING', 'true').lower() == 'true':
    logger.info("Starting Kafka polling mechanism...")
    # Define a self-contained polling function that creates its own app context
    def run_poller():
        # Wait a few seconds for main app to be fully initialized
        time.sleep(5)
        
        # Create a separate app instance for this thread to avoid context issues
        poller_app = create_app()
        
        # Get the poll interval from environment
        interval = int(os.environ.get('KAFKA_POLL_INTERVAL_SECONDS', '10'))
        
        logger.info(f"Poller thread starting with {interval}s interval")
        
        while True:
            try:
                # Use this app's context explicitly
                with poller_app.app_context():
                    from app.services.poll_service import poll_kafka_once
                    logger.info("Polling Kafka with dedicated app context")
                    count = poll_kafka_once()
                    logger.info(f"Processed {count} messages from Kafka")
            except Exception as e:
                logger.error(f"Error in Kafka polling: {e}", exc_info=True)
                # If we had an error, try to recreate the app context
                try:
                    poller_app = create_app()
                    logger.info("Recreated poller app context after error")
                except Exception as app_error:
                    logger.error(f"Failed to recreate app context: {app_error}")
                    # Brief pause if we're having issues
                    time.sleep(5)
            
            # Wait for next polling cycle
            time.sleep(interval)
    
    # Start the poller in a non-daemon thread so it keeps running
    kafka_thread = threading.Thread(target=run_poller, daemon=False)
    kafka_thread.start()
    logger.info(f"Kafka poller started in thread {kafka_thread.name}")

if __name__ == "__main__":
    # Run Flask app in the main thread
    app.run(host="0.0.0.0", port=3000, debug=True)

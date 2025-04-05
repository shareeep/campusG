"""
CLI commands for the notification service
"""
import click
from flask.cli import with_appcontext
import logging
import threading
import os
import time
from app.services.poll_service import poll_kafka_once

logger = logging.getLogger(__name__)

@click.command('poll-kafka')
@with_appcontext
def poll_kafka_command():
    """Poll Kafka once for new messages and save to the database."""
    click.echo('Polling Kafka for new messages...')
    messages_processed = poll_kafka_once()
    click.echo(f'Processed {messages_processed} messages')

@click.command('start-kafka-poller')
def start_kafka_poller_command():
    """Start the Kafka poller in a background thread."""
    # Don't use with_appcontext here to avoid context issues
    # We'll create our own app instance inside the thread
    
    # Create a simple polling function that doesn't use current_app
    def poll_periodically():
        """Poll Kafka at regular intervals."""
        # Import Flask app inside the thread to avoid context issues
        from app import create_app
        poll_app = create_app()
        
        # Set polling interval from environment or default
        interval = int(os.getenv('KAFKA_POLL_INTERVAL_SECONDS', '10'))
        logger.info(f"Starting Kafka polling thread with interval {interval}s")
        
        while True:
            try:
                # Use the app instance context explicitly
                with poll_app.app_context():
                    logger.info("Polling Kafka with explicit app context")
                    messages = poll_kafka_once()
                    logger.info(f"Poll processed {messages} messages")
            except Exception as e:
                logger.error(f"Error in polling thread: {e}", exc_info=True)
                # Try to recreate app in case of failure
                try:
                    poll_app = create_app()
                    logger.info("Recreated app instance after error")
                except Exception as app_err:
                    logger.error(f"Failed to recreate app: {app_err}")
            
            # Sleep until next poll
            time.sleep(interval)
    
    click.echo('Starting Kafka poller in a background thread...')
    # Create non-daemon thread to ensure it keeps running
    thread = threading.Thread(target=poll_periodically, daemon=False)
    thread.start()
    click.echo(f'Kafka poller started in thread {thread.name}')

def init_app(app):
    """Register CLI commands with the app."""
    app.cli.add_command(poll_kafka_command)
    app.cli.add_command(start_kafka_poller_command)

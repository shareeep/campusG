"""
Notification Service - Entry point for the Flask application.
"""
from app import create_app, db
from app.api.notification_routes import start_kafka_consumer

import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
)

app = create_app()

# Initialize database
with app.app_context():
    db.create_all()
    logging.info("Database tables created (if they didn't exist)")

# Start Kafka consumer in a background thread within app context
with app.app_context():
    start_kafka_consumer()
    logging.info("Kafka consumer started in background thread")

if __name__ == "__main__":
    # Run Flask app in the main thread
    app.run(host="0.0.0.0", port=3000, debug=True)

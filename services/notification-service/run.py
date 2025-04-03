"""
Notification Service - Entry point for the Flask application.
"""
from app import create_app
from app.api.notification_routes import start_kafka_consumer

app = create_app()

if __name__ == "__main__":
    # Start Kafka consumer in a background thread
    start_kafka_consumer()
    # Run Flask app in the main thread
    app.run(host="0.0.0.0", port=3000, debug=True)
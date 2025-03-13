from app import create_app, db
from app.services.kafka_service import kafka_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

app = create_app()

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    logging.info("Database tables created (if they didn't exist)")

@app.before_first_request
def setup():
    # Connect to Kafka
    kafka_client.connect()

@app.teardown_appcontext
def shutdown(exception=None):
    # Disconnect from Kafka when the application shuts down
    kafka_client.disconnect()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)

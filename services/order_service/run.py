from app import create_app, db
from app.services.kafka_service import init_kafka
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

# Initialize Kafka service
init_kafka(app)
logging.info("Kafka service initialized")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)

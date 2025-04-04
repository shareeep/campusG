'''
This is a fix for the Flask application context issue in the payment service.

PROBLEM: The Kafka message handler runs in a separate thread and tries to access 
the database outside of a Flask application context, resulting in the error:
"RuntimeError: Working outside of application context"

SOLUTION: Store the Flask app instance in the KafkaService and wrap database operations 
in an application context when processing messages from Kafka.
'''

# 1. First, modify KafkaService to store the Flask app instance

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from flask import Flask

from kafka import KafkaConsumer, KafkaProducer

logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
PAYMENT_COMMANDS_TOPIC = 'payment_commands'
PAYMENT_EVENTS_TOPIC = 'payment_events'
CONSUMER_GROUP_ID = 'payment-service-group'

class KafkaService:
    """Kafka client for the Payment Service"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating KafkaService instance")
            cls._instance = super(KafkaService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info("Initializing KafkaService")
        self.bootstrap_servers = KAFKA_BOOTSTRAP_SERVERS
        self.producer = None
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        self.command_handlers = {}
        self.app = None  # Store the Flask app instance
        self._connect()
        self._initialized = True
        logger.info("KafkaService initialized")

    # All other methods remain the same except for _process_message
    
    def _process_message(self, message):
        """Process a received Kafka command message with app context."""
        try:
            command_data = message.value
            command_type = command_data.get('type')
            correlation_id = command_data.get('correlation_id')
            payload = command_data.get('payload', {})

            if not command_type or not correlation_id:
                logger.warning(f"Received invalid message structure on {message.topic}: {command_data}")
                return

            logger.info(f"Received command {command_type} from {message.topic} with correlation_id {correlation_id}")

            handler = self.command_handlers.get(command_type)
            if handler:
                logger.debug(f"Executing handler for {command_type} (correlation_id: {correlation_id})")
                # Run handler in a separate thread with app context
                thread = threading.Thread(
                    target=self._run_handler_with_app_context, 
                    args=(handler, correlation_id, payload)
                )
                thread.start()
            else:
                logger.warning(f"No handler registered for command type: {command_type}")

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message from {message.topic}: {message.value}")
        except Exception as e:
            logger.error(f"Error processing message from {message.topic}: {e}", exc_info=True)

    def _run_handler_with_app_context(self, handler, correlation_id, payload):
        """Execute handler function within app context."""
        if not self.app:
            logger.error("Cannot run handler with app context: Flask app not set")
            return
            
        with self.app.app_context():
            try:
                handler(correlation_id, payload)
            except Exception as e:
                logger.error(f"Error in handler execution: {e}", exc_info=True)

# Modified init_kafka function to store the app instance
def init_kafka(app):
    """Initialize the Kafka client and start consuming."""
    global kafka_client
    
    if not isinstance(app, Flask):
        logger.error("Invalid Flask app instance provided to init_kafka")
        return None
        
    # Store the app instance in the KafkaService
    kafka_client.app = app
    
    # Rest of the function remains the same
    # ...

# 2. Now modify handle_authorize_payment_command to remove the app_context wrapper since KafkaService will handle it:

def handle_authorize_payment_command(correlation_id, payload):
    """
    Handles the 'authorize_payment' command received from Kafka.
    Attempts to create and confirm a Stripe Payment Intent.
    Publishes 'payment.authorized' or 'payment.failed' event back to Kafka.
    """
    logger.info(f"Handling authorize_payment command for correlation_id: {correlation_id}")
    global kafka_client # Use the global Kafka client instance
    
    # Import current_app at the top of the file if not already imported
    from flask import current_app
    
    # Wrap all database operations in an application context
    with current_app.app_context():
        # --- 1. Extract data from payload ---
        try:
            order_id = payload.get('order_id')
            # Use clerk_user_id from payload as our internal customer_id
            customer_id = payload.get('customer', {}).get('clerkUserId')
            stripe_customer_id = payload.get('customer', {}).get('stripeCustomerId')
            # Assuming payment_info contains payment_method_id under userStripeCard
            payment_method_id = payload.get('customer', {}).get('userStripeCard', {}).get('payment_method_id')
            # Amount is expected in cents from saga orchestrator/frontend
            amount_cents = payload.get('order', {}).get('amount')
            description = payload.get('order', {}).get('description', f"Payment for order {order_id}")
            return_url = payload.get('return_url') # Optional, for 3DS redirects

            # --- Validation ---
            if not all([order_id, customer_id, stripe_customer_id, payment_method_id, amount_cents]):
                error_msg = "Missing required fields in authorize_payment command payload"
                logger.error(f"{error_msg} for correlation_id: {correlation_id}. Payload: {payload}")
                publish_payment_failed_event(kafka_client, correlation_id, {'error': 'INVALID_PAYLOAD', 'message': error_msg})
                return

            if not isinstance(amount_cents, int) or amount_cents < 50: # Stripe minimum is typically 50 cents
                error_msg = f"Invalid amount: {amount_cents}. Must be an integer >= 50 cents."
                logger.error(f"{error_msg} for correlation_id: {correlation_id}")
                publish_payment_failed_event(kafka_client, correlation_id, {'error': 'INVALID_AMOUNT', 'message': error_msg})
                return

        except Exception as e:
            error_msg = f"Error parsing authorize_payment payload: {str(e)}"
            logger.error(f"{error_msg} for correlation_id: {correlation_id}. Payload: {payload}", exc_info=True)
            publish_payment_failed_event(kafka_client, correlation_id, {'error': 'PAYLOAD_PARSE_ERROR', 'message': error_msg})
            return

        # --- 2. Create/Update Payment Record in DB ---
        payment = None
        try:
            # Check if a payment record already exists for this order_id (e.g., retry scenario)
            payment = Payment.query.filter_by(order_id=order_id).first()
            payment_id = None

            if payment:
                logger.warning(f"Existing payment record found for order_id {order_id}. Updating status to INITIATING.")
                payment.status = PaymentStatus.INITIATING
                payment.customer_id = customer_id # Update just in case
                payment.amount = amount_cents / 100.0
                payment.description = description
                payment.updated_at = datetime.now(timezone.utc)
                payment_id = payment.payment_id # Use existing ID
            else:
                payment_id = str(uuid.uuid4())
                payment = Payment(
                    payment_id=payment_id,
                    order_id=order_id,
                    customer_id=customer_id, # Using clerk_user_id
                    amount=amount_cents / 100.0, # Store as dollars/euros etc.
                    status=PaymentStatus.INITIATING,
                    description=description,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                    # payment_intent_id will be added after successful Stripe call
                )
                db.session.add(payment)

            db.session.commit()
            logger.info(f"Payment record {payment_id} created/updated for order {order_id}, status: INITIATING")

        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = f"Database error preparing payment record for order {order_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            publish_payment_failed_event(kafka_client, correlation_id, {'error': 'DATABASE_ERROR', 'message': error_msg})
            return
        except Exception as e: # Catch broader exceptions during DB interaction
            db.session.rollback()
            error_msg = f"Unexpected error preparing payment record for order {order_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            publish_payment_failed_event(kafka_client, correlation_id, {'error': 'DB_UNEXPECTED_ERROR', 'message': error_msg})
            return

        # --- 3. Interact with Stripe API ---
        # Continue with rest of function...
        # (The rest of the function remains unchanged)

# Update the update_payment_status function to remove the app_context wrapper:
def update_payment_status(payment_id, new_status: PaymentStatus, payment_intent_id=None):
    """Updates the status of a payment record in the database."""
    if not isinstance(new_status, PaymentStatus):
        logger.error(f"Invalid status type provided to update_payment_status: {type(new_status)}")
        return False

    try:
        # Change from query.get() to filter_by() to look up by payment_id instead of primary key
        payment = Payment.query.filter_by(payment_id=payment_id).first()
        if not payment:
            logger.error(f"Payment record with payment_id {payment_id} not found for status update.")
            return False

        payment.status = new_status
        payment.updated_at = datetime.now(timezone.utc)
        # Optionally update intent ID if provided (e.g., if initial creation failed before saving it)
        if payment_intent_id and not payment.payment_intent_id:
            payment.payment_intent_id = payment_intent_id

        db.session.commit()
        logger.info(f"Payment record {payment_id} status updated to {new_status.value}")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating status for payment {payment_id}: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error updating status for payment {payment_id}: {str(e)}", exc_info=True)
        return False

# Fix the StripeService class methods to remove app_context and complete the try block:

@staticmethod
def capture_payment(payment_id):
    """Captures a previously authorized payment (called when order completes)."""
    logger.info(f"Attempting to capture payment {payment_id}")
    
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            logger.error(f"Payment {payment_id} not found for capture.")
            return {"success": False, "error": "not_found"}
        if not payment.payment_intent_id:
            logger.error(f"Payment {payment_id} has no payment_intent_id for capture.")
            return {"success": False, "error": "missing_intent_id"}

        # Check local status first
        if payment.status != PaymentStatus.AUTHORIZED:
            logger.warning(f"Attempting to capture payment {payment_id} not in AUTHORIZED state (state: {payment.status.value}). Proceeding with Stripe capture check.")
            # Allow proceeding, Stripe will enforce its state

        # Capture the payment via Stripe
        captured_intent = stripe.PaymentIntent.capture(payment.payment_intent_id)
        logger.info(f"Stripe capture successful for PaymentIntent {payment.payment_intent_id}, status: {captured_intent.status}")

        # Update local status based on Stripe's response
        new_status = PaymentStatus.SUCCEEDED if captured_intent.status == 'succeeded' else PaymentStatus.FAILED
        update_payment_status(payment.payment_id, new_status)

        return {"success": True, "status": new_status.value, "stripe_status": captured_intent.status}

    except stripe.error.StripeError as e:
        error_msg = f"Stripe error capturing payment {payment_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_payment_status(payment.payment_id, PaymentStatus.FAILED)
        return {"success": False, "error": "stripe_error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error capturing payment {payment_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_payment_status(payment.payment_id, PaymentStatus.FAILED)
        return {"success": False, "error": "unexpected_error", "message": error_msg}

# 3. Implementation notes:
#
# To fix the payment service:
# 1. Update app/__init__.py to modify how kafka_client is initialized
# 2. Update app/services/kafka_service.py with the changes to KafkaService class
# 3. Keep the stripe_service.py handler functions unchanged - they don't need Flask app_context wrappers now
#
# This design pattern is better because:
# - The app context management is centralized in the Kafka service
# - Command handlers don't need to know about Flask context management
# - It follows separation of concerns principles

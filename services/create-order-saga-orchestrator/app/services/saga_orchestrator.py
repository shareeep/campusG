import logging
from datetime import datetime, timedelta
from app import db
from app.models.saga_state import CreateOrderSagaState, SagaStatus, SagaStep
from flask import current_app # Ensure current_app is imported
from app.services.kafka_service import (
    publish_create_order_command,
    publish_get_user_payment_info_command,
    publish_authorize_payment_command,
    publish_update_order_status_command,
    publish_start_timer_command,
    # Import compensation command publishers
    publish_cancel_order_command,
    publish_revert_payment_command
)
from app.services.http_client import http_client
import threading # For potential background tasks like polling
from apscheduler.schedulers.background import BackgroundScheduler # For polling job

logger = logging.getLogger(__name__)

class CreateOrderSagaOrchestrator:
    """Orchestrates the create order saga using Kafka commands and events"""

    def __init__(self):
        """Initialize the orchestrator and register event handlers"""
        # The orchestrator keeps track of its own initialization status
        self.initialized = False
        self.init_error = None
        self.scheduler = None # Add scheduler attribute

        # Defer the actual handler registration since Kafka might not be ready yet
        # We'll lazy-initialize when needed

    def _ensure_initialized(self):
        """Ensure the orchestrator is initialized with Kafka

        Returns:
            bool: True if initialized successfully, False otherwise
        """
        if self.initialized:
            return True

        # More detailed logging for debugging
        logger.info("Attempting to initialize orchestrator with Kafka service")

        # Get the global Kafka client
        from app.services.kafka_service import kafka_client
        kafka_svc = kafka_client

        if not kafka_svc:
            self.init_error = "Kafka client not initialized"
            logger.error(self.init_error)
            return False

        # Double-check Kafka service has a producer
        logger.info(f"Kafka service found. Producer: {kafka_svc.producer is not None}")

        if not kafka_svc.producer:
            self.init_error = "Kafka producer not initialized"
            logger.error(self.init_error)
            return False

        # Register event handlers with Kafka client
        self._register_event_handlers(kafka_svc)
        self.initialized = True
        logger.info("CreateOrderSagaOrchestrator initialized successfully")
        return True

    def _register_event_handlers(self, kafka_service):
        """Register all event handlers with the Kafka service"""

        # Register event handlers for each step in the saga
        kafka_service.register_event_handler('order.created', self.handle_order_created)
        kafka_service.register_event_handler('user.payment_info_retrieved', self.handle_payment_info_retrieved)
        kafka_service.register_event_handler('payment.authorized', self.handle_payment_authorized)
        kafka_service.register_event_handler('order.status_updated', self.handle_order_status_updated)
        kafka_service.register_event_handler('timer.started', self.handle_timer_started)

        # Register failure handlers
        kafka_service.register_event_handler('order.creation_failed', self.handle_order_creation_failed)
        kafka_service.register_event_handler('user.payment_info_failed', self.handle_payment_info_failed)
        kafka_service.register_event_handler('payment.failed', self.handle_payment_failed)
        kafka_service.register_event_handler('order.status_update_failed', self.handle_order_status_update_failed)
        kafka_service.register_event_handler('timer.failed', self.handle_timer_failed)

        # Register compensation/cancellation confirmation event handlers
        kafka_service.register_event_handler('order.cancelled', self.handle_order_cancelled)
        kafka_service.register_event_handler('payment.released', self.handle_payment_released) # Use payment.released based on payment service code

    def start_saga(self, customer_id, order_details, payment_amount):
        """
        Start a new create order saga

        Args:
            customer_id: ID of the customer creating the order
            order_details: Order details (items, delivery location, etc.)
            payment_amount: Total payment amount for the order

        Returns:
            tuple: (success, message, saga_state)
        """
        # Get Kafka service first so we can log attempts
        kafka_svc = current_app.kafka_service

        # Detailed logging about initialization
        logger.info(f"Attempting to initialize orchestrator. Kafka service: {kafka_svc is not None}")
        if kafka_svc:
            logger.info(f"Kafka producer: {kafka_svc.producer is not None}, consumer: {kafka_svc.consumer is not None}")
            logger.info(f"Has publish_command: {hasattr(kafka_svc, 'publish_command')}")

        # Ensure the orchestrator is initialized before starting a saga
        if not self._ensure_initialized():
            logger.error(f"Cannot start saga: {self.init_error}")
            return False, f"Cannot start saga: {self.init_error}", None

        try:
            # Create saga state
            saga_state = CreateOrderSagaState(
                customer_id=customer_id,
                status=SagaStatus.STARTED,
                current_step=SagaStep.CREATE_ORDER,
                order_details=order_details,
                payment_amount=float(payment_amount)
            )
            db.session.add(saga_state)
            db.session.commit()

            logger.info(f"Starting create order saga {saga_state.id} for customer {customer_id}")

            # First command: Create order
            try:
                logger.info("Attempting to publish create_order command")
                success, correlation_id = publish_create_order_command(
                    kafka_svc,
                    {
                        'customer_id': customer_id,
                        'order_details': order_details,
                        'saga_id': saga_state.id
                    },
                    saga_state.id  # Use saga_id as correlation_id for tracing
                )
            except Exception as e:
                logger.error(f"Exception in publish_create_order_command: {str(e)}")
                saga_state.update_status(SagaStatus.FAILED, error=f"Error publishing command: {str(e)}")
                db.session.commit()
                return False, f"Failed to start saga: {str(e)}", saga_state

            if not success:
                logger.error(f"Failed to publish create_order command for saga {saga_state.id}")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish create_order command")
                db.session.commit()
                return False, "Failed to start saga: Kafka message publishing failed", saga_state

            return True, "Saga started successfully", saga_state

        except Exception as e:
            logger.error(f"Error starting saga: {str(e)}")
            return False, f"Error starting saga: {str(e)}", None

    def handle_order_created(self, correlation_id, payload):
        """Handle order.created event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            # Update saga state with order_id
            order_id = payload.get('order_id')
            if not order_id:
                logger.error(f"No order_id in payload for saga {correlation_id}")
                saga_state.update_status(SagaStatus.FAILED, error="No order_id in order.created event")
                db.session.commit()
                return

            saga_state.order_id = order_id
            saga_state.update_status(SagaStatus.STARTED, SagaStep.GET_USER_DATA)
            db.session.commit()

            logger.info(f"Order created for saga {correlation_id}, order_id: {order_id}")

            # Next step: Get user payment info
            kafka_svc = current_app.kafka_service
            success, _ = publish_get_user_payment_info_command(
                kafka_svc,
                saga_state.customer_id,
                correlation_id
            )

            if not success:
                logger.error(f"Failed to publish get_user_payment_info command for saga {correlation_id}")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish get_user_payment_info command")
                db.session.commit()

        except Exception as e:
            logger.error(f"Error handling order.created for correlation_id {correlation_id}: {str(e)}")

    def handle_payment_info_retrieved(self, correlation_id, payload):
        """Handle user.payment_info_retrieved event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            # Update saga state
            saga_state.update_status(SagaStatus.STARTED, SagaStep.AUTHORIZE_PAYMENT)
            db.session.commit()

            logger.info(f"User payment info retrieved for saga {correlation_id}")

            # Next step: Authorize payment
            kafka_svc = current_app.kafka_service
            # Extract payment info received from user service event
            user_payment_info = payload.get('payment_info', {})
            stripe_customer_id = user_payment_info.get('stripeCustomerId')
            payment_method_id = user_payment_info.get('paymentMethodId')

            # Construct the payload expected by the Payment Service
            # Ensure amount is in cents (integer)
            amount_cents = int(saga_state.payment_amount * 100)
            
            payment_payload = {
                'order_id': saga_state.order_id,
                'customer': {
                    'clerkUserId': saga_state.customer_id, # Use the customer_id stored in saga state
                    'stripeCustomerId': stripe_customer_id,
                    'userStripeCard': { # Nest payment method ID
                        'payment_method_id': payment_method_id
                    }
                },
                'order': {
                    'amount': amount_cents,
                    'description': f"Payment for order {saga_state.order_id}" # Optional description
                },
                # Add the return_url for 3DS flows
                'return_url': 'https://localhost:5173/customer/history'
            }

            success, _ = publish_authorize_payment_command(
                kafka_svc,
                payment_payload, # Send the correctly structured payload
                correlation_id
            )

            if not success:
                logger.error(f"Failed to publish authorize_payment command for saga {correlation_id}")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish authorize_payment command")
                db.session.commit()

        except Exception as e:
            logger.error(f"Error handling user.payment_info_retrieved for correlation_id {correlation_id}: {str(e)}")

    def handle_payment_authorized(self, correlation_id, payload):
        """Handle payment.authorized event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            # Extract payment_id from the event payload
            payment_id = payload.get('payment_id')
            if not payment_id:
                logger.error(f"No payment_id in payment.authorized payload for saga {correlation_id}")
                # Fail the saga if payment_id is missing, as it's needed for potential reverts
                saga_state.update_status(SagaStatus.FAILED, error="Missing payment_id in payment.authorized event")
                db.session.commit()
                return

            # Update saga state, storing the payment_id
            saga_state.payment_id = payment_id
            saga_state.update_status(SagaStatus.STARTED, SagaStep.UPDATE_ORDER_STATUS)
            db.session.commit()

            logger.info(f"Payment authorized for saga {correlation_id}, payment_id: {payment_id}")

            # Next step: Update order status to CREATED
            kafka_svc = current_app.kafka_service
            success, _ = publish_update_order_status_command(
                kafka_svc,
                saga_state.order_id,
                'CREATED',
                correlation_id
            )

            if not success:
                logger.error(f"Failed to publish update_order_status command for saga {correlation_id}")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish update_order_status command")
                db.session.commit()

        except Exception as e:
            logger.error(f"Error handling payment.authorized for correlation_id {correlation_id}: {str(e)}")

    def handle_order_status_updated(self, correlation_id, payload):
        """Handle order.status_updated event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            # Verify expected status
            new_status = payload.get('status')
            if new_status != 'CREATED':
                logger.warning(f"Unexpected status update in saga {correlation_id}: {new_status}")
                # Continue anyway

            # Update saga state
            saga_state.update_status(SagaStatus.STARTED, SagaStep.START_TIMER)
            db.session.commit()

            logger.info(f"Order status updated to CREATED for saga {correlation_id}")

            # Next step: Start order timeout timer via HTTP
            # Generate timeout 30 minutes from now - note: not used by current Timer API
            timeout_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat()

            # Try HTTP request to timer service
            try:
                # Use HTTP client to call timer service
                logger.info(f"Attempting to start timer via HTTP for order {saga_state.order_id}")
                success, response = http_client.start_timer(
                    saga_state.order_id,
                    saga_state.customer_id,
                    timeout_at,
                    correlation_id  # Still pass correlation_id even though current API doesn't use it
                )

                # Always mark saga as completed since the timer is non-critical
                saga_state.update_status(SagaStatus.COMPLETED)
                saga_state.completed_at = datetime.utcnow()
                db.session.commit()

                if success:
                    logger.info(f"Timer started via HTTP for order {saga_state.order_id}: {response}")
                    logger.info(f"Saga {correlation_id} completed after HTTP timer start")
                else:
                    logger.warning(f"Failed to start timer via HTTP: {response.get('error')}")
                    logger.info(f"Saga {correlation_id} completed despite timer failure")

            except Exception as e:
                # Exception during timer service call
                logger.error(f"Error starting timer for order {saga_state.order_id}: {str(e)}")
                
                # Mark saga as completed anyway since timer is non-critical
                saga_state.update_status(SagaStatus.COMPLETED)
                saga_state.completed_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Saga {correlation_id} completed despite timer error")

        except Exception as e:
            logger.error(f"Error handling order.status_updated for correlation_id {correlation_id}: {str(e)}")
            # Attempt to mark as completed even if there was an error
            try:
                saga_state.update_status(SagaStatus.COMPLETED)
                saga_state.completed_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Marked saga {correlation_id} as completed despite error in timer setup")
            except Exception as commit_error:
                logger.error(f"Failed to update saga status after error: {str(commit_error)}")

    def handle_timer_started(self, correlation_id, payload):
        """Handle timer.started event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            # Update saga state
            saga_state.update_status(SagaStatus.COMPLETED)
            saga_state.completed_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Timer started and saga completed for {correlation_id}")

        except Exception as e:
            logger.error(f"Error handling timer.started for correlation_id {correlation_id}: {str(e)}")

    def handle_order_creation_failed(self, correlation_id, payload):
        """Handle order.creation_failed event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            error_message = payload.get('error', 'Unknown error')
            saga_state.update_status(SagaStatus.FAILED, error=f"Order creation failed: {error_message}")
            db.session.commit()

            logger.error(f"Order creation failed for saga {correlation_id}: {error_message}")

        except Exception as e:
            logger.error(f"Error handling order.creation_failed for correlation_id {correlation_id}: {str(e)}")

    def handle_payment_info_failed(self, correlation_id, payload):
        """Handle user.payment_info_failed event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return

            error_message = payload.get('error', 'Unknown error')
            logger.error(f"User payment info retrieval failed for saga {correlation_id}: {error_message}")

            # --- Compensation Logic ---
            # If getting payment info fails, we need to cancel the order if it was created.
            if saga_state.order_id:
                logger.info(f"Initiating compensation for saga {correlation_id}: Cancelling order {saga_state.order_id}")
                saga_state.update_status(SagaStatus.COMPENSATING, error=f"Failed to get payment info: {error_message}")
                db.session.commit()

                kafka_svc = current_app.kafka_service
                success, _ = publish_cancel_order_command(
                    kafka_svc,
                    saga_state.order_id,
                    f"Compensation due to payment info failure: {error_message}",
                    correlation_id
                )
                if not success:
                    logger.error(f"Failed to publish cancel_order command during compensation for saga {correlation_id}")
                    # Saga remains in COMPENSATING state, requires manual intervention or retry mechanism
            else:
                # Order wasn't created yet, just fail the saga
                saga_state.update_status(SagaStatus.FAILED, error=f"Failed to get user payment info: {error_message}")
                db.session.commit()
                logger.info(f"Saga {correlation_id} failed before order creation.")

        except Exception as e:
            logger.error(f"Error handling user.payment_info_failed for correlation_id {correlation_id}: {str(e)}")

    def handle_payment_failed(self, correlation_id, payload):
        """Handle payment.failed event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            error_message = payload.get('error', 'Unknown error')
            logger.error(f"Payment authorization failed for saga {correlation_id}: {error_message}")

            # --- Compensation Logic ---
            # If payment fails, we need to cancel the order if it was created.
            if saga_state.order_id:
                logger.info(f"Initiating compensation for saga {correlation_id}: Cancelling order {saga_state.order_id} due to payment failure.")
                saga_state.update_status(SagaStatus.COMPENSATING, error=f"Payment authorization failed: {error_message}")
                db.session.commit()

                kafka_svc = current_app.kafka_service
                success, _ = publish_cancel_order_command(
                    kafka_svc,
                    saga_state.order_id,
                    f"Compensation due to payment failure: {error_message}",
                    correlation_id
                )
                if not success:
                    logger.error(f"Failed to publish cancel_order command during compensation for saga {correlation_id}")
                    # Saga remains in COMPENSATING state
            else:
                # Should not happen if order_created was successful, but handle defensively
                saga_state.update_status(SagaStatus.FAILED, error=f"Payment authorization failed: {error_message} (Order ID missing)")
                db.session.commit()
                logger.error(f"Saga {correlation_id} failed at payment step, but order_id was missing.")

        except Exception as e:
            logger.error(f"Error handling payment.failed for correlation_id {correlation_id}: {str(e)}")

    def handle_order_status_update_failed(self, correlation_id, payload):
        """Handle order.status_update_failed event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            error_message = payload.get('error', 'Unknown error')
            logger.error(f"Order status update failed for saga {correlation_id}: {error_message}")

            # --- Compensation Logic ---
            # If updating order status fails, we need to:
            # 1. Revert the payment (if authorized).
            # 2. Cancel the order (if created).
            # 3. Cancel the timer (if order created).
            if saga_state.payment_id or saga_state.order_id:
                logger.info(f"Initiating compensation for saga {correlation_id} due to order status update failure.")
                saga_state.update_status(SagaStatus.COMPENSATING, error=f"Failed to update order status: {error_message}")
                db.session.commit()

                kafka_svc = current_app.kafka_service
                revert_payment_success = True
                cancel_order_success = True
                cancel_timer_success = True

                # 1. Revert Payment
                if saga_state.payment_id:
                    logger.info(f"Publishing revert_payment command for payment {saga_state.payment_id}")
                    revert_payment_success, _ = publish_revert_payment_command(
                        kafka_svc,
                        saga_state.payment_id,
                        f"Compensation due to order status update failure: {error_message}",
                        correlation_id
                    )
                    if not revert_payment_success:
                        logger.error(f"Failed to publish revert_payment command during compensation for saga {correlation_id}")

                # 2. Cancel Order
                if saga_state.order_id:
                    logger.info(f"Publishing cancel_order command for order {saga_state.order_id}")
                    cancel_order_success, _ = publish_cancel_order_command(
                        kafka_svc,
                        saga_state.order_id,
                        f"Compensation due to order status update failure: {error_message}",
                        correlation_id
                    )
                    if not cancel_order_success:
                        logger.error(f"Failed to publish cancel_order command during compensation for saga {correlation_id}")

                    # 3. Cancel Timer (Only if order was created)
                    logger.info(f"Requesting external timer cancellation via HTTP for order {saga_state.order_id}")
                    cancel_timer_success, _ = http_client.cancel_timer(saga_state.order_id)
                    if not cancel_timer_success:
                        logger.warning(f"Failed to cancel external timer for order {saga_state.order_id} during compensation.")

                if not revert_payment_success or not cancel_order_success:
                     logger.error(f"One or more compensation commands failed to publish for saga {correlation_id}. Status remains COMPENSATING.")
                else:
                     logger.info(f"Compensation commands published successfully for saga {correlation_id}. Status remains COMPENSATING pending confirmation.")

            else:
                # Should not happen if payment was authorized or order created, but handle defensively
                saga_state.update_status(SagaStatus.FAILED, error=f"Failed to update order status: {error_message} (Payment ID and Order ID missing)")
                db.session.commit()
                logger.error(f"Saga {correlation_id} failed at order status update step, but payment/order IDs were missing.")

        except Exception as e:
            logger.error(f"Error handling order.status_update_failed for correlation_id {correlation_id}: {str(e)}")

    def handle_timer_failed(self, correlation_id, payload):
        """Handle timer.failed event"""
        try:
            # Get the saga state
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return

            error_message = payload.get('error', 'Unknown error')
            logger.warning(f"Timer start failed for saga {correlation_id}: {error_message}")

            # This is not critical for the saga completion
            # Mark saga as completed anyway
            saga_state.update_status(SagaStatus.COMPLETED)
            saga_state.completed_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Saga {correlation_id} completed despite timer failure")

        except Exception as e:
            logger.error(f"Error handling timer.failed for correlation_id {correlation_id}: {str(e)}")


    # --- Compensation/Cancellation Confirmation Handlers ---

    def handle_order_cancelled(self, correlation_id, payload):
        """Handle the confirmation that an order was successfully cancelled."""
        try:
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id} in handle_order_cancelled")
                return

            if saga_state.status not in [SagaStatus.COMPENSATING, SagaStatus.CANCELLING]:
                logger.warning(f"Received order.cancelled for saga {correlation_id} in unexpected state {saga_state.status.name}. Ignoring.")
                return

            logger.info(f"Received order.cancelled confirmation for saga {correlation_id}")
            saga_state.order_cancelled_confirmed = True
            self._check_and_complete_compensation_or_cancellation(saga_state)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error handling order.cancelled for correlation_id {correlation_id}: {str(e)}", exc_info=True)
            db.session.rollback() # Rollback on error

    def handle_payment_released(self, correlation_id, payload):
        """Handle the confirmation that a payment was successfully reverted/released."""
        try:
            saga_state = CreateOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id} in handle_payment_released")
                return

            if saga_state.status not in [SagaStatus.COMPENSATING, SagaStatus.CANCELLING]:
                logger.warning(f"Received payment.released for saga {correlation_id} in unexpected state {saga_state.status.name}. Ignoring.")
                return

            # Check if the status in the payload indicates a successful revert
            # Payment service sends 'REVERTED' string in the 'status' field on success
            if payload.get('status') == 'REVERTED':
                logger.info(f"Received payment.released (reverted) confirmation for saga {correlation_id}")
                saga_state.payment_reverted_confirmed = True
                self._check_and_complete_compensation_or_cancellation(saga_state)
                db.session.commit()
            else:
                 logger.warning(f"Received payment.released for saga {correlation_id}, but status was '{payload.get('status')}' not '{PaymentStatus.REVERTED.value}'. Not marking as reverted.")


        except Exception as e:
            logger.error(f"Error handling payment.released for correlation_id {correlation_id}: {str(e)}", exc_info=True)
            db.session.rollback() # Rollback on error


    def _check_and_complete_compensation_or_cancellation(self, saga_state):
        """
        Checks if all necessary compensating or cancellation actions are confirmed
        and updates the saga status to COMPENSATED or CANCELLED if complete.
        """
        if saga_state.status == SagaStatus.COMPENSATING:
            # Determine which actions were required based on the failure step
            # This logic assumes compensation was triggered by one of the failure handlers above.
            # We need to know *which* failure triggered compensation.
            # Let's check which compensating commands would have been sent based on existing IDs.

            order_cancellation_needed = False
            payment_revert_needed = False

            # Determine which actions were required based on the failure step that triggered compensation.
            order_cancellation_needed = False
            payment_revert_needed = False

            # If payment info failed or payment failed, order cancellation was attempted (if order existed)
            if saga_state.current_step == SagaStep.GET_USER_DATA or saga_state.current_step == SagaStep.AUTHORIZE_PAYMENT:
                if saga_state.order_id:
                    order_cancellation_needed = True

            # If order status update failed, both payment revert and order cancel were attempted (if they existed)
            elif saga_state.current_step == SagaStep.UPDATE_ORDER_STATUS:
                if saga_state.payment_id:
                    payment_revert_needed = True
                if saga_state.order_id:
                    order_cancellation_needed = True # Now also need order cancellation confirmation

            # Check if all *needed* actions for this specific compensation scenario are confirmed
            compensation_complete = True
            if order_cancellation_needed and not saga_state.order_cancelled_confirmed:
                compensation_complete = False
            if payment_revert_needed and not saga_state.payment_reverted_confirmed:
                compensation_complete = False

            if compensation_complete:
                logger.info(f"All required compensating actions confirmed for saga {saga_state.id}. Updating status to COMPENSATED.")
                saga_state.update_status(SagaStatus.COMPENSATED)
            else:
                 logger.info(f"Saga {saga_state.id} still compensating. Order Cancelled Confirmed: {saga_state.order_cancelled_confirmed} (Needed: {order_cancellation_needed}), Payment Reverted Confirmed: {saga_state.payment_reverted_confirmed} (Needed: {payment_revert_needed})")


        elif saga_state.status == SagaStatus.CANCELLING:
            # For cancellation, both order cancel and payment revert are attempted if applicable
            order_cancellation_needed = saga_state.order_id is not None
            payment_revert_needed = saga_state.payment_id is not None

            cancellation_complete = True
            if order_cancellation_needed and not saga_state.order_cancelled_confirmed:
                cancellation_complete = False
            if payment_revert_needed and not saga_state.payment_reverted_confirmed:
                cancellation_complete = False

            if cancellation_complete:
                logger.info(f"All required cancellation actions confirmed for saga {saga_state.id}. Updating status to CANCELLED.")
                saga_state.update_status(SagaStatus.CANCELLED)
            else:
                 logger.info(f"Saga {saga_state.id} still cancelling. Order Cancelled Confirmed: {saga_state.order_cancelled_confirmed} (Needed: {order_cancellation_needed}), Payment Reverted Confirmed: {saga_state.payment_reverted_confirmed} (Needed: {payment_revert_needed})")


    # --- Cancellation Initiation ---

    def _initiate_cancellation(self, saga_state, reason="Cancellation requested"):
        """
        Initiates the cancellation process for a given saga state.
        Updates status, calls external timer cancellation, and publishes compensation commands.
        """
        correlation_id = saga_state.id
        logger.info(f"Initiating cancellation for saga {correlation_id}. Reason: {reason}")

        # Check if already cancelling or in a non-cancellable final state.
        # Allow initiating cancellation even if COMPLETED, as the underlying order might still be cancellable.
        non_cancellable_states = [SagaStatus.CANCELLING, SagaStatus.CANCELLED, SagaStatus.FAILED, SagaStatus.COMPENSATED]
        if saga_state.status in non_cancellable_states:
            logger.warning(f"Saga {correlation_id} is already in state {saga_state.status.name}, cannot initiate cancellation.")
            return False # Indicate cancellation cannot be initiated

        # Update status to CANCELLING
        saga_state.update_status(SagaStatus.CANCELLING, error=reason)
        db.session.commit()

        # Get Kafka service
        kafka_svc = current_app.kafka_service
        if not kafka_svc:
             logger.error(f"Kafka service not available during cancellation for saga {correlation_id}")
             # Saga remains in CANCELLING state, needs attention
             return False

        # 1. Cancel external timer (OutSystems)
        if saga_state.order_id: # Timer is linked to order_id
            logger.info(f"Requesting external timer cancellation via HTTP for order {saga_state.order_id}")
            timer_cancel_success, _ = http_client.cancel_timer(saga_state.order_id)
            if not timer_cancel_success:
                # Log warning but continue with other cancellations
                logger.warning(f"Failed to cancel external timer for order {saga_state.order_id}. Continuing cancellation process.")
        else:
             logger.warning(f"Cannot cancel external timer for saga {correlation_id} as order_id is missing.")


        # 2. Cancel Order (if created)
        cancel_order_success = True # Assume success if no order_id
        if saga_state.order_id:
            logger.info(f"Publishing cancel_order command for order {saga_state.order_id}")
            cancel_order_success, _ = publish_cancel_order_command(
                kafka_svc,
                saga_state.order_id,
                reason,
                correlation_id
            )
            if not cancel_order_success:
                logger.error(f"Failed to publish cancel_order command for saga {correlation_id}")
                # Saga remains in CANCELLING state

        # 3. Revert Payment (if authorized)
        revert_payment_success = True # Assume success if no payment_id
        if saga_state.payment_id:
            logger.info(f"Publishing revert_payment command for payment {saga_state.payment_id}")
            revert_payment_success, _ = publish_revert_payment_command(
                kafka_svc,
                saga_state.payment_id,
                reason, # Use the same reason for Stripe
                correlation_id
            )
            if not revert_payment_success:
                logger.error(f"Failed to publish revert_payment command for saga {correlation_id}")
                # Saga remains in CANCELLING state

        # If all commands published successfully, we can potentially move to CANCELLED.
        # However, it's safer to wait for confirmation events (order.cancelled, payment.reverted)
        # For now, leave it in CANCELLING. We'll add event handlers later if needed.
        if cancel_order_success and revert_payment_success:
             logger.info(f"Cancellation commands published successfully for saga {correlation_id}. Status remains CANCELLING pending confirmation.")
             return True
        else:
             logger.error(f"One or more cancellation commands failed to publish for saga {correlation_id}. Status remains CANCELLING.")
             return False

    def _poll_for_cancellations(self, app):
        """
        Scheduled job function to poll the external timer service for expired timers
        and initiate cancellation for the corresponding sagas.

        Args:
            app: The Flask application instance.
        """
        # Ensure this runs within the Flask app context to access db, config, etc.
        # Use the passed 'app' object to create the context
        with app.app_context():
            logger.info("Polling for expired timers...")
            # Access http_client and db through the app context or ensure they are available
            # Note: http_client is likely global, db needs context.
            try:
                success, timers_data = http_client.get_timers_for_cancellation()

                if not success:
                    logger.error(f"Failed to poll timer service: {timers_data.get('error', 'Unknown error')}")
                    return

                if not timers_data:
                    logger.debug("No timers found for cancellation check.")
                    return

                expired_count = 0
                for timer_info in timers_data:
                    # Check the status field from the API response
                    if timer_info.get("Status") == "Expired":
                        saga_id = timer_info.get("SagaId")
                        order_id = timer_info.get("OrderId")
                        timer_id = timer_info.get("TimerId") # Use TimerId for logging

                        if not saga_id and not order_id:
                            logger.warning(f"Expired timer {timer_id} found, but missing SagaId and OrderId. Cannot link to saga.")
                            continue

                        # Find the saga state
                        saga_state = None
                        if saga_id:
                            saga_state = CreateOrderSagaState.query.get(saga_id)
                        elif order_id:
                            # Fallback to finding by order_id if SagaId is missing
                            saga_state = CreateOrderSagaState.query.filter_by(order_id=order_id).first()

                        if not saga_state:
                            logger.warning(f"Expired timer {timer_id} found (SagaId: {saga_id}, OrderId: {order_id}), but corresponding saga state not found.")
                            continue

                        # Check if saga is in a state where auto-cancellation makes sense
                        if saga_state.status == SagaStatus.STARTED:
                            logger.info(f"Expired timer {timer_id} detected for active saga {saga_state.id}. Initiating cancellation.")
                            self._initiate_cancellation(saga_state, reason="Order timed out (30 minutes)")
                            expired_count += 1
                        else:
                            logger.debug(f"Expired timer {timer_id} found for saga {saga_state.id}, but saga status is {saga_state.status.name}. Skipping auto-cancellation.")

                if expired_count > 0:
                     logger.info(f"Finished polling. Initiated cancellation for {expired_count} expired timers.")
                else:
                     logger.info("Finished polling. No active sagas found with expired timers.")

            except Exception as e:
                logger.error(f"Error during timer polling: {str(e)}", exc_info=True)

    def start_scheduler(self, app, interval_seconds=60):
        """
        Starts the background scheduler for polling tasks.

        Args:
            app: The Flask application instance.
            interval_seconds (int): Polling interval.
        """
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler already running.")
            return

        self.scheduler = BackgroundScheduler(daemon=True)
        self.scheduler.add_job(
            self._poll_for_cancellations,
            'interval',
            seconds=interval_seconds,
            id='timer_cancellation_poll',
            replace_existing=True,
            args=[app] # Pass the app instance received as an argument
        )
        try:
            self.scheduler.start()
            logger.info(f"Started background scheduler to poll for cancellations every {interval_seconds} seconds.")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
            self.scheduler = None # Ensure scheduler is None if start fails

    def stop_scheduler(self):
        """Stops the background scheduler."""
        if self.scheduler and self.scheduler.running:
            try:
                self.scheduler.shutdown()
                logger.info("Background scheduler shut down.")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {str(e)}", exc_info=True)
        self.scheduler = None


def init_orchestrator():
    """Initialize the saga orchestrator

    Returns:
        CreateOrderSagaOrchestrator or None: The initialized orchestrator instance, or None if initialization failed
    """
    try:
        orchestrator_instance = CreateOrderSagaOrchestrator()
        # The _ensure_initialized method will be called lazily when needed
        logger.info("CreateOrderSagaOrchestrator instance created (lazy initialization)")
        return orchestrator_instance
    except Exception as e:
        logger.error(f"Error creating CreateOrderSagaOrchestrator instance: {str(e)}")
        return None

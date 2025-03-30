import logging
from datetime import datetime, timedelta
from app import db
from app.models.saga_state import CreateOrderSagaState, SagaStatus, SagaStep
from flask import current_app
from app.services.kafka_service import (
    publish_create_order_command,
    publish_get_user_payment_info_command,
    publish_authorize_payment_command,
    publish_update_order_status_command,
    publish_start_timer_command
)

logger = logging.getLogger(__name__)

class CreateOrderSagaOrchestrator:
    """Orchestrates the create order saga using Kafka commands and events"""
    
    def __init__(self):
        """Initialize the orchestrator and register event handlers"""
        # The orchestrator keeps track of its own initialization status
        self.initialized = False
        self.init_error = None
        
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
            user_payment_info = payload.get('payment_info', {})
            
            success, _ = publish_authorize_payment_command(
                kafka_svc,
                {
                    'order_id': saga_state.order_id,
                    'customer_id': saga_state.customer_id,
                    'amount': saga_state.payment_amount,
                    'payment_info': user_payment_info
                },
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
            
            # Update saga state
            saga_state.update_status(SagaStatus.STARTED, SagaStep.UPDATE_ORDER_STATUS)
            db.session.commit()
            
            logger.info(f"Payment authorized for saga {correlation_id}")
            
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
            
            # Next step: Start order timeout timer
            kafka_svc = current_app.kafka_service
            timeout_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
            
            success, _ = publish_start_timer_command(
                kafka_svc,
                {
                    'order_id': saga_state.order_id,
                    'customer_id': saga_state.customer_id,
                    'timeout_at': timeout_at
                },
                correlation_id
            )
            
            if not success:
                logger.error(f"Failed to publish start_timer command for saga {correlation_id}")
                # Not critical for the success of the saga
                logger.warning("Continuing without timer")
                
                # Mark saga as completed
                saga_state.update_status(SagaStatus.COMPLETED)
                saga_state.completed_at = datetime.utcnow()
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error handling order.status_updated for correlation_id {correlation_id}: {str(e)}")
    
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
            saga_state.update_status(SagaStatus.FAILED, error=f"Failed to get user payment info: {error_message}")
            db.session.commit()
            
            logger.error(f"User payment info retrieval failed for saga {correlation_id}: {error_message}")
            
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
            saga_state.update_status(SagaStatus.FAILED, error=f"Payment authorization failed: {error_message}")
            db.session.commit()
            
            logger.error(f"Payment failed for saga {correlation_id}: {error_message}")
            
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
            saga_state.update_status(SagaStatus.FAILED, error=f"Failed to update order status: {error_message}")
            db.session.commit()
            
            logger.error(f"Order status update failed for saga {correlation_id}: {error_message}")
            
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

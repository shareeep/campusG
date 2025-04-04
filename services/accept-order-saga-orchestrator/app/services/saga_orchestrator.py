import logging
from datetime import datetime
from app import db
from flask import current_app
from app.models.saga_state import AcceptOrderSagaState, SagaStatus, SagaStep
from app.services.kafka_service import (
    publish_accept_order_command,
    publish_compensate_accept_order_command  # In case you add compensation later
)

logger = logging.getLogger(__name__)

class AcceptOrderSagaOrchestrator:
    """Orchestrates the accept order saga using Kafka commands and events."""
    
    def __init__(self):
        # Tracks whether initialization has been performed
        self.initialized = False
        self.init_error = None

    def _ensure_initialized(self):
        """Ensure the orchestrator is properly initialized with the Kafka service.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        if self.initialized:
            return True
        
        logger.info("Initializing AcceptOrderSagaOrchestrator with Kafka service...")
        from app.services.kafka_service import kafka_client  # Global Kafka client instance
        kafka_svc = kafka_client
        if not kafka_svc:
            self.init_error = "Kafka client not initialized"
            logger.error(self.init_error)
            return False
        if not kafka_svc.producer:
            self.init_error = "Kafka producer not initialized"
            logger.error(self.init_error)
            return False
        
        self._register_event_handlers(kafka_svc)
        self.initialized = True
        logger.info("AcceptOrderSagaOrchestrator initialized successfully")
        return True

    def _register_event_handlers(self, kafka_service):
        """Register all event handlers with the Kafka service."""
        kafka_service.register_event_handler('order.accepted', self.handle_order_accepted)
        kafka_service.register_event_handler('order.acceptance_failed', self.handle_order_acceptance_failed)
        # You can register additional failure handlers if needed

    def start_saga(self, order_id, runner_id):
        """
        Start a new accept order saga.
        
        Args:
            order_id (str): The ID of the order to accept.
            runner_id (str): The ID of the runner accepting the order.
            
        Returns:
            tuple: (success: bool, message: str, saga_state: AcceptOrderSagaState or None)
        """
        # Get Kafka service instance from the Flask app for logging/tracing
        kafka_svc = current_app.kafka_service
        
        logger.info(f"Starting Accept Order Saga. Kafka service available: {kafka_svc is not None}")
        
        if not self._ensure_initialized():
            logger.error(f"Cannot start saga: {self.init_error}")
            return False, f"Cannot start saga: {self.init_error}", None
        
        try:
            # Create a new saga state instance to track the accept order saga.
            saga_state = AcceptOrderSagaState(
                order_id=order_id,
                runner_id=runner_id,
                status=SagaStatus.STARTED,
                current_step=SagaStep.ACCEPT_ORDER
            )
            db.session.add(saga_state)
            db.session.commit()
            
            logger.info(f"Accept Order Saga {saga_state.id} started for order {order_id}")
            
            # Publish the accept order command via Kafka.
            success, correlation_id = publish_accept_order_command(
                kafka_svc,
                {
                    'orderId': order_id,
                    'runner_id': runner_id,
                    'saga_id': saga_state.id
                },
                saga_state.id  # Use the saga state ID as the correlation_id
            )
            
            if not success:
                logger.error(f"Failed to publish accept order command for saga {saga_state.id}")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish accept order command")
                db.session.commit()
                return False, "Failed to start saga: Kafka message publishing failed", saga_state
            
            return True, "Accept order saga started successfully", saga_state
            
        except Exception as e:
            logger.error(f"Error starting accept order saga: {str(e)}")
            return False, f"Error starting saga: {str(e)}", None

    def handle_order_accepted(self, correlation_id, payload):
        """Handle the event when the order is accepted successfully."""
        try:
            saga_state = AcceptOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            
            # Update saga state to completed.
            saga_state.update_status(SagaStatus.COMPLETED)
            saga_state.completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Accept Order Saga {correlation_id} completed successfully for order {saga_state.order_id}")
            
        except Exception as e:
            logger.error(f"Error handling order.accepted for correlation_id {correlation_id}: {str(e)}")

    def handle_order_acceptance_failed(self, correlation_id, payload):
        """Handle the event when order acceptance fails."""
        try:
            saga_state = AcceptOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            
            error_message = payload.get('error', 'Unknown error')
            saga_state.update_status(SagaStatus.FAILED, error=f"Order acceptance failed: {error_message}")
            db.session.commit()
            
            logger.error(f"Order acceptance failed for saga {correlation_id}: {error_message}")
        except Exception as e:
            logger.error(f"Error handling order.acceptance_failed for correlation_id {correlation_id}: {str(e)}")

def init_accept_order_orchestrator():
    """Initialize the Accept Order Saga orchestrator.
    
    Returns:
        AcceptOrderSagaOrchestrator or None: The orchestrator instance, or None if initialization failed.
    """
    try:
        orchestrator_instance = AcceptOrderSagaOrchestrator()
        logger.info("AcceptOrderSagaOrchestrator instance created (lazy initialization)")
        return orchestrator_instance
    except Exception as e:
        logger.error(f"Error creating AcceptOrderSagaOrchestrator instance: {str(e)}")
        return None

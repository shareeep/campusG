import logging
from datetime import datetime, timedelta
from app import db
from flask import current_app
from app.models.saga_state import CompleteOrderSagaState, SagaStatus, SagaStep
from app.config.kafka_config import (
    COMPLETE_ORDER_COMMANDS_TOPIC,
    COMPLETE_ORDER_EVENTS_TOPIC
)
from app.services.complete_order_commands import (
    publish_update_order_status_command,
    publish_runner_payment_info_command,
    publish_release_funds_command
)

logger = logging.getLogger(__name__)

class CompleteOrderSagaOrchestrator:
    """Orchestrates the complete order saga using Kafka commands and events."""
    
    def __init__(self):
        self.initialized = False
        self.init_error = None

    def _ensure_initialized(self):
        """Ensure the orchestrator is properly initialized with the Kafka service."""
        if self.initialized:
            return True
        
        logger.info("Initializing CompleteOrderSagaOrchestrator with Kafka service...")
        from app.services.kafka_service import kafka_client  # Global Kafka client
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
        logger.info("CompleteOrderSagaOrchestrator initialized successfully")
        return True

    def _register_event_handlers(self, kafka_service):
        """Register event handlers for complete order saga events."""
        kafka_service.register_event_handler('order.status_updated_to_delivered', self.handle_order_delivered)
        kafka_service.register_event_handler('runner.payment_info_retrieved', self.handle_runner_payment_info)
        kafka_service.register_event_handler('funds_released', self.handle_funds_released)
        kafka_service.register_event_handler('order.status_updated_to_completed', self.handle_order_completed)
        kafka_service.register_event_handler('complete_order_failed', self.handle_complete_order_failed)

    def start_saga(self, order_id):
        """
        Start a new complete order saga.
        
        Args:
            order_id (str): The ID of the order to complete.
            
        Returns:
            tuple: (success, message, saga_state)
        """
        from app.services.kafka_service import kafka_client
        kafka_svc = kafka_client
        
        if not self._ensure_initialized():
            logger.error(f"Cannot start saga: {self.init_error}")
            return False, f"Cannot start saga: {self.init_error}", None
        
        try:
            # Create a new saga state instance.
            saga_state = CompleteOrderSagaState(
                order_id=order_id,
                status=SagaStatus.STARTED,
                current_step=SagaStep.COMPLETE_ORDER
            )
            db.session.add(saga_state)
            db.session.commit()
            logger.info(f"Complete Order Saga {saga_state.id} started for order {order_id}")
            
            # Step 1: Publish a command to update the order status to DELIVERED.
            success, correlation_id = publish_update_order_status_command(
                kafka_svc,
                order_id,
                'DELIVERED',
                saga_state.id
            )
            if not success:
                logger.error("Failed to publish update_order_status command for DELIVERED")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish update_order_status command for DELIVERED")
                db.session.commit()
                return False, "Failed to start saga", saga_state
            
            return True, "Complete order saga started successfully", saga_state
            
        except Exception as e:
            logger.error(f"Error starting complete order saga: {str(e)}", exc_info=True)
            return False, f"Error starting saga: {str(e)}", None

    def handle_order_delivered(self, correlation_id, payload):
        """Handle event: order status updated to DELIVERED."""
        try:
            saga_state = CompleteOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            logger.info(f"Order marked as DELIVERED for saga {correlation_id}")
            # Update state if needed, then trigger next step: get runner payment info.
            from app.services.kafka_service import kafka_client
            kafka_svc = kafka_client
            success, _ = publish_runner_payment_info_command(
                kafka_svc,
                saga_state.order_id,
                correlation_id
            )
            if not success:
                logger.error("Failed to publish runner payment info command")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish runner payment info command")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error handling order.delivered event: {str(e)}", exc_info=True)

    def handle_runner_payment_info(self, correlation_id, payload):
        """Handle event: runner payment info retrieved."""
        try:
            saga_state = CompleteOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            logger.info(f"Runner payment info retrieved for saga {correlation_id}")
            
            # Step 3: Publish command to release funds via Payment Service.
            from app.services.kafka_service import kafka_client
            kafka_svc = kafka_client
            success, _ = publish_release_funds_command(
                kafka_svc,
                {
                    'orderId': saga_state.order_id,
                    'runnerPaymentInfo': payload.get('payment_info')
                },
                correlation_id
            )
            if not success:
                logger.error("Failed to publish release funds command")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish release funds command")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error handling runner.payment_info_retrieved event: {str(e)}", exc_info=True)

    def handle_funds_released(self, correlation_id, payload):
        """Handle event: funds released."""
        try:
            saga_state = CompleteOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            logger.info(f"Funds released for saga {correlation_id}")
            
            # Step 4: Publish command to update order status to COMPLETED.
            from app.services.kafka_service import kafka_client
            kafka_svc = kafka_client
            success, _ = publish_update_order_status_command(
                kafka_svc,
                saga_state.order_id,
                'COMPLETED',
                correlation_id
            )
            if not success:
                logger.error("Failed to publish update_order_status command for COMPLETED")
                saga_state.update_status(SagaStatus.FAILED, error="Failed to publish update_order_status command for COMPLETED")
                db.session.commit()
        except Exception as e:
            logger.error(f"Error handling funds_released event: {str(e)}", exc_info=True)

    def handle_order_completed(self, correlation_id, payload):
        """Handle event: order status updated to COMPLETED."""
        try:
            saga_state = CompleteOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            saga_state.update_status(SagaStatus.COMPLETED)
            saga_state.completed_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Complete Order Saga {correlation_id} completed successfully for order {saga_state.order_id}")
        except Exception as e:
            logger.error(f"Error handling order.completed event for correlation_id {correlation_id}: {str(e)}", exc_info=True)

    def handle_complete_order_failed(self, correlation_id, payload):
        """Handle event: complete order saga failure."""
        try:
            saga_state = CompleteOrderSagaState.query.get(correlation_id)
            if not saga_state:
                logger.error(f"Saga state not found for correlation_id {correlation_id}")
                return
            error_message = payload.get('error', 'Unknown error')
            saga_state.update_status(SagaStatus.FAILED, error=f"Complete order failed: {error_message}")
            db.session.commit()
            logger.error(f"Complete order saga {correlation_id} failed: {error_message}")
        except Exception as e:
            logger.error(f"Error handling complete order failure for correlation_id {correlation_id}: {str(e)}", exc_info=True)

def init_complete_order_orchestrator():
    """Initialize the Complete Order Saga orchestrator.
    
    Returns:
        CompleteOrderSagaOrchestrator or None: The orchestrator instance, or None if initialization failed.
    """
    try:
        orchestrator_instance = CompleteOrderSagaOrchestrator()
        logger.info("CompleteOrderSagaOrchestrator instance created (lazy initialization)")
        return orchestrator_instance
    except Exception as e:
        logger.error(f"Error creating CompleteOrderSagaOrchestrator instance: {str(e)}")
        return None
def _register_event_handlers(self, kafka_service):
    """Register event handlers for complete order saga events."""
    kafka_service.register_event_handler('order.status_updated_to_delivered', self.handle_order_delivered)
    kafka_service.register_event_handler('runner.payment_info_retrieved', self.handle_runner_payment_info)
    kafka_service.register_event_handler('funds_released', self.handle_funds_released)
    kafka_service.register_event_handler('order.status_updated_to_completed', self.handle_order_completed)
    kafka_service.register_event_handler('complete_order_failed', self.handle_complete_order_failed)

def handle_order_delivered(self, correlation_id, payload):
    """Handler for when the order status has been updated to DELIVERED."""
    try:
        saga_state = CompleteOrderSagaState.query.get(correlation_id)
        if not saga_state:
            current_app.logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return
        current_app.logger.info(f"Order {saga_state.order_id} marked as DELIVERED for saga {correlation_id}")
        
        # Trigger the next step: retrieve runner payment info.
        from app.services.kafka_service import kafka_client
        success, _ = publish_runner_payment_info_command(
            kafka_client,
            saga_state.order_id,
            correlation_id
        )
        if not success:
            current_app.logger.error("Failed to publish runner payment info command")
            saga_state.update_status(SagaStatus.FAILED, error="Failed to publish runner payment info command")
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error handling order_delivered event: {str(e)}", exc_info=True)

def handle_runner_payment_info(self, correlation_id, payload):
    """Handler for when runner payment info is retrieved."""
    try:
        saga_state = CompleteOrderSagaState.query.get(correlation_id)
        if not saga_state:
            current_app.logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return
        current_app.logger.info(f"Runner payment info retrieved for saga {correlation_id}")
        
        # Trigger the next step: release funds.
        from app.services.kafka_service import kafka_client
        success, _ = publish_release_funds_command(
            kafka_client,
            saga_state.order_id,
            payload.get('payment_info'),
            correlation_id
        )
        if not success:
            current_app.logger.error("Failed to publish release funds command")
            saga_state.update_status(SagaStatus.FAILED, error="Failed to publish release funds command")
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error handling runner_payment_info event: {str(e)}", exc_info=True)

def handle_funds_released(self, correlation_id, payload):
    """Handler for when funds have been released."""
    try:
        saga_state = CompleteOrderSagaState.query.get(correlation_id)
        if not saga_state:
            current_app.logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return
        current_app.logger.info(f"Funds released for saga {correlation_id}")
        
        # Trigger the final step: update order status to COMPLETED.
        from app.services.kafka_service import kafka_client
        success, _ = publish_update_order_status_command(
            kafka_client,
            saga_state.order_id,
            'COMPLETED',
            correlation_id
        )
        if not success:
            current_app.logger.error("Failed to publish update_order_status command for COMPLETED")
            saga_state.update_status(SagaStatus.FAILED, error="Failed to publish update_order_status command for COMPLETED")
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error handling funds_released event: {str(e)}", exc_info=True)

def handle_order_completed(self, correlation_id, payload):
    """Handler for when the order status has been updated to COMPLETED."""
    try:
        saga_state = CompleteOrderSagaState.query.get(correlation_id)
        if not saga_state:
            current_app.logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return
        saga_state.update_status(SagaStatus.COMPLETED)
        saga_state.completed_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(f"Complete Order Saga {correlation_id} completed for order {saga_state.order_id}")
    except Exception as e:
        current_app.logger.error(f"Error handling order_completed event for correlation_id {correlation_id}: {str(e)}", exc_info=True)

def handle_complete_order_failed(self, correlation_id, payload):
    """Handler for a failure in the complete order saga."""
    try:
        saga_state = CompleteOrderSagaState.query.get(correlation_id)
        if not saga_state:
            current_app.logger.error(f"Saga state not found for correlation_id {correlation_id}")
            return
        error_message = payload.get('error', 'Unknown error')
        saga_state.update_status(SagaStatus.FAILED, error=f"Complete order failed: {error_message}")
        db.session.commit()
        current_app.logger.error(f"Complete order saga {correlation_id} failed: {error_message}")
    except Exception as e:
        current_app.logger.error(f"Error handling complete_order_failed event for correlation_id {correlation_id}: {str(e)}", exc_info=True)

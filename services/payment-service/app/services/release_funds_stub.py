import logging
from app import db
from app.models.models import Payment, PaymentStatus
from app.services.kafka_service import kafka_client

logger = logging.getLogger(__name__)

def handle_release_funds_command(correlation_id, payload):
    """
    Temporary stub handler for the release_funds command.
    Always responds with a successful funds_released event.
    
    Args:
        correlation_id (str): The correlation ID of the saga
        payload (dict): The command payload containing order_id and runnerPaymentInfo
    """
    logger.info(f"STUB: Processing release_funds command with correlation_id {correlation_id}")
    
    # Extract order_id from payload
    order_id = payload.get('order_id')
    if not order_id:
        logger.error(f"Missing order_id in release_funds payload: {payload}")
        return kafka_client.publish_event(
            'payment.release_failed',
            {"error": "Missing order_id", "order_id": None},
            correlation_id
        )
    
    # Log runner payment info
    runner_payment_info = payload.get('runnerPaymentInfo')
    logger.info(f"STUB: Would process payment info for runner: {runner_payment_info}")
    
    # Update payment status in the database if the payment exists
    try:
        payment = Payment.query.filter_by(order_id=order_id).first()
        if payment:
            payment.status = PaymentStatus.RELEASED
            payment.updated_at = db.func.now()
            db.session.commit()
            logger.info(f"STUB: Updated payment status to RELEASED for order {order_id}")
        else:
            logger.warning(f"STUB: Payment not found for order {order_id}, but proceeding with success event")
    except Exception as e:
        logger.error(f"STUB: Error updating payment status: {str(e)}", exc_info=True)
        # Continue to send success event despite DB error
    
    # Always send a successful funds_released event
    success = kafka_client.publish_event(
        'funds_released', 
        {"order_id": order_id, "status": "SUCCESS"}, 
        correlation_id
    )
    
    if success:
        logger.info(f"STUB: Successfully published funds_released event for order {order_id}")
    else:
        logger.error(f"STUB: Failed to publish funds_released event for order {order_id}")
    
    return success

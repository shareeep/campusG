import uuid
from datetime import datetime
from app.config.kafka_config import (
    COMPLETE_ORDER_COMMANDS_TOPIC
)

def publish_update_order_status_command(kafka_service, order_id, status, correlation_id=None):
    """
    Publish a command to update the order status.
    
    Args:
        kafka_service: The Kafka client instance.
        order_id (str): The ID of the order.
        status (str): The new status (e.g., 'DELIVERED' or 'COMPLETED').
        correlation_id (str, optional): An identifier to correlate this command with a saga state.
    
    Returns:
        tuple: (success: bool, correlation_id: str)
    """
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    payload = {
        'order_id': order_id,
        'status': status
    }
    
    # Publish the command to the complete order commands topic.
    return kafka_service.publish_command(COMPLETE_ORDER_COMMANDS_TOPIC, 'update_order_status', payload, correlation_id)


def publish_runner_payment_info_command(kafka_service, order_id, correlation_id=None):
    """
    Publish a command to retrieve the runner's payment information.
    
    Args:
        kafka_service: The Kafka client instance.
        order_id (str): The ID of the order.
        correlation_id (str, optional): An identifier to correlate this command with a saga state.
        
    Returns:
        tuple: (success: bool, correlation_id: str)
    """
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    payload = {
        'order_id': order_id
    }
    
    return kafka_service.publish_command(COMPLETE_ORDER_COMMANDS_TOPIC, 'get_runner_payment_info', payload, correlation_id)


def publish_release_funds_command(kafka_service, order_id, runner_payment_info, correlation_id=None):
    """
    Publish a command to release funds via the Payment Service.
    
    Args:
        kafka_service: The Kafka client instance.
        order_id (str): The ID of the order.
        runner_payment_info (dict): Payment info needed to release funds.
        correlation_id (str, optional): An identifier to correlate this command with a saga state.
    
    Returns:
        tuple: (success: bool, correlation_id: str)
    """
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    payload = {
        'order_id': order_id,
        'runnerPaymentInfo': runner_payment_info
    }
    
    return kafka_service.publish_command(COMPLETE_ORDER_COMMANDS_TOPIC, 'release_funds', payload, correlation_id)

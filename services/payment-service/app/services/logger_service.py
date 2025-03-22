import json
from datetime import datetime
import uuid
from flask import current_app, request, g
from app.services.kafka_service import kafka_client

class KafkaLogger:
    """Centralized logging service that sends logs to Kafka"""
    
    def __init__(self, service_name="payment-service"):
        self.service_name = service_name
    
    def debug(self, message, data=None):
        """Log a debug message"""
        return self._log("DEBUG", message, data)
    
    def info(self, message, data=None):
        """Log an info message"""
        return self._log("INFO", message, data)
    
    def warning(self, message, data=None):
        """Log a warning message"""
        return self._log("WARNING", message, data)
    
    def error(self, message, data=None):
        """Log an error message"""
        return self._log("ERROR", message, data)
    
    def critical(self, message, data=None):
        """Log a critical message"""
        return self._log("CRITICAL", message, data)
    
    def _log(self, level, message, data=None):
        """
        Internal method to log a message
        
        Args:
            level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message (str): Log message
            data (dict, optional): Additional data to include in the log
            
        Returns:
            dict: The log entry that was created
        """
        try:
            # Get trace ID from request context or generate a new one
            trace_id = None
            request_id = None
            
            if request:
                trace_id = request.headers.get('X-Trace-ID')
            
            if hasattr(g, 'trace_id'):
                trace_id = g.trace_id
                
            if hasattr(g, 'request_id'):
                request_id = g.request_id
                
            if not trace_id:
                trace_id = str(uuid.uuid4())
            
            # Build log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "level": level,
                "message": message,
                "traceId": trace_id,
                "requestId": request_id,
                "data": data or {}
            }
            
            # Also log to standard logger for local debugging
            log_method = getattr(current_app.logger, level.lower(), current_app.logger.info)
            log_method(f"[{trace_id}] {message}")
            
            # Publish to Kafka log topic
            kafka_client.publish('system-logs', log_entry)
            
            return log_entry
            
        except Exception as e:
            # Fallback to standard logging if Kafka logging fails
            current_app.logger.error(f"Failed to send log to Kafka: {str(e)}")
            current_app.logger.log(
                getattr(current_app.logger, level.lower(), current_app.logger.info),
                message
            )
            return None

# Global logger instance
logger = KafkaLogger()

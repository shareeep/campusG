import uuid
from flask import request, g, current_app

class TracingMiddleware:
    """Middleware for adding trace IDs to requests for distributed tracing"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        @app.before_request
        def before_request():
            # Extract trace ID from request headers or generate a new one
            trace_id = request.headers.get('X-Trace-ID')
            if not trace_id:
                trace_id = str(uuid.uuid4())
                
            # Generate a request ID
            request_id = str(uuid.uuid4())
            
            # Store in Flask global context
            g.trace_id = trace_id
            g.request_id = request_id
            
            current_app.logger.debug(f"Request started [Trace ID: {trace_id}, Request ID: {request_id}]")
        
        @app.after_request
        def after_request(response):
            # Add trace ID to response headers
            if hasattr(g, 'trace_id'):
                response.headers['X-Trace-ID'] = g.trace_id
            
            return response

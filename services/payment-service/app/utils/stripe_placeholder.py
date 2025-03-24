"""
Stripe placeholder module that mocks the minimum required functionality
for the payment service to work without requiring the real stripe package.
This is a temporary solution and should be replaced with actual Stripe
integration later.
"""
import uuid

# Set a default API key (will be overridden by config)
api_key = "placeholder_api_key"

def log_action(message):
    """
    Log a stripe action without depending on Flask's current_app.
    This is a placeholder for what would normally go to current_app.logger.
    """
    import logging
    logging = logging.getLogger('stripe_placeholder')
    logging.info(message)

class PaymentIntent:
    """Mock PaymentIntent class that simulates Stripe's PaymentIntent functionality"""
    
    @classmethod
    def create(cls, amount=None, currency=None, payment_method=None, 
               customer=None, capture_method=None, description=None):
        """Mock create method that returns a fake payment intent object"""
        log_action(f"[STRIPE PLACEHOLDER] Creating payment intent: amount={amount}, description={description}")
        return cls(
            id=f"pi_{uuid.uuid4().hex}",
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            customer=customer,
            capture_method=capture_method,
            description=description
        )
    
    @classmethod
    def cancel(cls, payment_intent_id):
        """Mock cancel method"""
        log_action(f"[STRIPE PLACEHOLDER] Cancelling payment intent: {payment_intent_id}")
        return {"id": payment_intent_id, "status": "canceled"}
    
    @classmethod
    def capture(cls, payment_intent_id):
        """Mock capture method"""
        log_action(f"[STRIPE PLACEHOLDER] Capturing payment intent: {payment_intent_id}")
        return {"id": payment_intent_id, "status": "captured"}
    
    def __init__(self, id, amount=None, currency=None, payment_method=None, 
                customer=None, capture_method=None, description=None):
        """Initialize a mock payment intent with similar properties to Stripe's"""
        self.id = id
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.customer = customer
        self.capture_method = capture_method
        self.description = description
        self.status = "succeeded"  # Default to succeeded for simplicity

# Add other Stripe API classes as needed

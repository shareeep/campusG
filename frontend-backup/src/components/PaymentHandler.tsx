import { loadStripe } from '@stripe/stripe-js';

// Replace with your actual Stripe publishable key
const stripePromise = loadStripe(
  "k_test_51R3w7tQR8BO665MwdItLEUCpoGtnkeSyXbD2yiyGs7BpkLREWVqndrcJD9XVetcGMJLjdcm5YZ5yP3Zf06x3WW4w00pzCEey01"
);

// Simple interfaces with minimal type requirements
interface PaymentResponse {
  requires_action?: boolean;
  client_secret?: string;
  payment_id?: string;
  status?: string;
}

interface PaymentResult {
  success: boolean;
  error?: string;
}

/**
 * Handles 3D Secure authentication flow when required by the payment processor
 */
async function handlePaymentResponse(paymentResponse: PaymentResponse): Promise<PaymentResult> {
  // Only when 3D Secure is required
  if (paymentResponse.requires_action && paymentResponse.client_secret) {
    try {
      const stripe = await stripePromise;
      
      if (!stripe) {
        return { success: false, error: "Failed to load Stripe" };
      }
      
      // Handle 3D Secure authentication
      const result = await stripe.handleCardAction(paymentResponse.client_secret);
      
      if (result.error) {
        return { 
          success: false, 
          error: result.error.message 
        };
      }
      
      // Check if we have a successful payment intent
      if (result.paymentIntent && result.paymentIntent.status) {
        return { success: true };
      }
      
      return { 
        success: false,
        error: "Authentication failed or payment intent status is invalid" 
      };
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Authentication failed";
      return { success: false, error: errorMessage };
    }
  }
  
  // No action required, payment was successful
  return { success: true };
}

export { handlePaymentResponse };

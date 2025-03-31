import { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Button } from '@/components/ui/button';

interface CreditCardFormProps {
  onSave: (paymentMethodId: string) => Promise<void>;
  defaultErrorMessage?: string | null;
  userId?: string;
  userEmail?: string; // Add email prop
}

export function CreditCardForm({ onSave, defaultErrorMessage, userId, userEmail }: CreditCardFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState<string | null>(defaultErrorMessage || null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!stripe || !elements) {
      return;
    }
    
    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Step 1: Create a Payment Method - use userEmail if available
      const { error: createError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
        // Use the email address from user profile instead of ID
        billing_details: userEmail ? { email: userEmail } : undefined
      });
      
      if (createError) {
        setError(createError.message || 'An error occurred with your card');
        setLoading(false);
        return;
      }
      
      if (!paymentMethod || !paymentMethod.id) {
        setError('Failed to create payment method');
        setLoading(false);
        return;
      }
      
      // Step 2: Setup for future usage by creating and attaching to a customer
      // This is now handled by the backend in the update-payment endpoint
      await onSave(paymentMethod.id);
      
      setSuccess(true);
      cardElement.clear();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Card element style to match your existing UI
  const cardElementStyle = {
    base: {
      color: '#333',
      fontFamily: '"Arial", sans-serif',
      fontSize: '16px',
      '::placeholder': {
        color: '#aab7c4',
      },
    },
    invalid: {
      color: '#dc2626', // red-600 in Tailwind
      iconColor: '#dc2626',
    },
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Card Details
        </label>
        <div className="border rounded-md p-3 bg-white">
          <CardElement options={{ style: cardElementStyle }} />
        </div>
      </div>
      
      {error && (
        <div className="rounded-md bg-red-50 p-3">
          <div className="flex">
            <div className="text-sm text-red-700">{error}</div>
          </div>
        </div>
      )}
      
      {success && (
        <div className="rounded-md bg-green-50 p-3">
          <div className="flex">
            <div className="text-sm text-green-700">Your card has been saved successfully!</div>
          </div>
        </div>
      )}
      
      <Button 
        type="submit" 
        disabled={!stripe || loading}
        className="w-full"
      >
        {loading ? 'Saving...' : 'Save Card'}
      </Button>
    </form>
  );
}

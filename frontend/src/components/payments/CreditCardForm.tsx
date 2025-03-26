import { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Button } from '@/components/ui/button';

interface CreditCardFormProps {
  onSave: (paymentMethodId: string) => Promise<void>;
  defaultErrorMessage?: string | null;
}

export function CreditCardForm({ onSave, defaultErrorMessage }: CreditCardFormProps) {
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
      const { error, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });
      
      if (error) {
        setError(error.message || 'An error occurred with your card');
        return;
      }
      
      if (!paymentMethod || !paymentMethod.id) {
        setError('Failed to create payment method');
        return;
      }
      
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

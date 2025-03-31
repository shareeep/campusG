import { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import { StripeProvider } from '@/providers/StripeProvider';
import { CreditCardForm } from '@/components/payments/CreditCardForm';
import { SavedCardDisplay } from '@/components/payments/SavedCardDisplay';
import { CreditCard } from 'lucide-react';

interface PaymentMethod {
  last4?: string;
  brand?: string;
  exp_month?: string;
  exp_year?: string;
  payment_method_id?: string;
  token?: string;
}

export default function PaymentSettingsPage() {
  const { user, isLoaded } = useUser();
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPaymentMethod() {
      if (!isLoaded || !user) return;
      
      try {
        const response = await fetch(`http://localhost:3001/api/user/${user.id}/payment`);
        const data = await response.json();
        
        if (data.success) {
          setPaymentMethod(data.payment_info);
        }
      } catch (err) {
        // Don't set error if the user just doesn't have a payment method yet
        console.error('Error fetching payment method:', err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchPaymentMethod();
  }, [user, isLoaded]);

  const savePaymentMethod = async (paymentMethodId: string) => {
    if (!user) return;
    
    try {
      // Fix endpoint URL to match the backend - ensure consistency with "user" (singular)
      const response = await fetch(
        `http://localhost:3001/api/user/${user.id}/payment-methods`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ payment_method_id: paymentMethodId }),
        }
      );
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to save payment method');
      }
      
      // Handle either response format - card or payment_info
      if (data.card) {
        setPaymentMethod(data.card);
      } else if (data.payment_info) {
        setPaymentMethod(data.payment_info);
      } else {
        // Fallback to fetching payment info using the correct endpoint
        const refreshResponse = await fetch(`http://localhost:3001/api/user/${user.id}/payment`);
        const refreshData = await refreshResponse.json();
        
        if (refreshData.success) {
          setPaymentMethod(refreshData.payment_info);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save payment method');
      throw err;
    }
  };

  const deletePaymentMethod = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `http://localhost:3001/api/user/${user.id}/payment`,
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || 'Failed to delete payment method');
      }
      
      // Successfully deleted - clear the payment method from state
      setPaymentMethod(null);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete payment method');
    } finally {
      setLoading(false);
    }
  };

  if (!isLoaded) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <CreditCard className="h-6 w-6 text-blue-600" />
        Payment Settings
      </h1>
      
      <div className="space-y-6">
        {!loading && paymentMethod && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Your Saved Card</h2>
            <SavedCardDisplay 
              last4={paymentMethod.last4}
              brand={paymentMethod.brand}
              expiryMonth={paymentMethod.exp_month}
              expiryYear={paymentMethod.exp_year}
              onDelete={deletePaymentMethod}
              isDeleting={loading}
            />
          </div>
        )}
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">
            {paymentMethod ? 'Update Payment Method' : 'Add Payment Method'}
          </h2>
          <StripeProvider>
            <CreditCardForm 
              onSave={savePaymentMethod}
              defaultErrorMessage={error}
              userId={user?.id}
              userEmail={user?.primaryEmailAddress?.emailAddress} // Add email from user profile
            />
          </StripeProvider>
          <p className="mt-4 text-sm text-gray-500">
            Your card information is securely processed by Stripe. We never store your full card details.
          </p>
        </div>
      </div>
    </div>
  );
}
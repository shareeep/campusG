import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CreditCard, Lock, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { useBackendUser } from '@/lib/hooks/useBackendUser';
import { processPayment } from '@/lib/api-client';
import { handlePaymentResponse } from '@/components/PaymentHandler';

interface PaymentMethod {
  id: string;
  type: 'card';
  last4: string;
  brand: string;
}

export function PaymentAuthorizationPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { backendUser, clerkUser } = useBackendUser();
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  // Helper function to extract card data consistently regardless of format
  const getCardData = () => {
    const card = backendUser?.userStripeCard || backendUser?.user_stripe_card;
    if (!card) return null;
    
    const paymentMethodId = 
      card.paymentMethodId || 
      card.payment_method_id || 
      '';
      
    // Only return data if we have a valid payment method ID
    if (!paymentMethodId) return null;
    
    return {
      id: paymentMethodId,
      type: 'card' as const, // Use const assertion to ensure literal type
      last4: card.last4 || card.last_four || '•••',
      brand: card.brand || card.card_type || 'Card'
    };
  };

  // Check if there's a valid stored payment method
  const cardData = getCardData();
  const hasStoredCard = cardData !== null && 
                        (backendUser?.stripeCustomerId || backendUser?.stripe_customer_id);
  
  const savedMethods: PaymentMethod[] = hasStoredCard && cardData ? [cardData] : [];
  
  // Auto-select the payment method if there's only one
  useEffect(() => {
    if (savedMethods.length === 1 && !selectedMethod) {
      setSelectedMethod(savedMethods[0].id);
    }
  }, [savedMethods, selectedMethod]);

  const handlePaymentAuthorization = async () => {
    if (!selectedMethod) {
      toast({
        title: "Payment Method Required",
        description: "Please select a payment method to continue.",
        variant: "destructive"
      });
      return;
    }

    if (!clerkUser?.id || !orderId) {
      toast({
        title: "Missing Information",
        description: "User ID or Order ID is missing.",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);
    setPaymentError(null);

    try {
      // Process the payment with Stripe through our backend
      const amount = 1299; // This would normally come from the order details
      const paymentResponse = await processPayment(clerkUser.id, orderId, amount);
      
      if (paymentResponse.error) {
        throw new Error(paymentResponse.error);
      }

      // Handle 3D Secure authentication if required
      if (paymentResponse.requires_action && paymentResponse.client_secret) {
        const result = await handlePaymentResponse(paymentResponse);
        
        if (!result.success) {
          throw new Error(result.error || "Payment authentication failed");
        }
      }

      toast({
        title: "Payment Secured",
        description: "Your payment has been authorized and placed in escrow.",
      });

      navigate(`/customer/order/${orderId}/tracking`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown payment error";
      setPaymentError(errorMessage);
      toast({
        title: "Payment Failed",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h1 className="text-2xl font-bold mb-6">Payment Authorization</h1>

          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold mb-4">Saved Payment Methods</h2>
              <div className="space-y-3">
                {savedMethods.map((method) => (
                  <div
                    key={method.id}
                    className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                      selectedMethod === method.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedMethod(method.id)}
                  >
                    <CreditCard className="h-5 w-5 text-gray-500 mr-3" />
                    <div>
                      <p className="font-medium">
                        {method.brand.charAt(0).toUpperCase() + method.brand.slice(1)} ending in {method.last4}
                      </p>
                    </div>
                    <div className="ml-auto">
                      <div
                        className={`w-5 h-5 rounded-full border-2 ${
                          selectedMethod === method.id
                            ? 'border-blue-500 bg-blue-500'
                            : 'border-gray-300'
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {savedMethods.length === 0 && (
              <div className="text-center py-8 text-gray-500 border rounded-md mb-6">
                <CreditCard className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                <p>No payment methods available</p>
              </div>
            )}

            <div className="border-t pt-6">
              <Button
                onClick={() => navigate('/profile')}
                variant="secondary"
                className="w-full"
              >
                Manage Payment Methods
              </Button>
            </div>

            {paymentError && (
              <div className="rounded-md bg-red-50 p-3">
                <div className="flex">
                  <div className="text-sm text-red-700">{paymentError}</div>
                </div>
              </div>
            )}

            <div className="bg-blue-50 p-4 rounded-lg flex items-start">
              <Lock className="h-5 w-5 text-blue-500 mr-3 mt-0.5" />
              <div className="text-sm text-blue-700">
                <p className="font-medium mb-1">Secure Payment Process</p>
                <p>Your payment will be held in escrow until your order is successfully delivered.</p>
              </div>
            </div>

            <Button
              onClick={handlePaymentAuthorization}
              className="w-full"
              disabled={!selectedMethod || isProcessing || savedMethods.length === 0}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing Payment...
                </>
              ) : (
                'Authorize Payment'
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

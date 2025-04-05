import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CreditCard, Lock, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

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
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null);

  // Mock saved payment methods
  const savedMethods: PaymentMethod[] = [
    { id: '1', type: 'card', last4: '4242', brand: 'visa' },
    { id: '2', type: 'card', last4: '5555', brand: 'mastercard' }
  ];

  const handlePaymentAuthorization = async () => {
    if (!selectedMethod) {
      toast({
        title: "Payment Method Required",
        description: "Please select a payment method to continue.",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);

    try {
      // Simulated payment authorization
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Simulated escrow transfer
      await new Promise(resolve => setTimeout(resolve, 1500));

      toast({
        title: "Payment Secured",
        description: "Your payment has been authorized and placed in escrow.",
      });

      navigate(`/customer/order/${orderId}/tracking`);
    } catch (error) {
      toast({
        title: "Payment Failed",
        description: "There was an error processing your payment. Please try again.",
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

            <div className="border-t pt-6">
              <Button
                onClick={() => navigate('/customer/payment-methods/new')}
                variant="outline"
                className="w-full"
              >
                Add New Payment Method
              </Button>
            </div>

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
              disabled={!selectedMethod || isProcessing}
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
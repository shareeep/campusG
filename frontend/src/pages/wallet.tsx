import { useEffect, useState } from 'react';
import { Wallet, CreditCard, ArrowUpRight, ArrowDownLeft, Plus } from 'lucide-react';
import { getWallet } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { Wallet as WalletType } from '@/lib/types';
import { CreditCardForm } from '@/components/payments/CreditCardForm';
import { SavedCardDisplay } from '@/components/payments/SavedCardDisplay';
import { useBackendUser } from '@/lib/hooks/useBackendUser';
import { savePaymentMethod, deletePaymentMethod } from '@/lib/api-client';
import { Button } from '@/components/ui/button';

export function WalletPage() {
  const { id: userId } = useUser();
  const { backendUser, clerkUser } = useBackendUser();
  const [wallet, setWallet] = useState<WalletType | null>(null);
  const [showAddCard, setShowAddCard] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWallet = async () => {
      if (!userId) return;
      const data = await getWallet(userId);
      setWallet(data);
    };

    fetchWallet();
    const interval = setInterval(fetchWallet, 5000);
    return () => clearInterval(interval);
  }, [userId]);

  if (!wallet) {
    return (
      <div className="container mx-auto p-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-2">Loading wallet...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">My Wallet</h1>
            <Wallet className="h-6 w-6 text-blue-600" />
          </div>

          <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg p-6 text-white">
            <div className="flex items-center mb-4">
              <CreditCard className="h-6 w-6 mr-2" />
              <span className="text-sm opacity-90">Available Balance</span>
            </div>
            <div className="text-3xl font-bold">
              ${wallet.balance.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Payment Methods</h2>
            {!showAddCard && !backendUser?.user_stripe_card && (
              <Button 
                variant="secondary" 
                size="sm" 
                className="flex items-center gap-1"
                onClick={() => setShowAddCard(true)}
              >
                <Plus className="h-4 w-4" />
                Add Card
              </Button>
            )}
          </div>

          {showAddCard ? (
            <div className="mb-6">
              <CreditCardForm 
                onSave={async (paymentMethodId) => {
                  if (!clerkUser?.id) return;
                  setError(null);
                  try {
                    const success = await savePaymentMethod(clerkUser.id, paymentMethodId);
                    if (success) {
                      setShowAddCard(false);
                    } else {
                      setError('Failed to save payment method');
                    }
                  } catch (err) {
                    setError('An error occurred while saving your card');
                    console.error(err);
                  }
                }}
                defaultErrorMessage={error}
                userEmail={clerkUser?.primaryEmailAddress?.emailAddress}
              />
            </div>
          ) : backendUser?.user_stripe_card ? (
            <div className="mb-4">
              <SavedCardDisplay 
                last4={backendUser.user_stripe_card.last_four}
                brand={backendUser.user_stripe_card.card_type}
                expiryMonth={backendUser.user_stripe_card.expiry_month}
                expiryYear={backendUser.user_stripe_card.expiry_year}
                onDelete={async () => {
                  if (!clerkUser?.id) return;
                  setIsDeleting(true);
                  try {
                    const success = await deletePaymentMethod(clerkUser.id);
                    if (!success) {
                      setError('Failed to delete payment method');
                    }
                  } catch (err) {
                    setError('An error occurred while deleting your card');
                    console.error(err);
                  } finally {
                    setIsDeleting(false);
                  }
                }}
                isDeleting={isDeleting}
              />
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 border rounded-md">
              <CreditCard className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No payment methods saved</p>
              <Button 
                variant="secondary" 
                size="sm" 
                className="mt-4 flex items-center gap-1 mx-auto"
                onClick={() => setShowAddCard(true)}
              >
                <Plus className="h-4 w-4" />
                Add Card
              </Button>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Transaction History</h2>

          <div className="space-y-4">
            {wallet.transactions.map((transaction) => (
              <div
                key={transaction.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center">
                  <div className={`
                    p-2 rounded-full mr-4
                    ${transaction.type === 'earning' 
                      ? 'bg-green-100 text-green-600'
                      : 'bg-red-100 text-red-600'
                    }
                  `}>
                    {transaction.type === 'earning' 
                      ? <ArrowDownLeft className="h-5 w-5" />
                      : <ArrowUpRight className="h-5 w-5" />
                    }
                  </div>
                  <div>
                    <p className="font-medium">
                      {transaction.type === 'earning' ? 'Delivery Earning' : 'Order Payment'}
                    </p>
                    <p className="text-sm text-gray-600">
                      Order #{transaction.order_id}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(transaction.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className={`
                  font-semibold
                  ${transaction.type === 'earning' ? 'text-green-600' : 'text-red-600'}
                `}>
                  {transaction.type === 'earning' ? '+' : '-'}
                  ${transaction.amount.toFixed(2)}
                </div>
              </div>
            ))}

            {wallet.transactions.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>No transactions yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Wallet, CreditCard, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { getWallet } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { Wallet as WalletType } from '@/lib/types';

export function WalletPage() {
  const { id: userId } = useUser();
  const [wallet, setWallet] = useState<WalletType | null>(null);

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
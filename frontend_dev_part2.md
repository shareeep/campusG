# Payment Component Integration (Continued)

### 5.3 Create Payment Handler Component

```typescript
// frontend/src/components/PaymentHandler.tsx
import { useState, useEffect } from 'react';
import { toast } from '@/components/ui/use-toast';
import { useUserSync } from '@/providers/UserSyncProvider';
import { addPaymentMethod, getPaymentInfo, deletePaymentMethod } from '@/lib/payment-api';
import { CreditCardForm } from './payments/CreditCardForm';
import { SavedCardDisplay } from './payments/SavedCardDisplay';
import { UserStripeCard } from '@/lib/types';
import { Button } from '@/components/ui/button';

export function PaymentHandler() {
  const { backendUser } = useUserSync();
  const [savedCard, setSavedCard] = useState<UserStripeCard | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showAddCard, setShowAddCard] = useState(false);
  
  // Load saved card info
  useEffect(() => {
    async function loadPaymentInfo() {
      if (!backendUser?.clerk_user_id) return;
      
      setLoading(true);
      try {
        const paymentInfo = await getPaymentInfo(backendUser.clerk_user_id);
        setSavedCard(paymentInfo);
      } catch (error) {
        console.error('Error loading payment info:', error);
        toast({
          title: 'Error',
          description: 'Failed to load payment information',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    }
    
    loadPaymentInfo();
  }, [backendUser]);
  
  // Handle saving a new payment method
  const handleSaveCard = async (paymentMethodId: string) => {
    if (!backendUser?.clerk_user_id) {
      toast({
        title: 'Error',
        description: 'User information not available',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      const updatedCard = await addPaymentMethod(backendUser.clerk_user_id, paymentMethodId);
      setSavedCard(updatedCard);
      setShowAddCard(false);
      toast({
        title: 'Success',
        description: 'Payment method saved successfully',
      });
    } catch (error) {
      console.error('Error saving payment method:', error);
      toast({
        title: 'Error',
        description: 'Failed to save payment method',
        variant: 'destructive',
      });
    }
  };
  
  // Handle deleting a saved card
  const handleDeleteCard = async () => {
    if (!backendUser?.clerk_user_id) return;
    
    setIsDeleting(true);
    try {
      await deletePaymentMethod(backendUser.clerk_user_id);
      setSavedCard(null);
      toast({
        title: 'Success',
        description: 'Payment method removed',
      });
    } catch (error) {
      console.error('Error deleting payment method:', error);
      toast({
        title: 'Error',
        description: 'Failed to remove payment method',
        variant: 'destructive',
      });
    } finally {
      setIsDeleting(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex justify-center p-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Payment Methods</h2>
      
      {savedCard ? (
        <SavedCardDisplay
          last4={savedCard.last4}
          brand={savedCard.brand}
          expiryMonth={savedCard.exp_month}
          expiryYear={savedCard.exp_year}
          onDelete={handleDeleteCard}
          isDeleting={isDeleting}
        />
      ) : showAddCard ? (
        <div className="border rounded-md p-4">
          <CreditCardForm
            onSave={handleSaveCard}
            userId={backendUser?.clerk_user_id}
            userEmail={backendUser?.email}
          />
          <div className="mt-4">
            <Button
              variant="outline"
              onClick={() => setShowAddCard(false)}
              className="w-full"
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center p-6 border rounded-md">
          <p className="text-gray-500 mb-4">No payment methods saved</p>
          <Button
            onClick={() => setShowAddCard(true)}
            className="w-full md:w-auto"
          >
            Add Payment Method
          </Button>
        </div>
      )}
    </div>
  );
}
```

## 6. Wallet Page Enhancement

Now that we have all the payment components set up, let's enhance the wallet page to display payment methods and transaction history.

### 6.1 Update Wallet Page

```typescript
// frontend/src/pages/wallet.tsx
import { useEffect, useState } from 'react';
import { Wallet, CreditCard, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { getWallet } from '@/lib/api';
import { useUserSync } from '@/providers/UserSyncProvider';
import { PaymentHandler } from '@/components/PaymentHandler';
import type { Wallet as WalletType } from '@/lib/types';

export function WalletPage() {
  const { backendUser } = useUserSync();
  const [wallet, setWallet] = useState<WalletType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWallet = async () => {
      if (!backendUser?.clerk_user_id) return;
      
      setLoading(true);
      try {
        const data = await getWallet(backendUser.clerk_user_id);
        setWallet(data);
      } catch (error) {
        console.error('Error fetching wallet:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWallet();
    const interval = setInterval(fetchWallet, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [backendUser]);

  if (loading && !wallet) {
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
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Balance Card */}
        <div className="bg-white rounded-lg shadow-sm p-6">
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
              ${wallet?.balance?.toFixed(2) || '0.00'}
            </div>
          </div>
        </div>
        
        {/* Payment Methods Section */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <PaymentHandler />
        </div>

        {/* Transaction History */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Transaction History</h2>

          <div className="space-y-4">
            {wallet?.transactions?.map((transaction) => (
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

            {(!wallet?.transactions || wallet.transactions.length === 0) && (
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
```

### 6.2 Add Wallet API Functions

Add these functions to your API client:

```typescript
// Add to frontend/src/lib/api.ts

/**
 * Get wallet information for a user
 */
export async function getWallet(userId: string): Promise<Wallet> {
  try {
    const response = await apiRequest(`/user/${userId}/wallet`);
    return response.wallet;
  } catch (error) {
    console.error('Error fetching wallet:', error);
    // Return a default empty wallet
    return {
      user_id: userId,
      balance: 0,
      transactions: []
    };
  }
}
```

### 6.3 Update Types for Wallet

```typescript
// Add to frontend/src/lib/types.ts

export interface Wallet {
  user_id: string;
  balance: number;
  transactions: Transaction[];
}

export interface Transaction {
  id: string;
  user_id: string;
  order_id: string;
  amount: number;
  type: 'payment' | 'earning';
  status: 'pending' | 'held' | 'completed';
  created_at: string;
}
```

## 7. API Layer Consolidation

Now let's integrate our API layer to work with both Supabase and our backend services. We'll create an abstraction layer that handles the different data sources.

### 7.1 Create API Service Factory

```typescript
// frontend/src/lib/api-service-factory.ts
import { supabase } from './supabase';
import { apiRequest } from './api-client';
import { BackendUser, Order, Transaction } from './types';

/**
 * Factory to get the appropriate API service based on resource type
 */
export function getApiService<T>(resourceType: string): ApiService<T> {
  switch (resourceType) {
    case 'user':
      return new UserApiService() as unknown as ApiService<T>;
    case 'order':
      return new OrderApiService() as unknown as ApiService<T>;
    case 'transaction':
      return new TransactionApiService() as unknown as ApiService<T>;
    default:
      throw new Error(`Unknown resource type: ${resourceType}`);
  }
}

/**
 * Generic API service interface
 */
interface ApiService<T> {
  get(id: string): Promise<T | null>;
  list(filters?: Record<string, any>): Promise<T[]>;
  create(data: Partial<T>): Promise<T>;
  update(id: string, data: Partial<T>): Promise<T>;
  delete(id: string): Promise<boolean>;
}

/**
 * User API service using our backend service
 */
class UserApiService implements ApiService<BackendUser> {
  async get(id: string): Promise<BackendUser | null> {
    try {
      const response = await apiRequest(`/user/${id}`);
      return response.user;
    } catch (error) {
      console.error('Error fetching user:', error);
      return null;
    }
  }

  async list(filters?: Record<string, any>): Promise<BackendUser[]> {
    try {
      const response = await apiRequest('/user/list-users');
      return response.users || [];
    } catch (error) {
      console.error('Error listing users:', error);
      return [];
    }
  }

  async create(data: Partial<BackendUser>): Promise<BackendUser> {
    try {
      const response = await apiRequest('/user/sync-from-frontend', 'POST', { body: data });
      return response.user;
    } catch (error) {
      console.error('Error creating user:', error);
      throw error;
    }
  }

  async update(id: string, data: Partial<BackendUser>): Promise<BackendUser> {
    try {
      const response = await apiRequest(`/user/${id}`, 'PUT', { body: data });
      return response.user;
    } catch (error) {
      console.error('Error updating user:', error);
      throw error;
    }
  }

  async delete(id: string): Promise<boolean> {
    throw new Error('User deletion not supported');
  }
}

/**
 * Order API service using Supabase
 */
class OrderApiService implements ApiService<Order> {
  async get(id: string): Promise<Order | null> {
    const { data, error } = await supabase
      .from('orders')
      .select('*, order_items(*)')
      .eq('id', id)
      .single();
      
    if (error) {
      console.error('Error fetching order:', error);
      return null;
    }
    
    return data as Order;
  }

  async list(filters?: Record<string, any>): Promise<Order[]> {
    let query = supabase
      .from('orders')
      .select('*, order_items(*)');
      
    // Apply filters if provided
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        query = query.eq(key, value);
      });
    }
    
    const { data, error } = await query.order('created_at', { ascending: false });
    
    if (error) {
      console.error('Error listing orders:', error);
      return [];
    }
    
    return data as Order[];
  }

  async create(data: Partial<Order>): Promise<Order> {
    const { data: order, error } = await supabase
      .from('orders')
      .insert(data)
      .select('*')
      .single();
      
    if (error) {
      console.error('Error creating order:', error);
      throw error;
    }
    
    return order as Order;
  }

  async update(id: string, data: Partial<Order>): Promise<Order> {
    const { data: order, error } = await supabase
      .from('orders')
      .update(data)
      .eq('id', id)
      .select('*')
      .single();
      
    if (error) {
      console.error('Error updating order:', error);
      throw error;
    }
    
    return order as Order;
  }

  async delete(id: string): Promise<boolean> {
    const { error } = await supabase
      .from('orders')
      .delete()
      .eq('id', id);
      
    if (error) {
      console.error('Error deleting order:', error);
      return false;
    }
    
    return true;
  }
}

/**
 * Transaction API service using our backend service
 */
class TransactionApiService implements ApiService<Transaction> {
  async get(id: string): Promise<Transaction | null> {
    try {
      const response = await apiRequest(`/transaction/${id}`);
      return response.transaction;
    } catch (error) {
      console.error('Error fetching transaction:', error);
      return null;
    }
  }

  async list(filters?: Record<string, any>): Promise<Transaction[]> {
    try {
      // If we have userId filter, use it to get wallet transactions
      if (filters?.user_id) {
        const response = await apiRequest(`/user/${filters.user_id}/wallet`);
        return response.wallet?.transactions || [];
      }
      
      return [];
    } catch (error) {
      console.error('Error listing transactions:', error);
      return [];
    }
  }

  async create(data: Partial<Transaction>): Promise<Transaction> {
    throw new Error('Transaction creation not supported directly');
  }

  async update(id: string, data: Partial<Transaction>): Promise<Transaction> {
    throw new Error('Transaction update not supported');
  }

  async delete(id: string): Promise<boolean> {
    throw new Error('Transaction deletion not supported');
  }
}
```

### 7.2 Use the API Service in Components

Update components to use the new API service:

```typescript
// Example usage in a component
import { useEffect, useState } from 'react';
import { getApiService } from '@/lib/api-service-factory';
import { Order } from '@/lib/types';
import { useUserSync } from '@/providers/UserSyncProvider';

export function OrderHistory() {
  const { backendUser } = useUserSync();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function fetchOrders() {
      if (!backendUser?.clerk_user_id) return;
      
      setLoading(true);
      try {
        const orderService = getApiService<Order>('order');
        const userOrders = await orderService.list({ user_id: backendUser.clerk_user_id });
        setOrders(userOrders);
      } catch (error) {
        console.error('Error fetching orders:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchOrders();
  }, [backendUser]);
  
  // Render orders...
}
```

## 8. Testing and Validation

After implementing all the integration steps, it's essential to test thoroughly to ensure everything works as expected.

### 8.1 Authentication Testing

1. Test sign-up and sign-in flows
2. Verify that Clerk user data is synced with the backend
3. Test user session persistence after page refreshes
4. Verify protected routes redirect correctly

### 8.2 Payment Testing

1. Test adding a payment method
   - Use Stripe test cards (e.g., `4242 4242 4242 4242`)
   - Verify the card is saved in the backend
   - Check error handling for invalid cards

2. Test payment method display
   - Verify saved cards display correctly
   - Test card deletion

3. Test authorization flow
   - Ensure payment authorization works for orders

### 8.3 API Testing

1. Verify API calls to both Supabase and your backend services
2. Test error handling and fallbacks
3. Verify data consistency between both systems

### 8.4 Performance Considerations

1. Monitor API call frequency
2. Consider implementing caching for frequently accessed data
3. Use React's performance optimization features (memoization, etc.)

### 8.5 Security Testing

1. Verify Clerk token validation on protected routes
2. Ensure sensitive data (payment information) is properly handled
3. Test API endpoint security and permissions

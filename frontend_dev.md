# Complete Implementation Guide: Integrating Clerk Auth & Stripe Payments

This guide provides detailed steps to integrate Clerk authentication and Stripe payment functionality from the frontend-backup into your current frontend project, with a focus on frontend-driven synchronization with your backend user service.

## Table of Contents

1. [Project Preparation](#1-project-preparation)
2. [Clerk Authentication Integration](#2-clerk-authentication-integration)
3. [Backend Synchronization Implementation](#3-backend-synchronization-implementation)
4. [Stripe Integration](#4-stripe-integration)
5. [Payment Component Integration](#5-payment-component-integration)
6. [Wallet Page Enhancement](#6-wallet-page-enhancement)
7. [API Layer Consolidation](#7-api-layer-consolidation)
8. [Testing and Validation](#8-testing-and-validation)

## 1. Project Preparation

### 1.1 Add Required Dependencies

```bash
# Navigate to your frontend directory
cd frontend

# Install Clerk dependencies
npm install @clerk/clerk-react

# Install Stripe dependencies
npm install @stripe/stripe-js @stripe/react-stripe-js

# Install any other missing dependencies
npm install axios
```

### 1.2 Environment Configuration

Create or update your `.env` files to include necessary API keys:

```
# .env file
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
VITE_USER_SERVICE_URL=http://localhost:3001/api
```

Create a file to load environment variables in your project:

```typescript
// frontend/src/lib/env.ts
export const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
export const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
export const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3001/api';

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Missing Clerk publishable key');
}

if (!STRIPE_PUBLISHABLE_KEY) {
  throw new Error('Missing Stripe publishable key');
}
```

## 2. Clerk Authentication Integration

### 2.1 Create Clerk Provider Component

```typescript
// frontend/src/providers/ClerkProvider.tsx
import { ClerkProvider as BaseClerkProvider } from '@clerk/clerk-react';
import { ReactNode } from 'react';
import { CLERK_PUBLISHABLE_KEY } from '@/lib/env';

interface ClerkProviderProps {
  children: ReactNode;
}

export function ClerkProvider({ children }: ClerkProviderProps) {
  return (
    <BaseClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      {children}
    </BaseClerkProvider>
  );
}
```

### 2.2 Update App.tsx

```typescript
// frontend/src/App.tsx
import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';
import { ToastProvider } from '@/components/ui/toast-provider';
import { ClerkProvider } from '@/providers/ClerkProvider';
import { StripeProvider } from '@/providers/StripeProvider';
import { UserSyncProvider } from '@/providers/UserSyncProvider';

function App() {
  return (
    <ClerkProvider>
      <UserSyncProvider>
        <StripeProvider>
          <ToastProvider>
            <Router>
              <AppRoutes />
            </Router>
          </ToastProvider>
        </StripeProvider>
      </UserSyncProvider>
    </ClerkProvider>
  );
}

export default App;
```

### 2.3 Update Authentication Layout

Ensure your auth layout is compatible with Clerk:

```typescript
// frontend/src/components/layout/auth-layout.tsx
import { useUser as useClerkUser } from '@clerk/clerk-react';
import { Navigate } from 'react-router-dom';
import { ReactNode } from 'react';

interface AuthLayoutProps {
  children: ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  const { isSignedIn, isLoaded } = useClerkUser();
  
  // Show loading state while Clerk loads
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  // Redirect to sign-in if not authenticated
  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {children}
    </div>
  );
}
```

### 2.4 Update Sign-In and Sign-Up Pages

```typescript
// frontend/src/pages/auth/sign-in.tsx
import { SignIn } from '@clerk/clerk-react';

export function SignInPage() {
  return (
    <div className="flex flex-col items-center">
      <h1 className="text-2xl font-bold mb-8">Sign In to CampusEats</h1>
      <SignIn
        routing="path"
        path="/sign-in"
        redirectUrl="/role-select"
        appearance={{
          elements: {
            rootBox: "mx-auto w-full",
            card: "bg-white shadow-md rounded-lg p-8"
          }
        }}
      />
    </div>
  );
}

// frontend/src/pages/auth/sign-up.tsx
import { SignUp } from '@clerk/clerk-react';

export function SignUpPage() {
  return (
    <div className="flex flex-col items-center">
      <h1 className="text-2xl font-bold mb-8">Create Your CampusEats Account</h1>
      <SignUp
        routing="path"
        path="/sign-up"
        redirectUrl="/role-select"
        appearance={{
          elements: {
            rootBox: "mx-auto w-full",
            card: "bg-white shadow-md rounded-lg p-8"
          }
        }}
      />
    </div>
  );
}
```

## 3. Backend Synchronization Implementation

### 3.1 Create API Client for User Service

```typescript
// frontend/src/lib/api-client.ts
import { USER_SERVICE_URL } from './env';
import type { BackendUser } from './types';

interface ApiClientOptions {
  headers?: Record<string, string>;
  body?: unknown;
}

/**
 * Generic API request function with error handling
 */
export async function apiRequest(
  endpoint: string, 
  method: string = 'GET', 
  options: ApiClientOptions = {}
) {
  try {
    // Build request options
    const requestOptions: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    // Add body if present
    if (options.body) {
      requestOptions.body = JSON.stringify(options.body);
    }

    // Determine if endpoint is a full URL or a relative path
    const url = endpoint.startsWith('http') 
      ? endpoint 
      : `${USER_SERVICE_URL}${endpoint}`;

    // Make request
    const response = await fetch(url, requestOptions);
    
    // Parse JSON response
    const data = await response.json();
    
    // Handle API error responses
    if (!data.success) {
      throw new Error(data.message || 'API request failed');
    }
    
    return data;
  } catch (error) {
    console.error(`API request error for ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Fetch a user by their Clerk ID
 */
export async function getUserByClerkId(clerkUserId: string): Promise<BackendUser | null> {
  try {
    const response = await apiRequest(`/user/${clerkUserId}`);
    return response.user;
  } catch (error) {
    console.error('Error fetching user by Clerk ID:', error);
    return null;
  }
}

/**
 * Create a new user in the backend based on Clerk user data
 */
export async function createUserFromClerk(clerkUser: any): Promise<BackendUser | null> {
  try {
    // Extract primary email
    const email = clerkUser.emailAddresses?.[0]?.emailAddress || '';
    
    // Extract phone if available
    const phone = clerkUser.phoneNumbers?.[0]?.phoneNumber || '';
    
    const userData = {
      clerk_user_id: clerkUser.id,
      email,
      first_name: clerkUser.firstName || '',
      last_name: clerkUser.lastName || '',
      phone_number: phone,
      username: clerkUser.username || email.split('@')[0],
    };
    
    // Since the user-service doesn't have a direct user creation endpoint from frontend,
    // we'll use a special endpoint that mimics the webhook
    const response = await apiRequest(
      `/user/sync-from-frontend`,
      'POST',
      { body: userData }
    );
    
    return response.user;
  } catch (error) {
    console.error('Error creating user from Clerk data:', error);
    return null;
  }
}

/**
 * Update an existing backend user with the latest Clerk data
 */
export async function updateUserFromClerk(clerkUser: any): Promise<BackendUser | null> {
  try {
    // Extract primary email
    const email = clerkUser.emailAddresses?.[0]?.emailAddress || '';
    
    // Extract phone if available
    const phone = clerkUser.phoneNumbers?.[0]?.phoneNumber || '';
    
    const userData = {
      email,
      first_name: clerkUser.firstName || '',
      last_name: clerkUser.lastName || '',
      phone_number: phone,
      username: clerkUser.username || '',
    };
    
    const response = await apiRequest(
      `/user/${clerkUser.id}`,
      'PUT',
      { body: userData }
    );
    
    return response.user;
  } catch (error) {
    console.error('Error updating user from Clerk data:', error);
    return null;
  }
}
```

### 3.2 Create User Types

```typescript
// frontend/src/lib/types.ts (if it doesn't already have these)
export interface BackendUser {
  clerk_user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number?: string;
  username?: string;
  user_stripe_card?: UserStripeCard;
  stripe_customer_id?: string;
  stripe_connect_account_id?: string;
  customer_rating?: number;
  runner_rating?: number;
  created_at: string;
  updated_at: string;
}

export interface UserStripeCard {
  payment_method_id?: string;
  last4: string;
  brand: string;
  exp_month: string | number;
  exp_year: string | number;
  token?: string;
  updated_at?: string;
}
```

### 3.3 Create Backend User Hook

```typescript
// frontend/src/lib/hooks/useBackendUser.ts
import { useUser } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';
import { getUserByClerkId, createUserFromClerk, updateUserFromClerk } from '@/lib/api-client';
import { BackendUser } from '@/lib/types';

/**
 * Custom hook to fetch and manage the user from our backend
 * 
 * This combines Clerk authentication with our backend user data,
 * ensuring synchronization between the two systems.
 */
export function useBackendUser() {
  const { user: clerkUser, isSignedIn, isLoaded } = useUser();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncState, setSyncState] = useState<'idle' | 'syncing' | 'synced' | 'error'>('idle');

  // Function to sync user data
  async function syncUser() {
    if (!clerkUser || !isSignedIn) return null;
    
    setLoading(true);
    setSyncState('syncing');
    setError(null);
    
    try {
      // First try to fetch the user
      let user = await getUserByClerkId(clerkUser.id);
      
      if (user) {
        // User exists, check if needs updating
        const primaryEmail = clerkUser.emailAddresses?.[0]?.emailAddress || '';
        const primaryPhone = clerkUser.phoneNumbers?.[0]?.phoneNumber || '';
        
        const needsUpdate = 
          user.email !== primaryEmail ||
          user.first_name !== clerkUser.firstName ||
          user.last_name !== clerkUser.lastName ||
          (primaryPhone && user.phone_number !== primaryPhone);
          
        if (needsUpdate) {
          console.log('User data needs synchronization, updating...');
          user = await updateUserFromClerk(clerkUser);
        }
      } else {
        // User doesn't exist, create them
        console.log('User not found in backend, creating...');
        user = await createUserFromClerk(clerkUser);
      }
      
      setBackendUser(user);
      setSyncState('synced');
      return user;
    } catch (err: unknown) {
      console.error('Error syncing with backend:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync user';
      setError(errorMessage);
      setSyncState('error');
      return null;
    } finally {
      setLoading(false);
    }
  }
  
  // Sync when auth state changes
  useEffect(() => {
    // Only attempt to fetch if the user is signed in and Clerk has loaded
    if (!isLoaded || !isSignedIn || !clerkUser) {
      return;
    }
    
    syncUser();
  }, [clerkUser, isSignedIn, isLoaded]);
  
  return { 
    backendUser, 
    clerkUser, 
    loading, 
    error,
    syncState,
    syncUser, // Expose the sync function for manual syncing
    isLoaded,
    isSignedIn
  };
}
```

### 3.4 Create User Sync Provider

```typescript
// frontend/src/providers/UserSyncProvider.tsx
import { createContext, useContext, ReactNode } from 'react';
import { useBackendUser } from '@/lib/hooks/useBackendUser';
import { BackendUser } from '@/lib/types';

interface UserSyncContextType {
  backendUser: BackendUser | null;
  loading: boolean;
  error: string | null;
  syncState: 'idle' | 'syncing' | 'synced' | 'error';
  syncUser: () => Promise<BackendUser | null>;
}

const UserSyncContext = createContext<UserSyncContextType | undefined>(undefined);

interface UserSyncProviderProps {
  children: ReactNode;
}

export function UserSyncProvider({ children }: UserSyncProviderProps) {
  const { backendUser, loading, error, syncState, syncUser } = useBackendUser();
  
  return (
    <UserSyncContext.Provider value={{ 
      backendUser, 
      loading, 
      error, 
      syncState, 
      syncUser 
    }}>
      {children}
    </UserSyncContext.Provider>
  );
}

// Custom hook to use the user sync context
export function useUserSync() {
  const context = useContext(UserSyncContext);
  if (context === undefined) {
    throw new Error('useUserSync must be used within a UserSyncProvider');
  }
  return context;
}
```

### 3.5 Add Backend API Endpoint for Frontend Sync

Update your user-service to include a new endpoint:

```python
# services/user-service/app/api/user_routes.py
# Add this endpoint

@api.route('/user/sync-from-frontend', methods=['POST'])
def sync_user_from_frontend():
    """
    Sync a user from frontend Clerk data
    
    This endpoint allows the frontend to sync a user without relying on webhooks
    """
    try:
        data = request.json
        
        if not data or 'clerk_user_id' not in data:
            return jsonify({'success': False, 'message': 'Missing clerk_user_id'}), 400
            
        clerk_user_id = data['clerk_user_id']
        
        # Check if user already exists
        user = User.query.get(clerk_user_id)
        
        if user:
            # Update existing user
            if 'email' in data:
                user.email = data['email']
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'phone_number' in data:
                user.phone_number = data['phone_number']
            if 'username' in data:
                user.username = data['username']
                
            user.updated_at = datetime.now(timezone.utc)
        else:
            # Create new user
            user = User(
                clerk_user_id=clerk_user_id,
                email=data.get('email', ''),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                phone_number=data.get('phone_number'),
                username=data.get('username'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(user)
            
            # Create Stripe customer and account if needed
            try:
                # Same Stripe account creation logic as in handle_user_created
                # ...existing Stripe customer creation code...
            except Exception as stripe_error:
                current_app.logger.error(f"Stripe error during frontend sync: {str(stripe_error)}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User synced successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error syncing user from frontend: {str(e)}")
        return jsonify({'success': False, 'message': f"Failed to sync user: {str(e)}"}), 500
```

## 4. Stripe Integration

### 4.1 Create Stripe Provider

```typescript
// frontend/src/providers/StripeProvider.tsx
import { ReactNode } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { STRIPE_PUBLISHABLE_KEY } from '@/lib/env';

// Create a promise that resolves with the Stripe object
const stripePromise = loadStripe(STRIPE_PUBLISHABLE_KEY);

interface StripeProviderProps {
  children: ReactNode;
}

export function StripeProvider({ children }: StripeProviderProps) {
  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  );
}
```

### 4.2 Create Payment API Client

```typescript
// frontend/src/lib/payment-api.ts
import { apiRequest } from './api-client';
import { UserStripeCard } from './types';

/**
 * Add a payment method to a user's account
 */
export async function addPaymentMethod(userId: string, paymentMethodId: string) {
  try {
    const response = await apiRequest(
      `/user/${userId}/payment-methods`,
      'POST',
      {
        body: { payment_method_id: paymentMethodId }
      }
    );
    
    return response.payment_info;
  } catch (error) {
    console.error('Error adding payment method:', error);
    throw error;
  }
}

/**
 * Get a user's payment information
 */
export async function getPaymentInfo(userId: string): Promise<UserStripeCard | null> {
  try {
    const response = await apiRequest(`/user/${userId}/payment`);
    return response.payment_info;
  } catch (error) {
    console.error('Error fetching payment info:', error);
    return null;
  }
}

/**
 * Delete a user's payment method
 */
export async function deletePaymentMethod(userId: string) {
  try {
    const response = await apiRequest(
      `/user/${userId}/payment`,
      'DELETE'
    );
    
    return response.success;
  } catch (error) {
    console.error('Error deleting payment method:', error);
    throw error;
  }
}
```

## 5. Payment Component Integration

### 5.1 Create Credit Card Form Component

```typescript
// frontend/src/components/payments/CreditCardForm.tsx
import { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Button } from '@/components/ui/button';

interface CreditCardFormProps {
  onSave: (paymentMethodId: string) => Promise<void>;
  defaultErrorMessage?: string | null;
  userId?: string;
  userEmail?: string;
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
      // Create a Payment Method
      const { error: createError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
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
      
      // Pass the payment method ID to the parent component
      await onSave(paymentMethod.id);
      
      setSuccess(true);
      cardElement.clear();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Card element style
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
      color: '#dc2626',
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
```

### 5.2 Create Saved Card Display Component

```typescript
// frontend/src/components/payments/SavedCardDisplay.tsx
import { CreditCard, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SavedCardDisplayProps {
  last4?: string;
  brand?: string;
  expiryMonth?: string | number;
  expiryYear?: string | number;
  onDelete?: () => void;
  isDeleting?: boolean;
}

export function SavedCardDisplay({ 
  last4 = '••••', 
  brand = 'Card', 
  expiryMonth = '••', 
  expiryYear = '••',
  onDelete,
  isDeleting = false
}: SavedCardDisplayProps) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-md">
      <div className="flex items-center gap-3">
        <CreditCard className="h-6 w-6 text-blue-600" />
        <div>
          <p className="font-medium">
            {brand} •••• {last4}
          </p>
          <p className="text-sm text-gray-500">
            Expires {expiryMonth}/{expiryYear}
          </p>
        </div>
      </div>
      
      {onDelete && (
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={onDelete}
          disabled={isDeleting}
          className="text-gray-500 hover:text-red-600"
        >
          {isDeleting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
          <span className="sr-only">Delete Card</span>
        </Button>
      )}
    </div>
  );
}
```

### 5.3 Create Payment Handler Component

in part 2 and more
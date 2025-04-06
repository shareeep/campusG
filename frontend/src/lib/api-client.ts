/**
 * API client for communicating with backend services
 */
import type { BackendUser } from './types/user';

// Interface for Clerk user data to avoid using 'any'
interface ClerkUser {
  id: string;
  firstName?: string | null;
  lastName?: string | null;
  username?: string | null;
  emailAddresses?: Array<{ emailAddress: string }>;
  phoneNumbers?: Array<{ phoneNumber: string }>;
}

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3001/api';

interface ApiClientOptions {
  headers?: Record<string, string>;
  body?: unknown;
}

/**
 * Generic API request function with error handling
 */
export async function apiRequest<T>(
  endpoint: string, 
  method: string = 'GET', 
  options: ApiClientOptions = {}
): Promise<T> {
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
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Network response was not ok' }));
      throw new Error(errorData.message || `API request failed with status ${response.status}`);
    }
    
    // Parse JSON response
    const data = await response.json();
    
    // Handle API error responses
    if (data && data.success === false) {
      throw new Error(data.message || 'API request failed');
    }
    
    return data as T;
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
    // Add debugging to see what's happening with the API request
    console.log(`Fetching user with Clerk ID: ${clerkUserId}`);
    console.log(`API URL: ${USER_SERVICE_URL}/user/${clerkUserId}`);
    
    const response = await apiRequest<{ user: BackendUser }>(`/user/${clerkUserId}`);
    
    // Log the response and user data we got back in detail
    console.log('Full backend response:', response);
    console.log('Backend user data received:', response.user);
    
    // Deep check for Stripe card data with full object dump
    if (response.user) {
      console.log('Stripe Customer ID (camelCase):', response.user.stripeCustomerId);
      console.log('Stripe Customer ID (snake_case):', response.user.stripe_customer_id);
      console.log('User Stripe Card (camelCase):', response.user.userStripeCard);
      console.log('User Stripe Card (snake_case):', response.user.user_stripe_card);
      
      // Debug log all fields for complete understanding of structure
      console.log('ALL USER FIELDS:', Object.keys(response.user));
      
      // Explicitly log the card details regardless of whether they're found
      console.log('ALL STRIPE CARD FIELDS (camelCase):', response.user.userStripeCard 
        ? Object.keys(response.user.userStripeCard) 
        : 'No userStripeCard found');
        
      console.log('ALL STRIPE CARD FIELDS (snake_case):', response.user.user_stripe_card 
        ? Object.keys(response.user.user_stripe_card) 
        : 'No user_stripe_card found');
        
      // Log the entire card data structure to debug
      console.log('CARD DATA DUMP (camelCase):', JSON.stringify(response.user.userStripeCard));
      console.log('CARD DATA DUMP (snake_case):', JSON.stringify(response.user.user_stripe_card));
    }
    
    return response.user;
  } catch (error) {
    console.error('Error fetching user by Clerk ID:', error);
    return null;
  }
}

/**
 * Save a payment method for a user
 */
export async function savePaymentMethod(clerkUserId: string, paymentMethodId: string): Promise<boolean> {
  try {
    // The backend endpoint is payment-methods (plural), not payment-method (singular)
    console.log(`Saving payment method ${paymentMethodId} for user ${clerkUserId}`);
    const response = await apiRequest<{ success: boolean }>(
      `/user/${clerkUserId}/payment-methods`,
      'POST',
      { 
        body: { 
          payment_method_id: paymentMethodId 
        } 
      }
    );
    console.log('Save payment method response:', response);
    return response.success;
  } catch (error) {
    console.error('Error saving payment method:', error);
    return false;
  }
}

/**
 * Delete a payment method for a user
 */
export async function deletePaymentMethod(clerkUserId: string): Promise<boolean> {
  try {
    console.log(`Deleting payment method for user ${clerkUserId}`);
    const response = await apiRequest<{ success: boolean }>(
      `/user/${clerkUserId}/payment-methods`,
      'DELETE'
    );
    console.log('Delete payment method response:', response);
    return response.success;
  } catch (error) {
    console.error('Error deleting payment method:', error);
    return false;
  }
}

/**
 * Process a payment for an order
 */
export async function processPayment(
  clerkUserId: string, 
  orderId: string, 
  amount: number
): Promise<{ success: boolean; requires_action?: boolean; client_secret?: string; error?: string }> {
  try {
    const response = await apiRequest<{
      success: boolean;
      requires_action?: boolean;
      client_secret?: string;
      error?: string;
    }>(
      `/payment/process`,
      'POST',
      {
        body: {
          clerk_user_id: clerkUserId,
          order_id: orderId,
          amount
        }
      }
    );
    return response;
  } catch (error) {
    console.error('Error processing payment:', error);
    return { 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown payment error' 
    };
  }
}

/**
 * Create a new user in the backend based on Clerk user data
 */
export async function createUserFromClerk(clerkUser: ClerkUser): Promise<BackendUser | null> {
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
    
    const response = await apiRequest<{ user: BackendUser, success: boolean }>(
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
export async function updateUserFromClerk(clerkUserId: string, clerkUser: ClerkUser): Promise<BackendUser | null> {
  try {
    // First get the current user data to preserve fields we don't want to overwrite
    const currentUser = await getUserByClerkId(clerkUserId);
    
    // Extract primary email
    const email = clerkUser.emailAddresses?.[0]?.emailAddress || '';
    
    // Extract phone if available
    const phone = clerkUser.phoneNumbers?.[0]?.phoneNumber || '';
    
    const userData = {
      clerk_user_id: clerkUserId,
      email,
      first_name: clerkUser.firstName || '',
      last_name: clerkUser.lastName || '',
      phone_number: phone,
      username: clerkUser.username || email.split('@')[0],
      // Add a flag to indicate this is just a profile update, not a full user update
      // This helps the backend know to preserve payment data
      profile_update_only: true
    };
    
    console.log('Updating user with data:', userData);
    console.log('Current user data before update:', currentUser);
    
    // Use the sync-from-frontend endpoint which supports POST for both creating and updating users
    const response = await apiRequest<{ user: BackendUser, success: boolean }>(
      `/user/sync-from-frontend`,
      'POST',
      { body: userData }
    );
    
    // Verify that card data is still present
    console.log('Updated user response:', response);
    console.log('Card data after update:', response.user.userStripeCard || response.user.user_stripe_card);
    
    return response.user;
  } catch (error) {
    console.error('Error updating user from Clerk data:', error);
    return null;
  }
}

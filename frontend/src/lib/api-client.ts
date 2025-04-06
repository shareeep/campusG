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
    const response = await apiRequest<{ user: BackendUser }>(`/user/${clerkUserId}`);
    return response.user;
  } catch (error) {
    console.error('Error fetching user by Clerk ID:', error);
    return null;
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
    };
    
    // Use the sync-from-frontend endpoint which supports POST for both creating and updating users
    const response = await apiRequest<{ user: BackendUser, success: boolean }>(
      `/user/sync-from-frontend`,
      'POST',
      { body: userData }
    );
    
    return response.user;
  } catch (error) {
    console.error('Error updating user from Clerk data:', error);
    return null;
  }
}

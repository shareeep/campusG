/**
 * API client for communicating with backend services
 */
import { BackendUser } from './types';

interface ApiClientOptions {
  headers?: Record<string, string>;
  body?: unknown;
}

/**
 * Generic API request function with authentication
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
      : `/api${endpoint}`;

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
    const response = await apiRequest(
      `http://localhost:3001/api/user/${clerkUserId}`
    );
    return response.user;
  } catch (error) {
    console.error('Error fetching user by Clerk ID:', error);
    return null;
  }
}

/**
 * Check if a user exists by Clerk ID and create if not
 * Note: This requires the webhook to be properly set up
 * This is a fallback in case the webhook fails
 */
export async function ensureUserExists(clerkUser: { id: string }): Promise<BackendUser | null> {
  try {
    // First try to get the user
    const user = await getUserByClerkId(clerkUser.id);
    if (user) return user;
    
    // If not found, create the user
    console.log('User not found in backend, waiting for webhook to create user...');
    
    // Return null for now, the user will be created by the webhook
    return null;
  } catch (error) {
    console.error('Error ensuring user exists:', error);
    return null;
  }
}

import { useUser } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';
import { getUserByClerkId } from './api-client';
import { BackendUser } from './types';

/**
 * Custom hook to fetch and manage the user from our backend
 * 
 * This combines Clerk authentication with our backend user data.
 */
export function useBackendUser() {
  const { user: clerkUser, isSignedIn, isLoaded } = useUser();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only attempt to fetch if the user is signed in and Clerk has loaded
    if (!isLoaded || !isSignedIn || !clerkUser) {
      return;
    }
    
    async function fetchBackendUser() {
      setLoading(true);
      setError(null);
      
      try {
        // We already checked for clerkUser above, but TypeScript needs this
        if (!clerkUser) return;
        
        const user = await getUserByClerkId(clerkUser.id);
        setBackendUser(user);
      } catch (err: unknown) {
        console.error('Error fetching backend user:', err);
        // Handle the unknown error type safely
        setError(err instanceof Error ? err.message : 'Failed to fetch user');
      } finally {
        setLoading(false);
      }
    }
    
    fetchBackendUser();
  }, [clerkUser, isSignedIn, isLoaded]);
  
  return { 
    backendUser, 
    clerkUser, 
    loading, 
    error, 
    isLoaded,
    isSignedIn
  };
}

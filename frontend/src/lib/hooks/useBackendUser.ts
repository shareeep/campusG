import { useUser } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';
import { getUserByClerkId, createUserFromClerk, updateUserFromClerk } from '../api-client';
import type { BackendUser } from '../types/user';

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
          user = await updateUserFromClerk(clerkUser.id, clerkUser);
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

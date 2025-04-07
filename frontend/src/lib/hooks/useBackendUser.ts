import { useUser } from '@clerk/clerk-react';
import { useState, useEffect, useRef } from 'react';
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

  // Track sync timeout with a ref
  const syncTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Function to sync user data with timeout protection
  async function syncUser() {
    if (!clerkUser || !isSignedIn) return null;
    
    // If already in a loading state, clear any existing timeout
    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current);
      syncTimeoutRef.current = null;
    }
    
    setLoading(true);
    setSyncState('syncing');
    setError(null);
    
    // Set a timeout to prevent infinite loading state
    syncTimeoutRef.current = setTimeout(() => {
      if (syncState === 'syncing') {
        console.error('Sync operation timed out after 15 seconds');
        setError('Sync operation timed out. Please try again.');
        setSyncState('error');
        setLoading(false);
      }
    }, 15000); // 15 second timeout
    
    console.log("Syncing user data from Clerk to backend...", { clerkUserId: clerkUser.id });
    try {
      // First try to fetch the user
      let user = await getUserByClerkId(clerkUser.id);
      
      // Log user data to debug card info
      console.log('User data from backend before processing:', user);
      console.log('Has Stripe Card:', Boolean(user?.userStripeCard || user?.user_stripe_card));
      
      if (user) {
        // User exists, check if needs updating
        const primaryEmail = clerkUser.emailAddresses?.[0]?.emailAddress || '';
        const primaryPhone = clerkUser.phoneNumbers?.[0]?.phoneNumber || '';
        
        const needsUpdate = 
          user.email !== primaryEmail ||
          user.first_name !== clerkUser.firstName ||
          user.last_name !== clerkUser.lastName ||
          (clerkUser.username && user.username !== clerkUser.username) ||
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
      
      // Reset sync timeout
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
        syncTimeoutRef.current = null;
      }
      
      console.log('Final user data being set in state:', user);
      console.log('Final user card data:', user?.userStripeCard || user?.user_stripe_card);
      
      // Ensure we have a valid user object before updating state
      if (user) {
        setBackendUser(user);
        setSyncState('synced');
        return user;
      } else {
        throw new Error('Backend returned empty user data');
      }
    } catch (err: unknown) {
      console.error('Error syncing with backend:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync user';
      setError(errorMessage);
      setSyncState('error');
      return null;
    } finally {
      // Clean up timeout if it exists
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
        syncTimeoutRef.current = null;
      }
      setLoading(false);
    }
  }
  
  // Sync when auth state changes or when clerk user data changes
  useEffect(() => {
    // Only attempt to fetch if the user is signed in and Clerk has loaded
    if (!isLoaded || !isSignedIn || !clerkUser) {
      return;
    }
    
    // Initial load of user data
    syncUser();
    
    // Cleanup on unmount
    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
        syncTimeoutRef.current = null;
      }
    };
  }, [
    clerkUser, 
    isSignedIn, 
    isLoaded, 
    // Add dependencies to detect user profile changes
    clerkUser?.firstName,
    clerkUser?.lastName,
    clerkUser?.username,
    clerkUser?.primaryEmailAddress?.emailAddress,
    clerkUser?.primaryPhoneNumber?.phoneNumber
  ]);
  
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

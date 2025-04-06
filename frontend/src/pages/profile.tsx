import { useUser, UserProfile } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { User, Mail, Phone, RefreshCw, CreditCard, Plus } from 'lucide-react';
import { useRole } from '@/lib/hooks/use-role';
import { useUserSync } from '@/providers/UserSyncProvider';
import { Button } from '@/components/ui/button';
import { SavedCardDisplay } from '@/components/payments/SavedCardDisplay';
import { CreditCardForm } from '@/components/payments/CreditCardForm';
import { savePaymentMethod, deletePaymentMethod } from '@/lib/api-client';

export function ProfilePage() {
  const { user, isLoaded, isSignedIn } = useUser();
  const navigate = useNavigate();
  const { role } = useRole();
  const { backendUser, syncState, syncUser, loading, error } = useUserSync();
  // Using the direct Clerk user for some operations
  const { user: clerkUser } = useUser();
  const [showAddCard, setShowAddCard] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [cardError, setCardError] = useState<string | null>(null);

  // Helper function to extract card details consistently regardless of format
  const getCardDetail = (field: 'last4' | 'brand' | 'expiryMonth' | 'expiryYear') => {
    const card = backendUser?.userStripeCard || backendUser?.user_stripe_card;
    if (!card) return '••••';
    
    switch (field) {
      case 'last4':
        return card.last4 || card.last_four || '••••';
      case 'brand':
        return card.brand || card.card_type || 'Card';
      case 'expiryMonth':
        return String(card.exp_month || card.expiry_month || '••');
      case 'expiryYear':
        return String(card.exp_year || card.expiry_year || '••');
      default:
        return '••••';
    }
  };

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      navigate('/sign-in');
    }
  }, [isLoaded, isSignedIn, navigate]);

  if (!isLoaded || !user) {
    return (
      <div className="container mx-auto p-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-2">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Profile Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-4 mb-6">
            {user.hasImage ? (
              <img 
                src={user.imageUrl} 
                alt={user.fullName || 'Profile'} 
                className="h-20 w-20 rounded-full object-cover"
              />
            ) : (
              <div className="h-20 w-20 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="h-10 w-10 text-blue-600" />
              </div>
            )}
            <div>
              <h1 className="text-2xl font-bold">{user.fullName}</h1>
              <div className="text-sm text-gray-600 mt-1">
                <div className="flex items-center gap-1">
                  <Mail className="h-4 w-4" />
                  <span>{user.primaryEmailAddress?.emailAddress}</span>
                </div>
                {user.primaryPhoneNumber && (
                  <div className="flex items-center gap-1 mt-1">
                    <Phone className="h-4 w-4" />
                    <span>{user.primaryPhoneNumber.phoneNumber}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Current Role */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-2">Current Role</h2>
            <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              role === 'customer' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
            }`}>
              {role === 'customer' ? 'Customer' : 'Runner'}
            </div>
            <p className="text-sm text-gray-600 mt-2">
              You can switch roles anytime from the main navigation.
            </p>
          </div>

          {/* Payment Methods */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Payment Method</h2>
            {!showAddCard && !(backendUser?.userStripeCard || backendUser?.user_stripe_card) && (
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="flex items-center gap-1"
                  onClick={() => setShowAddCard(true)}
                >
                  <Plus className="h-4 w-4" />
                  Add Payment Method
                </Button>
              )}
            </div>
            
            {showAddCard ? (
              <div className="mb-4">
                <CreditCardForm 
                  onSave={async (paymentMethodId) => {
                    if (!clerkUser?.id) return;
                    setCardError(null);
                    try {
                      // Save the payment method
                      console.log('Saving payment method and refreshing user data...');
                      const success = await savePaymentMethod(clerkUser.id, paymentMethodId);
                      
                      // Force a delay before updating UI to allow backend to finish processing
                      await new Promise(resolve => setTimeout(resolve, 1000));
                      
                      if (success) {
                        setShowAddCard(false);
                        // Refresh backend user data
                        await syncUser();
                        console.log('User data refreshed after save');
                      } else {
                        setCardError('Failed to save payment method');
                      }
                    } catch (err) {
                      setCardError('An error occurred while saving your card');
                      console.error(err);
                    }
                  }}
                  defaultErrorMessage={cardError}
                  userEmail={user.primaryEmailAddress?.emailAddress}
                />
              </div>
            ) : backendUser && (backendUser.userStripeCard || backendUser.user_stripe_card) ? (
              <div className="mb-4">
                <SavedCardDisplay 
                  last4={getCardDetail('last4')}
                  brand={getCardDetail('brand')}
                  expiryMonth={getCardDetail('expiryMonth')}
                  expiryYear={getCardDetail('expiryYear')}
                  onDelete={async () => {
                    if (!clerkUser?.id) return;
                    setIsDeleting(true);
                    try {
                      const success = await deletePaymentMethod(clerkUser.id);
                      if (success) {
                        // Refresh backend user data
                        syncUser();
                      } else {
                        setCardError('Failed to delete payment method');
                      }
                    } catch (err) {
                      setCardError('An error occurred while deleting your card');
                      console.error(err);
                    } finally {
                      setIsDeleting(false);
                    }
                  }}
                  isDeleting={isDeleting}
                />
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500 border rounded-md mb-4">
                <CreditCard className="h-10 w-10 mx-auto mb-2 text-gray-400" />
                <p>No payment methods saved</p>
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="mt-3 flex items-center gap-1 mx-auto"
                  onClick={() => setShowAddCard(true)}
                >
                  <Plus className="h-4 w-4" />
                  Add Payment Method
                </Button>
              </div>
            )}
            
            {cardError && (
              <div className="mb-4 rounded-md bg-red-50 p-3">
                <div className="flex">
                  <div className="text-sm text-red-700">{cardError}</div>
                </div>
              </div>
            )}
          </div>

          {/* Account Management */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-3">Account Management</h2>
            <div className="flex flex-wrap gap-2">
              <UserProfile />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Changes made here will be synchronized with our backend services.
            </p>
          </div>
          
          {/* Backend Sync Status - Moved below Account Management */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Backend Sync Status</h2>
              <Button 
                variant="secondary" 
                size="sm" 
                onClick={() => syncUser()} 
                disabled={loading}
                className="flex items-center gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Sync Now
              </Button>
            </div>
            <div className="mt-2 p-3 bg-gray-50 rounded-md">
              <div className="text-sm flex items-center">
                <span className="font-medium">Status:</span>
                <span className="ml-2">
                  {syncState === 'synced' && (
                    <span className="text-green-600">Synced with backend</span>
                  )}
                  {syncState === 'syncing' && (
                    <span className="text-blue-600">Syncing...</span>
                  )}
                  {syncState === 'error' && (
                    <span className="text-red-600">Sync error</span>
                  )}
                  {syncState === 'idle' && (
                    <span className="text-gray-600">Waiting to sync</span>
                  )}
                </span>
              </div>
              {backendUser && (
                <div className="mt-2 text-xs text-gray-600">
                  <p>Backend data reflects: {backendUser.first_name} {backendUser.last_name} ({backendUser.email})</p>
                </div>
              )}
            </div>
          </div>
          
          {/* Debug Information - Simplified */}
          <details className="p-3 border rounded-md mb-4 text-xs bg-gray-50">
            <summary className="font-semibold cursor-pointer">Debug Information</summary>
            <div className="mt-2">
              <p>Stripe Customer ID: {backendUser?.stripeCustomerId || backendUser?.stripe_customer_id || 'Not set'}</p>
              <p>Card Data: {backendUser?.userStripeCard ? JSON.stringify(backendUser.userStripeCard) : 'None'}</p>
              <p>Sync State: {syncState}</p>
              <p>Clerk User ID: {clerkUser?.id || 'Not available'}</p>
              <p>API URL: {import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3001/api'}</p>
              <p>Error: {error || 'None'}</p>
            </div>
            <div className="mt-2 flex gap-2">
              <button 
                className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs"
                onClick={() => {
                  syncUser();
                  console.log('Manual sync triggered');
                }}
              >
                Debug: Force Sync
              </button>
              <button 
                className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs"
                onClick={() => {
                  setCardError(null);
                  console.clear();
                  console.log('Console cleared');
                }}
              >
                Clear Error
              </button>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}

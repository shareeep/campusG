import { useUser, UserProfile } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { 
  User, Mail, Phone, RefreshCw, CreditCard, Plus, 
  DollarSign, AlertCircle, Loader2, // Removed ArrowDownCircle, ArrowUpCircle
  ShoppingBag, Bike // Added new icons
} from 'lucide-react';
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

  // State for Payment History
  interface PaymentHistory {
    totalSpent: number;
    totalEarned: number;
    spentCount: number;
    earnedCount: number;
  }
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistory | null>(null);
  const [historyLoading, setHistoryLoading] = useState<boolean>(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

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

  // Fetch Payment History
  useEffect(() => {
    if (user?.id) {
      const fetchHistory = async () => {
        setHistoryLoading(true);
        setHistoryError(null);
        try {
          // Use the correct port identified from docker-compose.yml
          const response = await fetch(`http://localhost:3003/history/${user.id}`); 
          if (!response.ok) {
             // Try to get error message from backend if available
              let errorMsg = `HTTP error! status: ${response.status}`;
            try {
              const errorData = await response.json();
              errorMsg = errorData.message || errorData.error || errorMsg;
            } catch { // Removed unused jsonError variable
              // Ignore if response is not JSON
            }
            throw new Error(errorMsg);
          }
          const data: PaymentHistory = await response.json();
          setPaymentHistory(data);
        } catch (error: unknown) { // Changed type to unknown
          console.error("Failed to fetch payment history:", error);
          // Type check before accessing message property
          let errorMessage = "Could not load payment history. Please try again later.";
          if (error instanceof Error) {
            errorMessage = error.message || errorMessage;
          }
          setHistoryError(errorMessage);
        } finally {
          setHistoryLoading(false);
        }
      };
      fetchHistory();
    } else {
      // If no user ID, set loading to false and potentially an error or default state
      setHistoryLoading(false);
      // setHistoryError("User ID not available to fetch history."); // Optional: depends on desired UX
    }
  }, [user?.id]); // Dependency array includes user.id

  if (!isLoaded || !user) {
    return (
      <div className="container mx-auto px-2 sm:px-4 md:px-6 py-3 sm:py-6">
        <div className="w-full sm:max-w-4xl mx-auto text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-2">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-2 sm:px-4 md:px-6 py-3 sm:py-6">
      <div className="w-full sm:max-w-4xl mx-auto">
        {/* Profile Header */}
        <div className="bg-white rounded-lg shadow-sm p-3 sm:p-4 md:p-6 mb-4 sm:mb-6">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 mb-4 sm:mb-6">
            {user.hasImage ? (
              <img 
                src={user.imageUrl} 
                alt={user.fullName || 'Profile'} 
                className="h-16 w-16 sm:h-20 sm:w-20 rounded-full object-cover"
              />
            ) : (
              <div className="h-16 w-16 sm:h-20 sm:w-20 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="h-8 w-8 sm:h-10 sm:w-10 text-blue-600" />
              </div>
            )}
            <div className="text-center sm:text-left mt-2 sm:mt-0">
              <h1 className="text-xl sm:text-2xl font-bold">{user.fullName}</h1>
              <div className="text-sm text-gray-600 mt-1 overflow-hidden">
                <div className="flex items-center gap-1 justify-center sm:justify-start">
                  <Mail className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">{user.primaryEmailAddress?.emailAddress}</span>
                </div>
                {user.primaryPhoneNumber && (
                  <div className="flex items-center gap-1 mt-1 justify-center sm:justify-start">
                    <Phone className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate">{user.primaryPhoneNumber.phoneNumber}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Current Role */}
          <div className="mb-4 sm:mb-6">
            <h2 className="text-base sm:text-lg font-semibold mb-2">Current Role</h2>
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
          <div className="mb-4 sm:mb-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 sm:mb-4 gap-2">
              <h2 className="text-base sm:text-lg font-semibold">Payment Method</h2>
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

          {/* Payment Summary Section */}
          <div className="mb-4 sm:mb-6">
            <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">Transactions Summary</h2>
            {historyLoading ? (
              <div className="flex items-center justify-center p-6 bg-gray-50 rounded-md border">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600 mr-2" />
                <span>Loading payment summary...</span>
              </div>
            ) : historyError ? (
              <div className="flex items-center p-3 bg-red-50 text-red-700 rounded-md border border-red-200">
                <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
                <span>{historyError}</span>
              </div>
            ) : paymentHistory ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {/* Total Spent Card */}
                <div className="bg-white p-3 sm:p-4 rounded-lg border border-gray-200 flex items-center gap-3">
                  {/* Changed color to blue */}
                  <div className="p-2 bg-blue-100 rounded-full"> 
                    <DollarSign className="h-5 w-5 text-blue-600" /> 
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm text-gray-500">Total Spent</p>
                    <p className="text-base sm:text-lg font-semibold">
                      ${paymentHistory.totalSpent.toFixed(2)}
                    </p>
                  </div>
                </div>
                {/* Total Earned Card */}
                <div className="bg-white p-3 sm:p-4 rounded-lg border border-gray-200 flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-full">
                    {/* Changed icon to DollarSign and darker green */}
                    <DollarSign className="h-5 w-5 text-green-700" /> 
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm text-gray-500">Total Earnings</p>
                    <p className="text-base sm:text-lg font-semibold">
                      ${paymentHistory.totalEarned.toFixed(2)}
                    </p>
                  </div>
                </div>
                {/* Payments Made Card */}
                <div className="bg-white p-3 sm:p-4 rounded-lg border border-gray-200 flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-full">
                    {/* Changed icon to ShoppingBag */}
                    <ShoppingBag className="h-5 w-5 text-blue-600" /> 
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm text-gray-500">Orders Placed</p>
                    <p className="text-base sm:text-lg font-semibold">
                      {paymentHistory.spentCount}
                    </p>
                  </div>
                </div>
                {/* Payments Received Card */}
                <div className="bg-white p-3 sm:p-4 rounded-lg border border-gray-200 flex items-center gap-3">
                  {/* Changed color to green */}
                  <div className="p-2 bg-green-100 rounded-full"> 
                    <Bike className="h-5 w-5 text-green-600" /> 
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm text-gray-500">Orders Fulfilled</p>
                    <p className="text-base sm:text-lg font-semibold">
                      {paymentHistory.earnedCount}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
               <div className="text-center p-6 text-gray-500 border rounded-md">
                 No payment history available.
               </div>
            )}
          </div>

          {/* Account Management */}
          <div className="mb-4 sm:mb-6">
            <h2 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">Account Management</h2>
            <div className="w-full rounded-xl overflow-hidden border border-gray-100">
              <div className="w-full transform scale-[0.97] origin-top-left sm:scale-100">
                <UserProfile />
              </div>
            </div>
          </div>
          
          {/* Backend Sync Status - Moved below Account Management */}
          <div className="mb-4 sm:mb-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0">
              <h2 className="text-base sm:text-lg font-semibold">Backend Sync Status</h2>
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
            <div className="mt-2 p-2 sm:p-3 bg-gray-50 rounded-md">
              <div className="text-sm flex flex-wrap items-center">
                <span className="font-medium">Status:</span>
                <span className="ml-2 break-words">
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
                  <p className="break-words">Backend data reflects: {backendUser.first_name} {backendUser.last_name}</p>
                  <p className="truncate">({backendUser.email})</p>
                </div>
              )}
            </div>
          </div>
          
          {/* Debug Information - Simplified */}
          <details className="p-2 sm:p-3 border rounded-md mb-4 text-xs bg-gray-50">
            <summary className="font-semibold cursor-pointer">Debug Information</summary>
            <div className="mt-2 overflow-hidden">
              <p className="break-words">Stripe Customer ID: {backendUser?.stripeCustomerId || backendUser?.stripe_customer_id || 'Not set'}</p>
              <p className="break-words overflow-hidden">Card Data: {backendUser?.userStripeCard ? JSON.stringify(backendUser.userStripeCard).substring(0, 100) + '...' : 'None'}</p>
              <p className="break-words">Sync State: {syncState}</p>
              <p className="break-words">Clerk User ID: {clerkUser?.id || 'Not available'}</p>
              <p className="break-words">API URL: {import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:3001/api'}</p>
              <p className="break-words">Error: {error || 'None'}</p>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
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

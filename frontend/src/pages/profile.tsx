import { useUser, UserProfile } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { User, Mail, Phone, RefreshCw } from 'lucide-react';
import { useRole } from '@/lib/hooks/use-role';
import { useUserSync } from '@/providers/UserSyncProvider';
import { Button } from '@/components/ui/button';

export function ProfilePage() {
  const { user, isLoaded, isSignedIn } = useUser();
  const navigate = useNavigate();
  const { role } = useRole();
  const { backendUser, syncState, syncUser, loading } = useUserSync();

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

          {/* Sync Status */}
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

          {/* Account Management */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Account Management</h2>
            <div className="flex flex-wrap gap-2">
              <UserProfile />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Changes made here will be synchronized with our backend services.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

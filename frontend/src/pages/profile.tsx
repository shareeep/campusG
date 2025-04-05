import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { User, Package, Star, DollarSign, History } from 'lucide-react';
import { getUserProfile, getReviews, getWallet, recalculateUserStats } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import { useRole } from '@/lib/hooks/use-role';
import { ReviewList } from '@/components/reviews/review-list';
import type { UserProfile, Review, Wallet } from '@/lib/types';

export function ProfilePage() {
  const { id: userId } = useUser();
  const { role } = useRole();
  const params = useParams();
  const profileId = params.id || userId;
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const isOwnProfile = profileId === userId;

  useEffect(() => {
    const fetchData = async () => {
      if (!profileId || !role) return;
      
      // First recalculate stats for current role
      if (isOwnProfile) {
        await recalculateUserStats(profileId, role);
      }
      
      // Then fetch updated profile, reviews, and wallet data
      const [profileData, reviewsData, walletData] = await Promise.all([
        getUserProfile(profileId),
        getReviews(profileId),
        isOwnProfile ? getWallet(profileId) : null
      ]);
      
      setProfile(profileData);
      setReviews(reviewsData);
      setWallet(walletData);
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [profileId, role, isOwnProfile]);

  if (!profile) {
    return (
      <div className="container mx-auto p-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-2">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Determine what role's stats to show
  const showRunnerStats = isOwnProfile ? role === 'runner' : profile.roles.includes('runner');
  const showCustomerStats = isOwnProfile ? role === 'customer' : !showRunnerStats;

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Profile Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="h-20 w-20 bg-blue-100 rounded-full flex items-center justify-center">
              <User className="h-10 w-10 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{profile.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm text-gray-600">Contact:</span>
                <a 
                  href={`https://t.me/${profile.telegram}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm"
                >
                  @{profile.telegram}
                </a>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid md:grid-cols-3 gap-4">
            {/* Orders */}
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Package className="h-5 w-5 text-blue-600" />
                <h3 className="font-semibold">
                  {showRunnerStats ? 'Orders Delivered' : 'Orders Placed'}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold">{profile.stats.totalOrders}</p>
                <History className="h-4 w-4 text-gray-500" />
              </div>
            </div>

            {/* Runner Stats */}
            {showRunnerStats && profile.stats.averageRating !== undefined && (
              <>
                <div className="bg-yellow-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Star className="h-5 w-5 text-yellow-600" />
                    <h3 className="font-semibold">Rating</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold">
                      {profile.stats.averageRating.toFixed(1)}
                    </p>
                    <span className="text-sm text-gray-600">
                      ({reviews.length} reviews)
                    </span>
                  </div>
                </div>

                {/* Only show earnings to the runner themselves */}
                {isOwnProfile && wallet && (
                  <div className="bg-green-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="h-5 w-5 text-green-600" />
                      <h3 className="font-semibold">Total Earned</h3>
                    </div>
                    <p className="text-2xl font-bold">
                      ${profile.stats.totalEarned?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                )}
              </>
            )}

            {/* Customer Stats */}
            {showCustomerStats && profile.stats.totalSpent !== undefined && (
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="h-5 w-5 text-green-600" />
                  <h3 className="font-semibold">Total Spent</h3>
                </div>
                <p className="text-2xl font-bold">
                  ${profile.stats.totalSpent.toFixed(2)}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Reviews Section (only shown for runner profiles) */}
        {showRunnerStats && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Reviews</h2>
              {reviews.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                  <span>{profile.stats.averageRating?.toFixed(1)} average rating</span>
                </div>
              )}
            </div>
            <ReviewList reviews={reviews} />
          </div>
        )}

        {/* Transaction History (only shown to profile owner) */}
        {isOwnProfile && wallet && wallet.transactions.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6 mt-6">
            <h2 className="text-xl font-semibold mb-6">Transaction History</h2>
            <div className="space-y-4">
              {wallet.transactions
                .filter(t => role === 'customer' ? t.type === 'payment' : t.type === 'earning')
                .map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div>
                      <p className="font-medium">
                        {transaction.type === 'earning' ? 'Delivery Earning' : 'Order Payment'}
                      </p>
                      <p className="text-sm text-gray-600">
                        Order #{transaction.order_id}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(transaction.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className={`
                      font-semibold
                      ${transaction.type === 'earning' ? 'text-green-600' : 'text-red-600'}
                    `}>
                      {transaction.type === 'earning' ? '+' : '-'}
                      ${transaction.amount.toFixed(2)}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
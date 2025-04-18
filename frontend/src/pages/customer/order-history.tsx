import { useState, useEffect } from "react"; // Removed unused useCallback
import { Link } from "react-router-dom";
import { Clock, Search, ChevronDown, Store, MapPin, User } from "lucide-react"; // Added Store, MapPin, User icons
import { useAuth } from "@clerk/clerk-react"; // Import useAuth
// Removed unused Button import
import { Input } from '@/components/ui/input';
import { getUserDetails } from '@/lib/api'; // Import getUserDetails
// Removed unused getUserOrders import
// Removed unused useUser import

// Define Order type based on backend to_dict()
interface BackendOrder {
  orderId: string;
  custId: string;
  runnerId: string | null;
  orderDescription: string; // JSON string of items
  foodFee: number;
  deliveryFee: number;
  deliveryLocation: string;
  orderStatus: keyof typeof OrderStatusEnum; // Use keys of the enum map below
  sagaId: string | null;
  createdAt: string; // ISO string
  updatedAt: string; // ISO string
  completedAt: string | null; // ISO string or null
  storeLocation?: string; // Added optional store location
  // Removed 'review' field as it's not provided by the backend endpoint
}

// Map backend status strings for consistency if needed, or use directly
// Using an enum-like object for status keys used in the component
const OrderStatusEnum = {
  PENDING: "PENDING",
  CREATED: "CREATED",
  ACCEPTED: "ACCEPTED",
  PLACED: "PLACED",
  ON_THE_WAY: "ON_THE_WAY",
  DELIVERED: "DELIVERED",
  COMPLETED: "COMPLETED",
  CANCELLED: "CANCELLED",
} as const;


export function OrderHistoryPage() {
  const { userId, getToken } = useAuth(); // Use Clerk's useAuth
  const [searchTerm, setSearchTerm] = useState('');
  // Use keys of OrderStatusEnum for status filter type
  const [statusFilter, setStatusFilter] = useState<keyof typeof OrderStatusEnum | null>(null);
  const [orders, setOrders] = useState<BackendOrder[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runnerNames, setRunnerNames] = useState<Record<string, string>>({}); // State for runner names

  // Fetch orders using the new endpoint and Clerk auth
  const fetchOrders = async () => {
    if (!userId) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch(`http://localhost:3002/orders/customer/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch orders: ${response.statusText}`);
      }
      const data = await response.json();
      // Assuming the API returns { items: [], total: number, ... }
      setOrders(data.items || []);
    } catch (err) { // Use default error type
      const message = err instanceof Error ? err.message : 'An error occurred while fetching orders.';
      setError(message);
      console.error("Fetch orders error:", err);
    } finally {
      setIsLoading(false);
    }
  };


  useEffect(() => {
    fetchOrders(); // Initial fetch

    // Start polling every 10 seconds
    const intervalId = setInterval(fetchOrders, 10000); 

    // Cleanup function to clear the interval when the component unmounts
    return () => {
      clearInterval(intervalId);
      console.log("[OrderHistoryPage] Cleanup: Cleared interval polling.");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]); // Removed getToken from deps as fetchOrders doesn't directly use it, but relies on it being stable from useAuth

  // Effect to fetch runner names when orders change
  useEffect(() => {
    const fetchRunnerNames = async () => {
      if (!orders.length || !getToken) return;

      const token = await getToken();
      if (!token) return; // Need token to fetch

      const runnerIdsToFetch = orders
        .map(order => order.runnerId)
        .filter((id): id is string => !!id && !runnerNames[id]); // Filter out null/undefined and already fetched IDs

      if (!runnerIdsToFetch.length) return;

      // Create a unique set of IDs to avoid redundant fetches
      const uniqueRunnerIds = [...new Set(runnerIdsToFetch)];

      console.log("[OrderHistoryPage] Fetching names for runner IDs:", uniqueRunnerIds);

      const namePromises = uniqueRunnerIds.map(async (runnerId) => {
        try {
          const details = await getUserDetails(runnerId, token);
          // Prioritize username, fallback to first name, then ID snippet
          const name = details?.username || details?.firstName || `Runner (${runnerId.substring(0, 6)}...)`;
          return { id: runnerId, name };
        } catch (err) {
          console.error(`[OrderHistoryPage] Error fetching name for runner ${runnerId}:`, err);
          return { id: runnerId, name: `Runner (${runnerId.substring(0, 6)}...)` }; // Fallback on error
        }
      });

      const fetchedNames = await Promise.all(namePromises);

      setRunnerNames(prevNames => {
        const newNames = { ...prevNames };
        fetchedNames.forEach(({ id, name }) => {
          newNames[id] = name;
        });
        return newNames;
      });
    };

    fetchRunnerNames();
  }, [orders, getToken, runnerNames]); // Depend on orders, getToken, and runnerNames map itself

  // Update filtering logic
  const filteredOrders = orders.filter(order => {
    // Basic search on order ID or description (if needed)
    const searchLower = searchTerm.toLowerCase();
    // Try parsing description for item names if needed, otherwise search ID
    let descriptionMatch = false;
    try {
        // Attempt to parse, provide type hint for items if possible
        const items: Array<{ name?: string }> = JSON.parse(order.orderDescription);
        descriptionMatch = items.some((item) => item.name?.toLowerCase().includes(searchLower));
    } catch { // Removed unused 'e' variable
        // Log parsing error if needed, otherwise ignore
        // console.warn("Could not parse orderDescription:", order.orderDescription);
    }
    const matchesSearch = order.orderId.toLowerCase().includes(searchLower) || descriptionMatch;

    const matchesStatus = !statusFilter || order.orderStatus === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Update getStatusColor to use backend OrderStatus enum values
  const getStatusColor = (status: keyof typeof OrderStatusEnum) => {
    switch (status) {
      case 'COMPLETED': return 'bg-green-100 text-green-700';
      case 'DELIVERED': return 'bg-blue-100 text-blue-700';
      case 'ON_THE_WAY': return 'bg-yellow-100 text-yellow-700'; // Assuming ON_THE_WAY replaces picked_up
      case 'PLACED': return 'bg-purple-100 text-purple-700'; // Assuming PLACED replaces order_placed
      case 'ACCEPTED': return 'bg-indigo-100 text-indigo-700'; // Assuming ACCEPTED replaces runner_assigned
      case 'CREATED': return 'bg-orange-100 text-orange-700';
      case 'PENDING': return 'bg-gray-100 text-gray-700';
      case 'CANCELLED': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Order History</h1>
          <div className="flex gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <Input
                type="text"
                placeholder="Search orders..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="relative">
              <select
                className="appearance-none bg-white border rounded-md px-4 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={statusFilter || ''}
                // Update onChange to use OrderStatusEnum keys
                onChange={(e) => setStatusFilter(e.target.value as keyof typeof OrderStatusEnum || null)}
              >
                <option value="">All Status</option>
                {/* Map over OrderStatusEnum keys for options */}
                {Object.keys(OrderStatusEnum).map(statusKey => (
                  <option key={statusKey} value={statusKey}>
                    {/* Format status names for display - Replace all underscores */}
                    {statusKey.replace(/_/g, ' ').charAt(0).toUpperCase() + statusKey.replace(/_/g, ' ').slice(1).toLowerCase()}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Loading and Error States */}
        {isLoading && <div className="p-8 text-center">Loading orders...</div>}
        {error && <div className="p-8 text-center text-red-600">Error: {error}</div>}

        <div className="bg-white rounded-lg shadow-sm">
          {!isLoading && !error && filteredOrders.map((order) => (
            <div
              key={order.orderId} // Use orderId as key
              className="border-b last:border-b-0 p-6 hover:bg-gray-50 transition-colors duration-150" // Add hover effect
            >
              {/* Wrap content in Link for clickability */}
              <Link to={`/customer/order/${order.orderId}/tracking`} className="block">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="text-lg font-semibold">Order #{order.orderId.substring(0, 8)}</h3> {/* Shorten ID */}
                    <p className="text-sm text-gray-600">
                      {new Date(order.createdAt).toLocaleDateString()} at{' '}
                      {new Date(order.createdAt).toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(order.orderStatus)}`}>
                      {order.orderStatus === "ON_THE_WAY" && ( // Check for ON_THE_WAY
                        <Clock className="inline-block h-4 w-4 mr-1" />
                      )}
                      {/* Format status name properly */}
                      {order.orderStatus
                        .toLowerCase()
                        .split('_')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ')}
                    </span>
                  </div>
                </div>
                {/* Add Store and Delivery Location */}
                <div className="mt-3 text-sm text-gray-600 space-y-1">
                  {order.storeLocation && (
                    <div className="flex items-center">
                      <Store className="h-4 w-4 mr-2 flex-shrink-0 text-gray-500" />
                      <span>Pickup: {order.storeLocation}</span>
                    </div>
                  )}
                  <div className="flex items-center">
                     <MapPin className="h-4 w-4 mr-2 flex-shrink-0 text-gray-500" />
                     <span>Delivery: {order.deliveryLocation}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3"> {/* Added mt-3 */}
                  <div>
                    {/* Display Runner Info */}
                    {order.runnerId && (
                      <div className="flex items-center text-sm text-gray-500 mt-1">
                        <User className="h-4 w-4 mr-1 flex-shrink-0" />
                        <span>
                          {runnerNames[order.runnerId] ? `Runner: ${runnerNames[order.runnerId]}` : 'Runner Accepted'}
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="font-semibold">
                    ${(order.foodFee + order.deliveryFee).toFixed(2)} {/* Calculate total */}
                  </p>
                </div>
              </Link>
              {/* Review Dialog removed */}
            </div>
          ))}

          {!isLoading && !error && filteredOrders.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg">No orders found</p>
              <p className="mt-2">Try adjusting your search or filters, or place a new order!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

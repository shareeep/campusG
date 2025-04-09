import { useState, useEffect, useCallback } from "react"; // Import useCallback
import { Clock, MapPin, Package, History, Loader2, Store, Truck, CheckCircle2, User, LucideIcon } from "lucide-react"; // Added Truck, CheckCircle2, User, LucideIcon
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from '@clerk/clerk-react'; // Use Clerk auth
import { getUserDetails } from "@/lib/api"; // Import getUserDetails
import type { UserDetails } from "@/lib/api"; // Import UserDetails type
// import { OrderLogs } from '@/components/order/order-logs'; // Removed unused import

// Define BackendOrder type matching the order service response
interface BackendOrder {
  orderId: string;
  custId: string;
  runnerId: string | null;
  orderDescription: string; // JSON string of items
  foodFee: number;
  deliveryFee: number;
  deliveryLocation: string;
  orderStatus: OrderStatusType; // Use the type below
  sagaId: string | null;
  createdAt: string; // ISO string
  updatedAt: string; // ISO string
  // Add specific timestamps from backend response
  acceptedAt?: string | null;
  placedAt?: string | null;
  pickedUpAt?: string | null;
  deliveredAt?: string | null;
  completedAt: string | null; // ISO string or null
  cancelledAt?: string | null;
  storeLocation?: string; // Added optional store location
  // Add other fields if needed based on display requirements
  instructions?: string;
}

// Define structure for items expected *within* the parsed orderDescription JSON
interface RawOrderItem {
  item_name?: string; // Use item_name
  quantity?: string | number;
  price?: string | number;
}

// Define structure for parsed items used in rendering
interface ParsedItem {
    name: string;
    quantity: number;
    price: number; // Make price non-optional for calculations, default to 0 if missing/invalid
}

// Define possible backend order statuses directly as a type
type OrderStatusType =
  | "PENDING"
  | "CREATED"
  | "ACCEPTED"
  | "PLACED" // Runner has placed the order at the store
  | "ON_THE_WAY" // Runner has picked up the order
  | "DELIVERED" // Runner has delivered to customer (pending completion)
  | "COMPLETED" // Saga completed, payment released
  | "CANCELLED";

// Define the flow for runner status updates
const runnerStatusFlow: Partial<Record<OrderStatusType, OrderStatusType>> = {
  ACCEPTED: 'PLACED',
  PLACED: 'ON_THE_WAY',
  ON_THE_WAY: 'DELIVERED',
  // DELIVERED triggers the complete saga, not a direct status update
};

// --- Timeline Helper Logic (Adapted from customer page) ---

// Map API status string (uppercase) to internal status keys used in hierarchy
const mapApiStatusRunner = (apiStatus: OrderStatusType): string => {
  switch (apiStatus) {
    case 'PENDING': return 'created'; // Treat PENDING as the initial state
    case 'CREATED': return 'created';
    case 'ACCEPTED': return 'runner_assigned';
    case 'PLACED': return 'order_placed';
    case 'ON_THE_WAY': return 'picked_up';
    case 'DELIVERED': return 'delivered';
    case 'COMPLETED': return 'completed';
    // Add 'CANCELLED' if needed
    default:
      console.warn(`Unknown API status received on runner page: ${apiStatus}`);
      return 'created'; // Fallback
  }
};

// Define status hierarchy using internal keys
const statusHierarchyRunner: string[] = [
  'created',
  'runner_assigned',
  'order_placed',
  'picked_up',
  'delivered',
  'completed'
];

// Get timestamp for a specific status from the BackendOrder object
const getStatusTimeRunner = (order: BackendOrder, targetStatusKey: string): string | null => {
  switch (targetStatusKey) {
    case 'created': return order.createdAt || null;
    case 'runner_assigned': return order.acceptedAt || null;
    case 'order_placed': return order.placedAt || null;
    case 'picked_up': return order.pickedUpAt || null;
    case 'delivered': return order.deliveredAt || null;
    case 'completed': return order.completedAt || null;
    default: return null;
  }
};

// --- End Timeline Helper Logic ---


// Helper function to get status badge colors
const getStatusColor = (status: OrderStatusType): string => {
  switch (status) {
    case 'COMPLETED': return 'bg-green-100 text-green-700';
    case 'DELIVERED': return 'bg-blue-100 text-blue-700';
    case 'ON_THE_WAY': return 'bg-yellow-100 text-yellow-700';
    case 'PLACED': return 'bg-purple-100 text-purple-700';
    case 'ACCEPTED': return 'bg-indigo-100 text-indigo-700';
    case 'CREATED': return 'bg-orange-100 text-orange-700'; // Should not appear here often
    case 'PENDING': return 'bg-gray-100 text-gray-700'; // Should not appear here often
    case 'CANCELLED': return 'bg-red-100 text-red-700';
    default: return 'bg-gray-100 text-gray-700';
  }
};

export function ActiveOrdersPage() {
  const { userId: runnerId, getToken } = useAuth();
  const { toast } = useToast();
  const [allOrders, setAllOrders] = useState<BackendOrder[]>([]);
  const [showCompleted, setShowCompleted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingOrderId, setUpdatingOrderId] = useState<string | null>(null); // Track which order is being updated/completed
  // State to store fetched customer names: { [custId: string]: string }
  const [customerNames, setCustomerNames] = useState<Record<string, string>>({});

  const fetchOrders = useCallback(async () => { // Use useCallback
    if (!runnerId) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch(`http://localhost:3002/orders?runnerId=${runnerId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch runner orders: ${response.statusText}`);
      }
      const data = await response.json();
      // Sort all orders by creation date, newest first
      const sortedOrders = (data.items || []).sort((a: BackendOrder, b: BackendOrder) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setAllOrders(sortedOrders);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred while fetching orders.';
      setError(message);
      console.error('Error fetching orders:', err);
    } finally {
      setIsLoading(false);
    }
  }, [runnerId, getToken]); // Add dependency array for useCallback

  useEffect(() => {
    fetchOrders();
    // Optional: Add polling or switch to WebSocket/SSE
    // const interval = setInterval(fetchOrders, 10000);
    // return () => clearInterval(interval);
  }, [runnerId, getToken]); // Add dependency array

  // Effect to fetch customer names when orders change
  useEffect(() => {
    const fetchCustomerNames = async () => {
      if (!allOrders.length || !getToken) return;

      const token = await getToken();
      if (!token) return; // Need token to fetch user details

      const customerIdsToFetch = allOrders
        .map(order => order.custId)
        .filter((id): id is string => !!id && !customerNames[id]); // Filter out null/undefined and already fetched

      if (!customerIdsToFetch.length) return;

      const uniqueCustomerIds = [...new Set(customerIdsToFetch)];
      const namePromises = uniqueCustomerIds.map(id => getUserDetails(id, token));

      try {
        const results = await Promise.all(namePromises);
        const newNames: Record<string, string> = {};
        // Add types for details and index
        results.forEach((details: UserDetails | null, index: number) => {
          if (details) {
            // Prioritize username, fallback to first name
            const name = details.username || details.firstName || `Customer (${uniqueCustomerIds[index].substring(0, 6)}...)`;
            newNames[uniqueCustomerIds[index]] = name;
          }
        });

        setCustomerNames(prevNames => ({ ...prevNames, ...newNames }));
      } catch (err) {
        console.error("Error fetching customer names:", err);
        // Optionally show a toast or handle error
      }
    };

    fetchCustomerNames();
  }, [allOrders, getToken, customerNames]); // Depend on allOrders, getToken, and customerNames


  const handleUpdateStatus = async (order: BackendOrder) => {
    if (!runnerId) return;

    const currentStatus = order.orderStatus;
    const nextStatus = runnerStatusFlow[currentStatus];

    if (!nextStatus) {
      toast({ title: "Info", description: "No further status update available for this order.", variant: "default" });
      return;
    }

    setUpdatingOrderId(order.orderId);
    try {
      const token = await getToken();
      // Call Order Service to update status directly
      const response = await fetch('http://localhost:3002/updateOrderStatus', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ orderId: order.orderId, status: nextStatus })
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || `Failed to update status to ${nextStatus}`);
      }

      // Format status for display (replace underscore, capitalize words)
      const formattedStatus = nextStatus
        .toLowerCase()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

      toast({
        title: "Order Updated",
        description: `Order status updated to ${formattedStatus}`,
      });
      // Refresh local state optimistically or re-fetch
      setAllOrders(prevOrders =>
        prevOrders.map(o =>
          o.orderId === order.orderId ? { ...o, orderStatus: nextStatus } : o
        )
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update order status.';
      toast({ title: "Error", description: message, variant: "destructive" });
      console.error('Error updating status:', err);
    } finally {
      setUpdatingOrderId(null);
    }
  };

  // Function to trigger the Complete Order Saga
  const handleCompleteOrderSaga = async (order: BackendOrder) => {
     if (!runnerId) return;
     setUpdatingOrderId(order.orderId); // Use the same state to show loading

     try {
        const token = await getToken();
        // Call the Complete Order Saga Orchestrator's correct endpoint
        const response = await fetch('http://localhost:3103/triggerCompleteOrderWorkflow', { // Correct Saga endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` // Assuming saga needs auth
            },
            // Saga API expects order_id and clerk_user_id
            body: JSON.stringify({ order_id: order.orderId, clerk_user_id: runnerId })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `Failed to trigger order completion saga.`);
        }

        toast({
            title: "Completion Initiated",
            description: `Order completion process started for order ${order.orderId.substring(0, 8)}`,
        });

        // Wait 5 seconds, refresh data, then switch to the completed orders view
        setTimeout(async () => { // Make the callback async
          await fetchOrders(); // Re-fetch orders to get updated status
          setShowCompleted(true);
          // Update URL parameter as well (will be added in the next step)
        }, 5000); // 5000 milliseconds = 5 seconds

     } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to initiate order completion.';
        toast({ title: "Error", description: message, variant: "destructive" });
        console.error('Error completing order saga:', err);
     } finally {
        setUpdatingOrderId(null);
     }
  };


  // Filter orders based on the toggle
  const activeOrders = allOrders.filter(o => o.orderStatus !== 'COMPLETED' && o.orderStatus !== 'CANCELLED');
  const completedOrders = allOrders.filter(o => o.orderStatus === 'COMPLETED');
  const ordersToDisplay = showCompleted ? completedOrders : activeOrders;

  // Helper function to parse orderDescription safely
  const parseOrderItems = (description: string): ParsedItem[] => {
    try {
      const parsedData = JSON.parse(description);
      if (!Array.isArray(parsedData)) return [];
      // Use RawOrderItem type for mapping and conversion
      return parsedData.map((item: RawOrderItem) => ({
        name: item.item_name || 'Unknown Item', // Map item_name to name
        quantity: Number(item.quantity) || 0, // Convert quantity to number
        price: item.price !== undefined && !isNaN(Number(item.price)) ? Number(item.price) : 0, // Convert price to number, default 0
      }));
    } catch (e) {
      console.error("Failed to parse order description:", description, e);
      return [];
    }
  };

  // Determine button text and action based on status
  const getButtonProps = (order: BackendOrder): { text: string; action: () => void; disabled: boolean } => {
    const currentStatus = order.orderStatus;
    const nextStatus = runnerStatusFlow[currentStatus];
    const isLoading = updatingOrderId === order.orderId;

    if (currentStatus === 'DELIVERED') {
      return {
        text: 'Mark as Complete!',
        action: () => handleCompleteOrderSaga(order),
        disabled: isLoading,
      };
    } else if (nextStatus) {
      // Format the next status for better readability
      const formattedStatus = nextStatus
        .toLowerCase()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      return {
        text: `Mark as ${formattedStatus}`,
        action: () => handleUpdateStatus(order),
        disabled: isLoading,
      };
    } else {
      return {
        text: 'No Action Available',
        action: () => {},
        disabled: true,
      };
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">
            {showCompleted ? 'Completed Orders' : 'Active Orders'}
          </h1>
          <Button
            variant="secondary" // Changed from "outline" to "secondary"
            onClick={() => setShowCompleted(!showCompleted)}
          >
            {showCompleted ? (
              <>
                <Package className="h-4 w-4 mr-2" />
                View Active Orders
              </>
            ) : (
              <>
                <History className="h-4 w-4 mr-2" />
                View Completed Orders
              </>
            )}
          </Button>
        </div>

        {/* Loading and Error States */}
        {isLoading && <div className="text-center p-8">Loading orders...</div>}
        {error && <div className="text-center p-8 text-red-600">Error: {error}</div>}

        <div className="space-y-4">
          {!isLoading && !error && ordersToDisplay.map((order) => {
            const items = parseOrderItems(order.orderDescription);
            const total = order.foodFee + order.deliveryFee;
            const buttonProps = getButtonProps(order);

            return (
              <div key={order.orderId} className="bg-white rounded-lg shadow-sm p-6">
                {/* Order Header */}
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-lg font-semibold mb-1">Order #{order.orderId.substring(0, 8)}</h3>
                    {/* Display Customer Name */}
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <span>Customer:</span>
                      {/* Use fetched name from state, fallback to ID or generic text */}
                      <span className="font-medium">{customerNames[order.custId] || `Customer (${order.custId.substring(0, 6)}...)`}</span>
                      {/* Add contact button if needed, requires fetching customer details */}
                      {/* <a href={`...`} className="text-blue-600 hover:underline flex items-center gap-1">
                        <MessageSquare className="h-4 w-4" /> Contact
                      </a> */}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Accepted {new Date(order.createdAt).toLocaleString()} {/* Adjust if accept time available */}
                    </p>
                  </div>
                  {/* Use getStatusColor helper function for dynamic classes */}
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(order.orderStatus)}`}>
                    {order.orderStatus === 'ON_THE_WAY' && (
                      <Clock className="h-4 w-4 inline-block mr-1" />
                    )}
                    {/* Format status for display */}
                    {order.orderStatus
                      .toLowerCase()
                      .split('_')
                      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                      .join(' ')}
                  </div>
                </div>

                {/* Order Summary */}
                <div className="bg-gray-50 rounded-lg p-6 space-y-6">
                  {/* Store Location */}
                  {order.storeLocation && (
                    <div>
                      <h4 className="font-medium mb-2">Pickup Location (Store):</h4>
                      <div className="flex items-start text-gray-700">
                        <Store className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                        <p>{order.storeLocation}</p>
                      </div>
                    </div>
                  )}

                  {/* Order Items */}
                  <div>
                    <h4 className="font-medium mb-2">Order Items:</h4>
                    {items.length > 0 ? (
                      <div className="space-y-2">
                        {items.map((item, index) => (
                          <div key={index} className="flex justify-between">
                            <span>{item.quantity}x {item.name}</span>
                            {/* Price is now always a number, no need for undefined check */}
                            <span className="text-gray-600">${(item.price * item.quantity).toFixed(2)}</span>
                          </div>
                        ))}
                        <div className="flex justify-between pt-2 border-t text-gray-600">
                          <span>Delivery Fee</span>
                          <span>${order.deliveryFee.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pt-2 border-t font-semibold">
                          <span>Total</span>
                          <span>${total.toFixed(2)}</span>
                        </div>
                      </div>
                    ) : (
                       <p className="text-gray-500 text-sm">Could not load items.</p>
                    )}
                  </div>

                  {/* Delivery Details */}
                  <div>
                    <h4 className="font-medium mb-2">Delivery Details:</h4>
                    <div className="flex items-start text-gray-700">
                      <MapPin className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                      {/* Display raw location string */}
                      <p>{order.deliveryLocation}</p>
                    </div>
                  </div>

                  {/* Special Instructions - Assuming part of description or not available */}
                </div>

                {/* Action Button */}
                {!showCompleted && (
                  <div className="mt-6 pt-6 border-t">
                    <Button
                      onClick={buttonProps.action}
                      className="w-full"
                      disabled={buttonProps.disabled}
                    >
                      {buttonProps.disabled && updatingOrderId === order.orderId ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        buttonProps.text
                      )}
                    </Button>
                  </div>
                )}

                {/* Show Timeline for Completed Orders */}
                {showCompleted && (
                  <div className="mt-6 pt-6 border-t">
                    <h4 className="text-md font-semibold mb-4">Order History</h4>
                    {(() => {
                      // Calculate steps inside the map function to access the specific 'order'
                      const currentMappedStatus = mapApiStatusRunner(order.orderStatus);
                      const currentStatusIndex = statusHierarchyRunner.indexOf(currentMappedStatus);
                      // Define TimelineStep interface locally or import if shared
                      interface TimelineStep {
                        title: string;
                        description: string;
                        icon: LucideIcon;
                        statusKey: string;
                        status: 'completed' | 'pending';
                        time: string | null;
                      }
                      const steps: TimelineStep[] = [
                        { title: 'Order Created', description: 'Order was created', icon: Package, statusKey: 'created' },
                        { title: 'Runner Accepted', description: `You accepted`, icon: User, statusKey: 'runner_assigned' }, // Changed title and description
                        { title: 'Order Placed', description: 'You placed the order', icon: Package, statusKey: 'order_placed' },
                        { title: 'Order Picked Up', description: 'You picked up the order', icon: Truck, statusKey: 'picked_up' },
                        { title: 'Order Delivered', description: 'You delivered the order', icon: CheckCircle2, statusKey: 'delivered' },
                        { title: 'Order Completed', description: 'Order is complete', icon: CheckCircle2, statusKey: 'completed' }
                      ].map(step => ({
                        ...step,
                        status: currentStatusIndex >= statusHierarchyRunner.indexOf(step.statusKey) ? 'completed' : 'pending',
                        time: getStatusTimeRunner(order, step.statusKey)
                      }));

                      return (
                        <div className="relative">
                          <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-gray-200" aria-hidden="true"></div>
                          {steps.map((step, index) => (
                            <div key={index} className="flex items-start mb-8 last:mb-0 relative pl-12">
                              <div className={`
                                absolute left-0 top-0 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center z-10
                                ${step.status === 'completed' ? 'bg-green-500' : 'bg-gray-300 border-2 border-white'}
                              `}>
                                <step.icon className={`h-5 w-5 ${step.status === 'completed' ? 'text-white' : 'text-gray-500'}`} />
                              </div>
                              <div className="ml-4 flex-1 pt-1">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <h3 className={`font-medium ${step.status === 'completed' ? 'text-gray-900' : 'text-gray-500'}`}>
                                      {step.title}
                                    </h3>
                                    <div className="text-sm text-gray-600">{step.description}</div>
                                  </div>
                                  {step.time && (
                                    <span className="text-sm text-gray-500 whitespace-nowrap">
                                      {new Date(step.time).toLocaleString()}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                  </div>
                )}
                {/* Order Logs Removed */}
              </div>
            );
          })}

          {!isLoading && !error && ordersToDisplay.length === 0 && (
            <div className="bg-white rounded-lg shadow-sm p-8 text-center">
              <Package className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium text-gray-900">
                {showCompleted ? 'No Completed Orders' : 'No Active Orders'}
              </h3>
              <p className="mt-2 text-gray-600">
                {showCompleted
                  ? 'You haven\'t completed any orders yet.'
                  : 'You have no active orders.'
                }
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

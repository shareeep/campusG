import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Package, Truck, CheckCircle2, Loader2, User, Ban } from 'lucide-react'; // Added Ban icon for cancel button
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { getOrder, confirmDelivery, cancelSaga } from '@/lib/api'; // Added cancelSaga import
// OrderLogs component seems unused after merge, removing import
// import { OrderLogs } from '@/components/order/order-logs';
// import { useUser } from '@/lib/hooks/use-user'; // useUser might not be needed if userId comes from useAuth
import { useAuth } from '@clerk/clerk-react'; // Import useAuth to get token and userId
// Import ApiOrderResponse from types.ts
import type { OrderItem, OrderStatus, ApiOrderResponse } from '@/lib/types';

// Define structure for items expected *within* the parsed orderDescription JSON
interface RawOrderItem {
  item_name?: string; // Changed from name to item_name
  quantity?: string | number;
  price?: string | number;
}

// Helper function to parse order items safely
const parseOrderItems = (description: string): OrderItem[] => {
  try {
    const parsedData = JSON.parse(description);
    if (!Array.isArray(parsedData)) return [];
    // Use RawOrderItem type for mapping
    return parsedData.map((item: RawOrderItem) => ({
      name: item.item_name || 'Unknown Item', // Changed from item.name to item.item_name
      quantity: Number(item.quantity) || 0,
      price: item.price !== undefined && !isNaN(Number(item.price)) ? Number(item.price) : 0, // Default price to 0 if invalid/missing
    }));
  } catch (e) {
    console.error("Failed to parse order description:", description, e);
    return [];
  }
};

// Helper to map API status string to frontend OrderStatus type used in hierarchy
const mapApiStatus = (apiStatus: string): OrderStatus => {
  const lowerStatus = apiStatus.toLowerCase();
  switch (lowerStatus) {
    // Map API statuses (like PENDING, ACCEPTED, ON_THE_WAY) 
    // to the corresponding OrderStatus type values used in statusHierarchy
    case 'pending': return 'created'; // Treat PENDING as the initial state for the timeline
    case 'created': return 'created';
    case 'accepted': return 'runner_assigned';
    case 'placed': return 'order_placed';
    case 'on_the_way': return 'picked_up'; // Map API's ON_THE_WAY to internal 'picked_up'
    case 'delivered': return 'delivered';
    case 'completed': return 'completed';
    // Add 'cancelled' if it needs representation in the hierarchy/timeline logic
    // case 'cancelled': return 'cancelled'; 
    default: 
      console.warn(`Unknown API status received: ${apiStatus}`);
      return 'created'; // Fallback to initial state
  }
};


export function OrderTrackingPage() {
  const { orderId: routeOrderId } = useParams<{ orderId: string }>(); // Rename to avoid conflict
  const { toast } = useToast(); // Initialize toast for use with confirm/cancel
  const { userId, getToken, isLoaded: isAuthLoaded } = useAuth();
  // Use the API response type for state
  const [orderData, setOrderData] = useState<ApiOrderResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Combined state variables from both branches
  const [isUpdating, setIsUpdating] = useState(false); // For confirm delivery
  const [isCancelling, setIsCancelling] = useState(false); // For cancel order
  const [intervalId, setIntervalId] = useState<NodeJS.Timeout | null>(null); // For polling

  // Define fetchOrder outside useEffect so it can be called from handlers
  const fetchOrder = async (currentIntervalId: NodeJS.Timeout | null) => { 
    if (!isAuthLoaded) return;

    if (!routeOrderId) { // Use renamed param
      console.error("Order Tracking: No orderId found in URL params.");
      setError("Order ID is missing.");
      setIsLoading(false);
      return;
    }

    if (!userId) {
      if (isAuthLoaded) {
         console.error("Order Tracking: User is not authenticated.");
         setError("You must be logged in to view order details.");
         setIsLoading(false);
      }
      return;
    }

    const token = await getToken();
    if (!token) {
      console.error("Order Tracking: Failed to get authentication token.");
      setError("Authentication failed. Please try logging in again.");
      setIsLoading(false);
      return;
    }

    console.log(`[OrderTrackingPage] Fetching order ${routeOrderId} for user ${userId}`);
    if (isLoading || error) {
      setIsLoading(true);
      setError(null);
    }

    try {
      // getOrder now returns ApiOrderResponse | null
      const fetchedData = await getOrder(routeOrderId, token);

      if (fetchedData) {
        console.log(`[OrderTrackingPage] Received order data for ${routeOrderId}:`, fetchedData);
        setOrderData(fetchedData); // Set the raw API data
        setError(null);

        // Stop polling if order is completed or cancelled
        const finalStatuses = ['COMPLETED', 'CANCELLED'];
        if (finalStatuses.includes(fetchedData.orderStatus.toUpperCase()) && currentIntervalId) {
          console.log(`[OrderTrackingPage] Order reached final state (${fetchedData.orderStatus}). Stopping polling.`);
          clearInterval(currentIntervalId);
          setIntervalId(null); // Clear intervalId from state
        }
      } else {
        console.warn(`[OrderTrackingPage] getOrder returned null for ${routeOrderId}. Order might not exist or fetch failed.`);
        if (!orderData) { // Check if we have *any* data yet
           setError(`Could not load details for order #${routeOrderId}. It might not exist or there was a server issue.`);
        }
      }
    } catch (err) {
       console.error(`[OrderTrackingPage] Unexpected error fetching order ${routeOrderId}:`, err);
       setError("An unexpected error occurred while loading the order.");
    } finally {
       setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch when component mounts or dependencies change
    fetchOrder(intervalId); // Pass current intervalId

    // Start polling only if intervalId is not already set
    if (!intervalId) {
      console.log("[OrderTrackingPage] Starting polling...");
      const newIntervalId = setInterval(() => fetchOrder(newIntervalId), 5000); // Poll every 5 seconds
      setIntervalId(newIntervalId); // Store the new interval ID
    }

    // Cleanup function: Clear interval when component unmounts or dependencies change
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
        console.log("[OrderTrackingPage] Cleanup: Cleared interval polling.");
      }
    };
    // Dependencies: Fetch when route/user changes, or auth loads.
    // Include intervalId to ensure cleanup works correctly if it changes.
  }, [routeOrderId, userId, getToken, isAuthLoaded, intervalId]);

  // Handler for cancelling an order
  const handleCancelOrder = async () => {
    if (!orderData || !orderData.sagaId || !userId) {
       toast({
         title: "Error",
         description: "Cannot cancel order. Missing saga ID or user info.",
         variant: "destructive"
       });
       return;
    }

    setIsCancelling(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Authentication token not available.");
      
      // Using cancelSaga which returns {success: boolean, message: string}
      const result = await cancelSaga(orderData.sagaId, token);
      
      if (result.success) {
        toast({
          title: "Order Cancellation Initiated",
          description: result.message || "Your order cancellation has been initiated.",
        });
        
        // Refetch order details immediately to reflect status change
        await fetchOrder(intervalId);
      } else {
        toast({
          title: "Cancellation Failed",
          description: result.message || "Failed to cancel the order. Please try again.",
          variant: "destructive"
        });
      }
    } catch (error) {
       const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
       console.error("Error cancelling order:", error);
       toast({
         title: "Error Cancelling Order",
         description: `Failed to cancel order: ${errorMessage}. Please try again.`,
         variant: "destructive"
       });
    } finally {
       setIsCancelling(false);
    }
  };

  // Handler for confirming delivery
  const handleConfirmDelivery = async () => {
    // Use orderData (API response)
    if (!orderData || !userId) {
       toast({ 
         title: "Error", 
         description: "Cannot confirm delivery. Missing order or user info.", 
         variant: "destructive" 
       });
       return;
    }

    setIsUpdating(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Authentication token not available.");
      
      // Call the confirmDelivery API function - note it expects orderId, userId, and role
      await confirmDelivery(orderData.orderId, userId, 'customer');
      
      toast({
        title: "Delivery Confirmed",
        description: "You have confirmed the delivery.",
      });
      
      // Fetch updated order details immediately
      await fetchOrder(intervalId);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
      console.error("Error confirming delivery:", error);
      toast({
        title: "Error Confirming Delivery",
        description: `Failed to confirm delivery: ${errorMessage}. Please try again.`,
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  // --- Render Logic ---

  if (isLoading || !isAuthLoaded) {
    // Show loading spinner
    return (
      <div className="container mx-auto p-6 flex justify-center items-center min-h-[300px]">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !orderData) { // Show error only if we have no data at all
     return (
      <div className="container mx-auto p-6">
        <div className="max-w-2xl mx-auto text-center py-10 bg-red-50 border border-red-200 rounded-lg">
           <h2 className="text-xl font-semibold text-red-700">Error Loading Order</h2>
           <p className="mt-2 text-red-600">{error}</p>
           <Button variant="secondary" className="mt-4" onClick={() => setIsLoading(true)}>
              Retry
           </Button>
         </div>
       </div>
     );
   }

  // Order Data Loaded State
  if (orderData) {
    // Parse items from description
    const items = parseOrderItems(orderData.orderDescription);
    // Map API status to frontend status
    const currentStatus = mapApiStatus(orderData.orderStatus);
    // Calculate total from API fields
    const total = (orderData.foodFee || 0) + (orderData.deliveryFee || 0);

    // --- Adapt Steps Logic ---

    // Correct statusHierarchy using OrderStatus type values
    const statusHierarchy: OrderStatus[] = [
      'created',
      'runner_assigned',
      'order_placed',
      'picked_up',
      'delivered',
      'completed' // Added 'completed' to the hierarchy
      // 'reviewed' // Not typically shown as a mandatory step in this kind of timeline
    ];
    
    // Calculate currentStatusIndex using the mapped status
    const currentStatusIndex = statusHierarchy.indexOf(currentStatus);

    const getStatusTime = (targetStatus: OrderStatus): string | null => {
      // Use specific timestamps if available, otherwise fallback or return null
      switch (targetStatus) {
        case 'created':
          return orderData.createdAt || null;
        case 'runner_assigned': // Maps to ACCEPTED status
          // Assuming the backend response now includes 'acceptedAt'
          return orderData.acceptedAt || null; 
        case 'order_placed': // Maps to PLACED status
          return orderData.placedAt || null;
        case 'picked_up': // Maps to ON_THE_WAY status
          return orderData.pickedUpAt || null;
        case 'delivered': // Maps to DELIVERED status
          return orderData.deliveredAt || null;
        case 'completed': // Maps to COMPLETED status
          return orderData.completedAt || null;
        // Add cases for other statuses like 'cancelled' if needed on the timeline
        default:
          // Fallback for statuses without specific timestamps or if data is missing
          return null; 
      }
    };

    // Define the steps for the timeline
    const steps = [
      {
        title: 'Order Created',
        description: 'Your order has been created',
        icon: Package,
        // Completed if current status is 'created' or beyond
        status: currentStatusIndex >= statusHierarchy.indexOf('created') ? 'completed' : 'pending',
        time: getStatusTime('created')
      },
      {
        title: 'Runner Accepted', // Changed title
        description: orderData.runnerId ? `Runner ${orderData.runnerId.substring(0, 6)}... accepted` : 'Waiting for runner', // Changed description
        icon: User,
        // Completed if current status is 'runner_assigned' or beyond
        status: currentStatusIndex >= statusHierarchy.indexOf('runner_assigned') ? 'completed' : 'pending',
        time: getStatusTime('runner_assigned')
      },
      {
        title: 'Order Placed',
        description: 'Runner has placed your order',
        icon: Package,
         // Completed if current status is 'order_placed' or beyond
        status: currentStatusIndex >= statusHierarchy.indexOf('order_placed') ? 'completed' : 'pending',
        time: getStatusTime('order_placed')
      },
      {
        title: 'Order Picked Up',
        description: 'Your order is on its way',
        icon: Truck,
         // Completed if current status is 'picked_up' or beyond
        status: currentStatusIndex >= statusHierarchy.indexOf('picked_up') ? 'completed' : 'pending',
        time: getStatusTime('picked_up')
      },
      {
        title: 'Order Delivered',
        // Confirmation status might not be available, simplify description
        description: 'Order marked as delivered',
        icon: CheckCircle2,
        // Make consistent with index check
        status: currentStatusIndex >= statusHierarchy.indexOf('delivered') ? 'completed' : 'pending',
        time: getStatusTime('delivered')
      },
      { // Add the 'completed' step
        title: 'Order Completed',
        description: 'Your order is complete',
        icon: CheckCircle2,
        status: currentStatusIndex >= statusHierarchy.indexOf('completed') ? 'completed' : 'pending',
        time: getStatusTime('completed') // Reverted: Show completed time regardless of delivered time
      }
    ];

    return (
      <div className="container mx-auto p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-sm p-6">
            {/* Use orderData.orderId */}
            <h1 className="text-2xl font-bold mb-6">Order #{orderData.orderId.substring(0, 8)}...</h1>

            {error && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                 Warning: Could not refresh order status. Displaying last known details. ({error})
              </div>
            )}

            {/* Order Summary - Adapt to API response structure */}
            <div className="bg-gray-50 rounded-lg p-6 mb-8">
              <div className="grid gap-6">
                {/* Store Location */}
                {orderData.storeLocation && (
                  <div>
                    <h2 className="font-semibold mb-2">Pickup Location (Store)</h2>
                    <p className="text-gray-700">{orderData.storeLocation}</p>
                  </div>
                )}

                {/* Delivery Location */}
                 <div>
                  <h2 className="font-semibold mb-2">Delivery Location</h2>
                  <p className="text-gray-700">{orderData.deliveryLocation || 'Not specified'}</p>
                 </div>

                {/* Items - Parsed from orderDescription */}
                <div>
                  <h2 className="font-semibold mb-2">Items</h2>
                  <div className="space-y-2">
                    {items.map((item, index) => (
                      <div key={index} className="flex justify-between">
                        <span>{item.quantity}x {item.name}</span>
                        <span>${(item.price * item.quantity).toFixed(2)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between pt-2 border-t text-gray-600">
                      <span>Delivery Fee</span>
                      <span>${Number(orderData.deliveryFee || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between pt-2 border-t font-semibold">
                      <span>Total</span>
                      <span>${total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                {/* Runner Info - Use runnerId if available */}
                {orderData.runnerId && (
                  <div className="pt-4 border-t">
                    <h2 className="font-semibold mb-2">Runner</h2>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <User className="h-5 w-5 text-blue-600" />
                        {/* Link might need adjustment if runner profiles are fetched differently */}
                        <Link
                          to={`/profile/${orderData.runnerId}`}
                          className="text-blue-600 hover:underline"
                        >
                          Runner ID: {orderData.runnerId.substring(0, 8)}...
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Order Timeline - Uses adapted steps */}
            <div className="mb-6">
              {/* Format the displayed order status */}
              <h2 className="text-lg font-semibold mb-4">
                Order Status: {orderData.orderStatus
                                .toLowerCase()
                                .split('_')
                                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                                .join(' ')}
              </h2>
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
            </div>

            {/* Cancel Order Button - Only show when status is CREATED or PENDING and sagaId exists */}
            {(orderData.orderStatus.toUpperCase() === 'CREATED' || orderData.orderStatus.toUpperCase() === 'PENDING') && 
             orderData.sagaId && (
              <div className="mt-8 pt-6 border-t">
                <Button 
                  onClick={handleCancelOrder} 
                  className="w-full bg-red-600 hover:bg-red-700 text-white" 
                  variant="secondary"
                  disabled={isCancelling}
                >
                  {isCancelling ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Cancelling...</>
                  ) : (
                    <><Ban className="mr-2 h-4 w-4" /> Cancel Order</>
                  )}
                </Button>
                <p className="text-sm text-gray-600 text-center mt-2">
                  You can only cancel before a runner accepts your order.
                </p>
              </div>
            )}
            
            {/* Confirm Delivery Button - Show when status is PICKED_UP or DELIVERED */}
            {(orderData.orderStatus.toUpperCase() === 'PICKED_UP' || orderData.orderStatus.toUpperCase() === 'DELIVERED') && (
              <div className="mt-8 pt-6 border-t">
                <Button onClick={handleConfirmDelivery} className="w-full" disabled={isUpdating}>
                  {isUpdating ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Confirming...</>
                  ) : ( 'Confirm Order Received' )}
                </Button>
                <p className="text-sm text-gray-600 text-center mt-2">
                  Click when you've received your order.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Fallback if no data and no error after loading
   return (
     <div className="container mx-auto p-6">
        <div className="max-w-2xl mx-auto text-center py-10">
           <p>No order data available.</p>
        </div>
     </div>
   );
}

import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Package, Truck, CheckCircle2, Loader2, User } from 'lucide-react'; // Removed Clock, MessageSquare
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { getOrder, confirmDelivery } from '@/lib/api'; // getOrder signature changed
import { OrderLogs } from '@/components/order/order-logs';
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

// Helper to map API status string to frontend OrderStatus type
const mapApiStatus = (apiStatus: string): OrderStatus => {
  return apiStatus.toLowerCase() as OrderStatus; // Simple lowercase mapping for now
  // Add more robust mapping if API uses different terms (e.g., PENDING -> created)
};


export function OrderTrackingPage() {
  const { orderId: routeOrderId } = useParams<{ orderId: string }>(); // Rename to avoid conflict
  const { toast } = useToast();
  const { userId, getToken, isLoaded: isAuthLoaded } = useAuth();
  // Use the API response type for state
  const [orderData, setOrderData] = useState<ApiOrderResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    const fetchOrder = async () => {
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

    fetchOrder();
    const intervalId = setInterval(fetchOrder, 10000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [routeOrderId, userId, getToken, isAuthLoaded]); // Dependencies are correct now

  const handleConfirmDelivery = async () => {
    // Use orderData (API response)
    if (!orderData || !userId) {
       toast({ title: "Error", description: "Cannot confirm delivery. Missing order or user info.", variant: "destructive" });
       return;
    }

    setIsUpdating(true);
    try {
      // confirmDelivery likely expects the internal order_id (which is the same as API's orderId)
      await confirmDelivery(orderData.orderId, userId, 'customer');

      toast({
        title: "Delivery Confirmed",
        // Confirmation status might not be directly available in ApiOrderResponse, adjust message
        description: "Delivery confirmed. Waiting for runner if needed.",
        // description: orderData.runner_confirmation === 'confirmed' // This field might not exist
        //   ? "Order completed! Payment has been released to the runner."
        //   : "Waiting for runner to confirm delivery.",
      });

      // Refetch order details after confirmation
      const token = await getToken();
      const updatedData = await getOrder(orderData.orderId, token);
      setOrderData(updatedData); // Update with new raw data
    } catch (error) {
       const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
       toast({
         title: "Error Confirming Delivery",
         description: `Failed to confirm delivery: ${errorMessage}. Please try again.`,
         variant: "destructive"
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
    const getStatusTime = (targetStatus: OrderStatus): string | null => {
      // Use API timestamps based on current mapped status
      if (targetStatus === 'created') return orderData.createdAt || null;

      // For subsequent steps, use updatedAt if the current status is at or beyond the target status
      const statusHierarchy: OrderStatus[] = ['created', 'runner_assigned', 'order_placed', 'picked_up', 'delivered', 'completed', 'reviewed'];
      const currentIndex = statusHierarchy.indexOf(currentStatus);
      const targetIndex = statusHierarchy.indexOf(targetStatus);

      if (currentIndex >= targetIndex) {
        return orderData.updatedAt || null; // Use updatedAt as approximation
      }
      return null;
    };

    const steps = [
      {
        title: 'Order Created',
        description: 'Your order has been created',
        icon: Package,
        status: 'completed', // Always completed if order exists
        time: getStatusTime('created')
      },
      {
        title: 'Runner Assigned',
        // Runner info might not be in this API response, adjust description
        description: orderData.runnerId ? `Runner ${orderData.runnerId.substring(0, 6)}... assigned` : 'Waiting for runner',
        icon: User,
        status: currentStatus === 'created' ? 'pending' : 'completed',
        time: getStatusTime('runner_assigned')
      },
      {
        title: 'Order Placed',
        description: 'Runner has placed your order',
        icon: Package,
        status: ['created', 'runner_assigned'].includes(currentStatus) ? 'pending' : 'completed',
        time: getStatusTime('order_placed')
      },
      {
        title: 'Order Picked Up',
        description: 'Your order is on its way',
        icon: Truck,
        status: ['created', 'runner_assigned', 'order_placed'].includes(currentStatus) ? 'pending' : 'completed',
        time: getStatusTime('picked_up')
      },
      {
        title: 'Order Delivered',
        // Confirmation status might not be available, simplify description
        description: 'Order marked as delivered',
        // description: (
        //   <div className="space-y-1">
        //     <p>Customer: {orderData.customer_confirmation === 'confirmed' ? '✓ Confirmed' : 'Pending'}</p>
        //     <p>Runner: {orderData.runner_confirmation === 'confirmed' ? '✓ Confirmed' : 'Pending'}</p>
        //   </div>
        // ),
        icon: CheckCircle2,
        status: currentStatus === 'completed' || currentStatus === 'delivered' ? 'completed' : 'pending',
        time: getStatusTime('delivered')
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
                {/* Store details are not available in API response */}
                {/* <div> ... Store ... </div> */}

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

                {/* Instructions might not be available */}
                {/* {orderData.instructions && ( ... )} */}

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
                      {/* Contact info might not be available */}
                      {/* <a href={`https://t.me/${orderData.customer_telegram}`} ...> ... </a> */}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Order Timeline - Uses adapted steps */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-4">Order Status: {orderData.orderStatus}</h2>
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

            {/* Confirm Delivery Button - Logic might need adjustment based on available data */}
            {/* Show button if status allows confirmation (e.g., 'DELIVERED' or 'PICKED_UP' from API) */}
            {/* Confirmation status check might need removal if not in API response */}
            {(orderData.orderStatus === 'PICKED_UP' || orderData.orderStatus === 'DELIVERED') &&
             // orderData.customer_confirmation !== 'confirmed' && // Remove if confirmation status not available
             (
              <div className="mt-8 pt-6 border-t">
                <Button onClick={handleConfirmDelivery} className="w-full" disabled={isUpdating}>
                  {isUpdating ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Confirming...</>
                  ) : ( 'Confirm Order Received' )}
                </Button>
                <p className="text-sm text-gray-600 text-center mt-2">
                  Click when you've received your order
                </p>
              </div>
            )}

            {/* Use orderData.orderId */}
            <OrderLogs orderId={orderData.orderId} />
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

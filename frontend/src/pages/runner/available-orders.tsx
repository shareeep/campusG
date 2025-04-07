import { useState, useEffect } from 'react';
// Removed unused useNavigate import
import { MapPin, Package, Loader2 } from 'lucide-react'; // Removed MessageSquare, added Loader2
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { useAuth } from '@clerk/clerk-react'; // Use Clerk auth

// Define BackendOrder type matching the order service response
// (Similar to the one in order-history.tsx)
interface BackendOrder {
  orderId: string;
  custId: string;
  runnerId: string | null;
  orderDescription: string; // JSON string of items
  foodFee: number;
  deliveryFee: number;
  deliveryLocation: string; // Simple string for now, adjust if structured
  orderStatus: string; // Assuming string status from backend
  sagaId: string | null;
  createdAt: string; // ISO string
  updatedAt: string; // ISO string
  completedAt: string | null; // ISO string or null
  // Add other fields if needed based on display requirements
  instructions?: string; // Assuming instructions might be part of orderDescription or separate
}

// Define structure for parsed items from orderDescription
interface ParsedItem {
    name: string;
    quantity: number;
    price?: number; // Price might be optional in description
}


export function AvailableOrdersPage() {
  // Removed unused navigate variable
  const { toast } = useToast();
  const { userId: runnerId, getToken } = useAuth(); // Use Clerk's useAuth
  const [orders, setOrders] = useState<BackendOrder[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acceptingOrderId, setAcceptingOrderId] = useState<string | null>(null); // Track which order is being accepted

  useEffect(() => {
    const fetchOrders = async () => {
      if (!runnerId) return; // Don't fetch if runner isn't logged in
      setIsLoading(true);
      setError(null);
      try {
        const token = await getToken();
        // Fetch orders with status CREATED from order service
        const response = await fetch('http://localhost:3002/orders?status=CREATED', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (!response.ok) {
          throw new Error(`Failed to fetch available orders: ${response.statusText}`);
        }
        const data = await response.json();
        // Sort orders by creation date, newest first
        const sortedOrders = (data.items || []).sort((a: BackendOrder, b: BackendOrder) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
        setOrders(sortedOrders);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'An error occurred while fetching orders.';
        setError(message);
        console.error('Error fetching orders:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrders();
    // Optional: Keep polling or switch to WebSocket/SSE
    // const interval = setInterval(fetchOrders, 10000);
    // return () => clearInterval(interval);
  }, [runnerId, getToken]); // Depend on runnerId and getToken

  const handleAcceptOrder = async (orderId: string) => {
    if (!runnerId) {
        toast({ title: "Error", description: "Runner ID not found. Please log in.", variant: "destructive" });
        return;
    };
    setAcceptingOrderId(orderId); // Set loading state for this specific button

    try {
      const token = await getToken();
      // Call the accept order saga orchestrator with the correct prefixed path
      const response = await fetch('http://localhost:3102/saga/accept/acceptOrder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ orderId: orderId, runner_id: runnerId })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `Failed to accept order: ${response.statusText}`);
      }

      toast({
        title: "Order Accepted",
        description: `You've successfully accepted order ${orderId.substring(0, 8)}...`,
      });

      // Remove the accepted order from the local state
      setOrders(prevOrders => prevOrders.filter(o => o.orderId !== orderId));

      // Optionally navigate to active orders page
      // navigate('/runner/active-orders');

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to accept order. Please try again.';
      toast({
        title: "Error Accepting Order",
        description: message,
        variant: "destructive"
      });
      console.error('Error accepting order:', err);
    } finally {
       setAcceptingOrderId(null); // Clear loading state for the button
    }
  };

  // Define structure for items expected *within* the parsed orderDescription JSON
  interface RawOrderItem {
    name?: string;
    quantity?: string | number;
    price?: string | number;
  }

   // Helper function to parse orderDescription safely and ensure price is a number
  const parseOrderItems = (description: string): ParsedItem[] => {
    try {
      const parsedData = JSON.parse(description);
      // Ensure it's an array before mapping
      if (!Array.isArray(parsedData)) {
         console.error("Parsed order description is not an array:", parsedData);
         return [];
      }
      // Map and ensure price is a number or undefined
      return parsedData.map((item: RawOrderItem) => ({ // Use RawOrderItem type here
        name: item.name || 'Unknown Item', // Provide default name
        quantity: Number(item.quantity) || 0, // Ensure quantity is a number
        // Explicitly convert price to number, handle non-numeric values
        price: item.price !== undefined && !isNaN(Number(item.price))
                 ? Number(item.price)
                 : undefined,
      }));
    } catch (e) {
      console.error("Failed to parse order description:", description, e);
      return []; // Return empty array on error
    }
  };


  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Available Orders</h1>

        {/* Loading and Error States */}
        {isLoading && <div className="text-center p-8">Loading available orders...</div>}
        {error && <div className="text-center p-8 text-red-600">Error: {error}</div>}

        {!isLoading && !error && orders.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
            <Package className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-medium text-gray-900">No Available Orders</h3>
            <p className="mt-2 text-gray-600">
              Check back soon for new delivery opportunities
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {!isLoading && !error && orders.map((order) => {
              const items = parseOrderItems(order.orderDescription);
              const total = order.foodFee + order.deliveryFee;

              return (
                <div key={order.orderId} className="bg-white p-6 rounded-lg shadow-sm">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold">Order #{order.orderId.substring(0, 8)}...</h3>
                      {/* Customer details might need fetching from user service if required */}
                      {/* <div className="flex items-center gap-2 text-sm text-gray-600">
                        <span>Customer ID:</span>
                        <span className="font-medium">{order.custId.substring(0, 8)}...</span>
                      </div> */}
                      <p className="text-sm text-gray-500 mt-1">
                        Posted {new Date(order.createdAt).toLocaleString()}
                      </p>
                    </div>
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                      ${total.toFixed(2)}
                    </span>
                  </div>

                  {/* Removed Store details as not directly available */}

                  <div className="mb-4">
                    <h4 className="font-medium mb-2">Order Items:</h4>
                    {items.length > 0 ? (
                      <ul className="list-disc list-inside text-gray-600">
                        {items.map((item, index) => (
                          <li key={index}>
                            {item.quantity}x {item.name}
                            {/* Display price if available */}
                            {item.price !== undefined ? ` ($${item.price.toFixed(2)} each)` : ''}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-500 text-sm">Could not load items.</p>
                    )}
                  </div>

                  <div className="mb-4">
                    <h4 className="font-medium mb-2">Delivery Location:</h4>
                    <div className="flex items-start text-gray-600">
                      <MapPin className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                      {/* Display raw location string, needs parsing/formatting if structured */}
                      <p>{order.deliveryLocation}</p>
                    </div>
                  </div>

                  {/* Assuming instructions are part of orderDescription or need separate handling */}
                  {/* {order.instructions && (
                    <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                      <h4 className="font-medium mb-2">Special Instructions:</h4>
                      <p className="text-gray-600">{order.instructions}</p>
                    </div>
                  )} */}

                  <Button
                    onClick={() => handleAcceptOrder(order.orderId)}
                    className="w-full"
                    disabled={acceptingOrderId === order.orderId} // Disable button while accepting this order
                  >
                    {acceptingOrderId === order.orderId ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Accepting...
                      </>
                    ) : (
                      `Accept Order (${order.deliveryFee.toFixed(2)} delivery fee)`
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

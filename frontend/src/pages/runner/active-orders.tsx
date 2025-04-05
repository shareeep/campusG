import { useState, useEffect } from 'react';
import { Clock, MapPin, Package, History, Loader2, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { getActiveOrders, getCompletedOrders, updateOrderStatus, confirmDelivery } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import { OrderLogs } from '@/components/order/order-logs';
import type { Order, OrderStatus } from '@/lib/types';

export function ActiveOrdersPage() {
  const { id: runnerId } = useUser();
  const { toast } = useToast();
  const [activeOrders, setActiveOrders] = useState<Order[]>([]);
  const [completedOrders, setCompletedOrders] = useState<Order[]>([]);
  const [showCompleted, setShowCompleted] = useState(false);
  const [isUpdating, setIsUpdating] = useState<string | null>(null);

  useEffect(() => {
    const fetchOrders = async () => {
      if (!runnerId) return;
      const [active, completed] = await Promise.all([
        getActiveOrders(runnerId),
        getCompletedOrders(runnerId)
      ]);
      setActiveOrders(active);
      setCompletedOrders(completed);
    };

    fetchOrders();
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, [runnerId]);

  const handleUpdateStatus = async (orderId: string, newStatus: OrderStatus) => {
    if (!runnerId) return;
    setIsUpdating(orderId);

    try {
      if (newStatus === 'delivered') {
        await confirmDelivery(orderId, runnerId, 'runner');
        toast({
          title: "Delivery Confirmed",
          description: "Waiting for customer to confirm delivery.",
        });
      } else {
        await updateOrderStatus(orderId, newStatus);
        toast({
          title: "Order Updated",
          description: `Order status updated to ${newStatus.replace('_', ' ')}`,
        });
      }

      // Refresh orders
      const [active, completed] = await Promise.all([
        getActiveOrders(runnerId),
        getCompletedOrders(runnerId)
      ]);
      setActiveOrders(active);
      setCompletedOrders(completed);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update order status",
        variant: "destructive"
      });
    } finally {
      setIsUpdating(null);
    }
  };

  const getNextStatus = (currentStatus: OrderStatus): OrderStatus | null => {
    const statusFlow = {
      'runner_assigned': 'order_placed',
      'order_placed': 'picked_up',
      'picked_up': 'delivered'
    } as const;
    return statusFlow[currentStatus as keyof typeof statusFlow] || null;
  };

  const getStatusButtonText = (status: OrderStatus): string => {
    const statusTexts = {
      'runner_assigned': 'Mark as Order Placed',
      'order_placed': 'Mark as Order Picked Up',
      'picked_up': 'Mark as Delivered',
      'delivered': 'Waiting for Customer'
    } as const;
    return statusTexts[status] || 'Update Status';
  };

  const orders = showCompleted ? completedOrders : activeOrders;

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">
            {showCompleted ? 'Completed Orders' : 'Active Orders'}
          </h1>
          <Button
            variant="outline"
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

        <div className="space-y-4">
          {orders.map((order) => (
            <div key={order.id} className="bg-white rounded-lg shadow-sm p-6">
              {/* Order Header */}
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-lg font-semibold mb-1">Order #{order.order_id}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span>Customer:</span>
                    <span className="font-medium">{order.customer_name}</span>
                    <a 
                      href={`https://t.me/${order.customer_telegram}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline flex items-center gap-1"
                    >
                      <MessageSquare className="h-4 w-4" />
                      Contact on Telegram
                    </a>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Accepted {new Date(order.created_at!).toLocaleString()}
                  </p>
                </div>
                <div className={`px-3 py-1 rounded-full text-sm ${
                  order.status === 'picked_up'
                    ? 'bg-yellow-100 text-yellow-700'
                    : order.status === 'delivered'
                    ? 'bg-blue-100 text-blue-700'
                    : order.status === 'completed'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {order.status === 'picked_up' && (
                    <Clock className="h-4 w-4 inline-block mr-1" />
                  )}
                  {order.status.replace('_', ' ').charAt(0).toUpperCase() + 
                   order.status.replace('_', ' ').slice(1)}
                </div>
              </div>

              {/* Order Summary */}
              <div className="bg-gray-50 rounded-lg p-6 space-y-6">
                {/* Store Details */}
                <div>
                  <h4 className="font-medium mb-2">Store Details:</h4>
                  <div className="text-gray-700">
                    <p>{order.store.name}</p>
                    <p>Postal Code: {order.store.postalCode}</p>
                  </div>
                </div>

                {/* Order Items */}
                <div>
                  <h4 className="font-medium mb-2">Order Items:</h4>
                  <div className="space-y-2">
                    {order.items.map((item, index) => (
                      <div key={index} className="flex justify-between">
                        <span>{item.quantity}x {item.name}</span>
                        <span className="text-gray-600">${(item.price * item.quantity).toFixed(2)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between pt-2 border-t text-gray-600">
                      <span>Delivery Fee</span>
                      <span>${order.deliveryFee.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between pt-2 border-t font-semibold">
                      <span>Total</span>
                      <span>${order.total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                {/* Delivery Details */}
                <div>
                  <h4 className="font-medium mb-2">Delivery Details:</h4>
                  <div className="flex items-start text-gray-700">
                    <MapPin className="h-5 w-5 mr-2 mt-0.5" />
                    <div>
                      <p>{order.deliveryDetails.school}</p>
                      <p>{order.deliveryDetails.building}, Level {order.deliveryDetails.level}</p>
                      <p>Room {order.deliveryDetails.roomNumber}</p>
                      {order.deliveryDetails.meetingPoint && (
                        <p className="mt-1 text-sm">
                          Meeting point: {order.deliveryDetails.meetingPoint}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Special Instructions */}
                {order.instructions && (
                  <div>
                    <h4 className="font-medium mb-2">Special Instructions:</h4>
                    <p className="text-gray-700">{order.instructions}</p>
                  </div>
                )}
              </div>

              {!showCompleted && (
                <div className="mt-6 pt-6 border-t">
                  {order.status !== 'completed' && (
                    <Button
                      onClick={() => {
                        const nextStatus = getNextStatus(order.status);
                        if (nextStatus) {
                          handleUpdateStatus(order.order_id, nextStatus);
                        }
                      }}
                      className="w-full"
                      disabled={!!isUpdating || !getNextStatus(order.status)}
                    >
                      {isUpdating === order.order_id ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Updating...
                        </>
                      ) : (
                        getStatusButtonText(order.status)
                      )}
                    </Button>
                  )}

                  {order.status === 'delivered' && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                      <h5 className="font-medium mb-2">Delivery Confirmation Status:</h5>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Runner:</span>
                          <span className={order.runner_confirmation === 'confirmed' ? 'text-green-600' : 'text-gray-600'}>
                            {order.runner_confirmation === 'confirmed' ? '✓ Confirmed' : 'Pending'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Customer:</span>
                          <span className={order.customer_confirmation === 'confirmed' ? 'text-green-600' : 'text-gray-600'}>
                            {order.customer_confirmation === 'confirmed' ? '✓ Confirmed' : 'Pending'}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <OrderLogs orderId={order.order_id} />
            </div>
          ))}

          {orders.length === 0 && (
            <div className="bg-white rounded-lg shadow-sm p-8 text-center">
              <Package className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium text-gray-900">
                {showCompleted ? 'No Completed Orders' : 'No Active Orders'}
              </h3>
              <p className="mt-2 text-gray-600">
                {showCompleted 
                  ? 'Complete some deliveries to see them here'
                  : 'Check the available orders page for new delivery opportunities'
                }
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
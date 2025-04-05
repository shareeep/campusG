import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Clock, Package, Truck, CheckCircle2, Loader2, User, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { getOrder, confirmDelivery } from '@/lib/api';
import { OrderLogs } from '@/components/order/order-logs';
import { useUser } from '@/lib/hooks/use-user';
import type { Order } from '@/lib/types';

export function OrderTrackingPage() {
  const { orderId } = useParams();
  const { toast } = useToast();
  const { id: userId } = useUser();
  const [order, setOrder] = useState<Order | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    const fetchOrder = async () => {
      if (!orderId) return;
      const orderData = await getOrder(orderId);
      setOrder(orderData);
    };

    fetchOrder();
    const interval = setInterval(fetchOrder, 5000);
    return () => clearInterval(interval);
  }, [orderId]);

  const handleConfirmDelivery = async () => {
    if (!order || !userId) return;

    setIsUpdating(true);
    try {
      await confirmDelivery(order.order_id, userId, 'customer');
      
      toast({
        title: "Delivery Confirmed",
        description: order.runner_confirmation === 'confirmed' 
          ? "Order completed! Payment has been released to the runner."
          : "Waiting for runner to confirm delivery.",
      });

      const updatedOrder = await getOrder(order.order_id);
      setOrder(updatedOrder);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to confirm delivery. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsUpdating(false);
    }
  };

  if (!order) {
    return (
      <div className="container mx-auto p-6">
        <div className="max-w-2xl mx-auto text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="mt-2">Loading order details...</p>
        </div>
      </div>
    );
  }

  // Get the timestamp for each status based on order logs
  const getStatusTime = (status: string): string | null => {
    switch (status) {
      case 'created':
        return order.created_at || null;
      case 'runner_assigned':
        return order.status === 'runner_assigned' || order.status === 'order_placed' || 
               order.status === 'picked_up' || order.status === 'delivered' || 
               order.status === 'completed'
          ? order.updated_at
          : null;
      case 'order_placed':
        return order.status === 'order_placed' || order.status === 'picked_up' || 
               order.status === 'delivered' || order.status === 'completed'
          ? order.updated_at
          : null;
      case 'picked_up':
        return order.status === 'picked_up' || order.status === 'delivered' || 
               order.status === 'completed'
          ? order.updated_at
          : null;
      case 'delivered':
      case 'completed':
        return (order.status === 'delivered' || order.status === 'completed')
          ? order.updated_at
          : null;
      default:
        return null;
    }
  };

  const steps = [
    {
      title: 'Order Created',
      description: 'Your order has been created',
      icon: Package,
      status: 'completed',
      time: getStatusTime('created')
    },
    {
      title: 'Runner Assigned',
      description: order.runner_name ? (
        <span>
          <Link 
            to={`/profile/${order.runner_id}`} 
            className="text-blue-600 hover:underline"
          >
            {order.runner_name}
          </Link>
          {' '}accepted your order
        </span>
      ) : 'Waiting for runner',
      icon: User,
      status: order.status === 'created' ? 'pending' : 'completed',
      time: getStatusTime('runner_assigned')
    },
    {
      title: 'Order Placed',
      description: 'Runner has placed your order',
      icon: Package,
      status: ['created', 'runner_assigned'].includes(order.status) ? 'pending' : 'completed',
      time: getStatusTime('order_placed')
    },
    {
      title: 'Order Picked Up',
      description: 'Your order is on its way',
      icon: Truck,
      status: ['created', 'runner_assigned', 'order_placed'].includes(order.status) ? 'pending' : 'completed',
      time: getStatusTime('picked_up')
    },
    {
      title: 'Order Delivered',
      description: (
        <div className="space-y-1">
          <p>Customer: {order.customer_confirmation === 'confirmed' ? '✓' : 'Pending'}</p>
          <p>Runner: {order.runner_confirmation === 'confirmed' ? '✓' : 'Pending'}</p>
        </div>
      ),
      icon: CheckCircle2,
      status: order.status === 'completed' ? 'completed' : 'pending',
      time: getStatusTime('delivered')
    }
  ];

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h1 className="text-2xl font-bold mb-6">Order #{order.order_id}</h1>

          {/* Order Summary */}
          <div className="bg-gray-50 rounded-lg p-6 mb-8">
            <div className="grid gap-6">
              <div>
                <h2 className="font-semibold mb-2">Order Summary</h2>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Store:</span>
                    <span className="font-medium">{order.store.name} ({order.store.postalCode})</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Delivery to:</span>
                    <span className="font-medium text-right">
                      {order.deliveryDetails.building}, Level {order.deliveryDetails.level}<br />
                      Room {order.deliveryDetails.roomNumber}, {order.deliveryDetails.school}
                    </span>
                  </div>
                  {order.deliveryDetails.meetingPoint && (
                    <div className="flex justify-between">
                      <span>Meeting Point:</span>
                      <span className="font-medium">{order.deliveryDetails.meetingPoint}</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h2 className="font-semibold mb-2">Items</h2>
                <div className="space-y-2">
                  {order.items.map((item, index) => (
                    <div key={index} className="flex justify-between">
                      <span>{item.quantity}x {item.name}</span>
                      <span>${(item.price * item.quantity).toFixed(2)}</span>
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

              {order.instructions && (
                <div>
                  <h2 className="font-semibold mb-2">Special Instructions</h2>
                  <p className="text-gray-700">{order.instructions}</p>
                </div>
              )}

              {order.runner_name && (
                <div className="pt-4 border-t">
                  <h2 className="font-semibold mb-2">Runner</h2>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <User className="h-5 w-5 text-blue-600" />
                      <Link 
                        to={`/profile/${order.runner_id}`}
                        className="text-blue-600 hover:underline"
                      >
                        {order.runner_name}
                      </Link>
                    </div>
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
                </div>
              )}
            </div>
          </div>

          {/* Order Timeline */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-4">Order Status</h2>
            <div className="relative">
              {steps.map((step, index) => (
                <div key={index} className="flex items-start mb-8 last:mb-0">
                  <div className={`
                    flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                    ${step.status === 'completed' ? 'bg-green-100' : 'bg-gray-100'}
                  `}>
                    <step.icon className={`
                      h-5 w-5
                      ${step.status === 'completed' ? 'text-green-600' : 'text-gray-400'}
                    `} />
                  </div>
                  <div className="ml-4 flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className={`
                          font-medium
                          ${step.status === 'completed' ? 'text-gray-900' : 'text-gray-500'}
                        `}>
                          {step.title}
                        </h3>
                        <div className="text-sm text-gray-600">
                          {typeof step.description === 'string' 
                            ? step.description 
                            : step.description}
                        </div>
                      </div>
                      {step.time && (
                        <span className="text-sm text-gray-500">
                          {new Date(step.time).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {(order.status === 'picked_up' || order.status === 'delivered') && 
           order.customer_confirmation !== 'confirmed' && (
            <div className="mt-8 pt-6 border-t">
              <Button
                onClick={handleConfirmDelivery}
                className="w-full"
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Confirming...
                  </>
                ) : (
                  'Confirm Order Received'
                )}
              </Button>
              <p className="text-sm text-gray-600 text-center mt-2">
                Click when you've received your order
              </p>
            </div>
          )}

          <OrderLogs orderId={order.order_id} />
        </div>
      </div>
    </div>
  );
}
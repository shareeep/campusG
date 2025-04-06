import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Package, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { getAvailableOrders, acceptOrder } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { Order } from '@/lib/types';

export function AvailableOrdersPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { id: runnerId } = useUser();
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const availableOrders = await getAvailableOrders();
        // Sort orders by creation date, newest first
        const sortedOrders = availableOrders.sort((a, b) => 
          new Date(b.created_at!).getTime() - new Date(a.created_at!).getTime()
        );
        setOrders(sortedOrders);
      } catch (error) {
        console.error('Error fetching orders:', error);
      }
    };

    fetchOrders();
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAcceptOrder = async (orderId: string) => {
    if (!runnerId) return;

    try {
      await acceptOrder(orderId, runnerId);
      
      toast({
        title: "Order Accepted",
        description: `You've successfully accepted order ${orderId}`,
      });

      navigate('/runner/active-orders');
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to accept order. Please try again.",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Available Orders</h1>

        {orders.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
            <Package className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-medium text-gray-900">No Available Orders</h3>
            <p className="mt-2 text-gray-600">
              Check back soon for new delivery opportunities
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {orders.map((order) => (
              <div key={order.id} className="bg-white p-6 rounded-lg shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Order #{order.order_id}</h3>
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
                      Posted {new Date(order.created_at!).toLocaleString()}
                    </p>
                  </div>
                  <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                    ${order.total.toFixed(2)}
                  </span>
                </div>

                <div className="mb-4">
                  <h4 className="font-medium mb-2">Store:</h4>
                  <p className="text-gray-600">
                    {order.store.name} ({order.store.postalCode})
                  </p>
                </div>

                <div className="mb-4">
                  <h4 className="font-medium mb-2">Order Items:</h4>
                  <ul className="list-disc list-inside text-gray-600">
                    {order.items.map((item, index) => (
                      <li key={index}>
                        {item.quantity}x {item.name} (${item.price.toFixed(2)} each)
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="font-medium mb-2">Delivery Location:</h4>
                  <div className="flex items-start text-gray-600">
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

                {order.instructions && (
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-2">Special Instructions:</h4>
                    <p className="text-gray-600">{order.instructions}</p>
                  </div>
                )}

                <Button
                  onClick={() => handleAcceptOrder(order.order_id)}
                  className="w-full"
                >
                  Accept Order (${order.deliveryFee.toFixed(2)} delivery fee)
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
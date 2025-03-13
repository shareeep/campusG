import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { formatDistanceToNow } from 'date-fns';

type Order = {
  id: string;
  restaurantName: string;
  customerName: string;
  items: Array<{ name: string; quantity: number }>;
  totalAmount: number;
  createdAt: string;
  deliveryAddress: string;
};

export function AvailableOrdersPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([
    {
      id: '1',
      restaurantName: 'Campus Café',
      customerName: 'John D.',
      items: [
        { name: 'Burger', quantity: 1 },
        { name: 'Fries', quantity: 1 }
      ],
      totalAmount: 15.99,
      createdAt: new Date().toISOString(),
      deliveryAddress: 'Student Center, Room 204'
    },
    // More sample orders...
  ]);

  const handleAcceptOrder = async (orderId: string) => {
    try {
      // TODO: Implement order acceptance
      console.log('Accepting order:', orderId);
      navigate(`/runner/active-order/${orderId}`);
    } catch (error) {
      console.error('Error accepting order:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Available Orders</h1>

      <div className="grid gap-4">
        {orders.map((order) => (
          <div key={order.id} className="bg-white p-4 rounded-lg shadow-md">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold">{order.restaurantName}</h3>
                <p className="text-gray-600">
                  Posted {formatDistanceToNow(new Date(order.createdAt))} ago
                </p>
              </div>
              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                ${order.totalAmount.toFixed(2)}
              </span>
            </div>

            <div className="mb-4">
              <h4 className="font-medium mb-2">Order Items:</h4>
              <ul className="list-disc list-inside text-gray-600">
                {order.items.map((item, index) => (
                  <li key={index}>
                    {item.quantity}x {item.name}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mb-4">
              <h4 className="font-medium mb-1">Delivery Location:</h4>
              <p className="text-gray-600">{order.deliveryAddress}</p>
            </div>

            <Button
              onClick={() => handleAcceptOrder(order.id)}
              className="w-full"
            >
              Accept Order
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Search, Filter, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ReviewDialog } from '@/components/reviews/review-dialog';
import { getUserOrders } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { Order } from '@/lib/types';

export function OrderHistoryPage() {
  const { id: userId } = useUser();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    const fetchOrders = async () => {
      if (!userId) return;
      const userOrders = await getUserOrders(userId);
      setOrders(userOrders);
    };

    fetchOrders();
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, [userId]);

  const filteredOrders = orders.filter(order => {
    const matchesSearch = order.items.some(item =>
      item.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    const matchesStatus = !statusFilter || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleReviewSubmitted = async () => {
    if (!userId) return;
    const userOrders = await getUserOrders(userId);
    setOrders(userOrders);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'delivered':
        return 'bg-blue-100 text-blue-700';
      case 'picked_up':
        return 'bg-yellow-100 text-yellow-700';
      case 'order_placed':
        return 'bg-purple-100 text-purple-700';
      case 'runner_assigned':
        return 'bg-indigo-100 text-indigo-700';
      case 'created':
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-gray-100 text-gray-700';
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
                onChange={(e) => setStatusFilter(e.target.value || null)}
              >
                <option value="">All Status</option>
                <option value="created">Order Created</option>
                <option value="runner_assigned">Runner Assigned</option>
                <option value="order_placed">Order Placed</option>
                <option value="picked_up">Order Picked Up</option>
                <option value="delivered">Delivered</option>
                <option value="completed">Completed</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4 pointer-events-none" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm">
          {filteredOrders.map((order) => (
            <div
              key={order.id}
              className="border-b last:border-b-0 p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold">Order #{order.order_id}</h3>
                  <p className="text-sm text-gray-600">
                    {new Date(order.created_at!).toLocaleDateString()} at{' '}
                    {new Date(order.created_at!).toLocaleTimeString()}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(order.status)}`}>
                    {order.status === 'picked_up' && (
                      <Clock className="inline-block h-4 w-4 mr-1" />
                    )}
                    {order.status.replace('_', ' ').charAt(0).toUpperCase() + 
                     order.status.replace('_', ' ').slice(1)}
                  </span>
                  <Link
                    to={`/customer/order/${order.order_id}/tracking`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    Track Order
                  </Link>
                  {order.status === 'completed' && order.runner_id && !order.review && (
                    <ReviewDialog
                      orderId={order.order_id}
                      runnerId={order.runner_id}
                      runnerName={order.runner_name || 'Runner'}
                      onReviewSubmitted={handleReviewSubmitted}
                    />
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600">
                    {order.items.map(item => `${item.quantity}x ${item.name}`).join(', ')}
                  </p>
                  {order.runner_name && (
                    <p className="text-sm text-gray-500 mt-1">
                      Runner: {order.runner_name}
                      {order.review && (
                        <span className="ml-2 text-green-600">
                          (Review submitted)
                        </span>
                      )}
                    </p>
                  )}
                </div>
                <p className="font-semibold">
                  ${order.total.toFixed(2)}
                </p>
              </div>
            </div>
          ))}

          {filteredOrders.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg">No orders found</p>
              <p className="mt-2">Try adjusting your search or filters</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
import { nanoid } from 'nanoid';
import type { 
  Order,
  OrderStatus,
  // PaymentStatus, // Removed as unused
  Transaction,
  Wallet,
  Notification,
  OrderLog,
  UserProfile, // Keep UserProfile import
  UserRole,
  Review,
  ApiOrderResponse // Import ApiOrderResponse
} from './types';

// Initialize storage
const initializeStorage = () => {
  if (!localStorage.getItem('orders')) {
    localStorage.setItem('orders', JSON.stringify([]));
  }
  if (!localStorage.getItem('wallets')) {
    localStorage.setItem('wallets', JSON.stringify({}));
  }
  if (!localStorage.getItem('transactions')) {
    localStorage.setItem('transactions', JSON.stringify([]));
  }
  if (!localStorage.getItem('notifications')) {
    localStorage.setItem('notifications', JSON.stringify([]));
  }
  if (!localStorage.getItem('orderLogs')) {
    localStorage.setItem('orderLogs', JSON.stringify([]));
  }
  if (!localStorage.getItem('profiles')) {
    localStorage.setItem('profiles', JSON.stringify({}));
  }
  if (!localStorage.getItem('reviews')) {
    localStorage.setItem('reviews', JSON.stringify([]));
  }
};

function generateOrderId() {
  const year = new Date().getFullYear().toString().slice(-2);
  const random = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `G${year}${random}`;
}

async function recalculateUserStats(userId: string, role: UserRole) {
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  const transactions = JSON.parse(localStorage.getItem('transactions') || '[]');
  const reviews = JSON.parse(localStorage.getItem('reviews') || '[]');
  const profiles = JSON.parse(localStorage.getItem('profiles') || '{}');

  const profile: UserProfile = profiles[userId] || await getUserProfile(userId); // Add type

  let stats = {
    totalOrders: 0,
    totalSpent: undefined as number | undefined,
    totalEarned: undefined as number | undefined,
    completionRate: undefined as number | undefined,
    averageRating: undefined as number | undefined
  };

  if (role === 'customer') {
    const customerOrders = orders.filter((o: Order) => // Add type
      o.user_id === userId &&
      o.status === 'completed'
    );

    const customerTransactions = transactions.filter((t: Transaction) => // Add type
      t.user_id === userId &&
      t.type === 'payment' &&
      t.status === 'completed'
    );

    stats = {
      ...stats,
      totalOrders: customerOrders.length,
      totalSpent: customerTransactions.reduce((sum: number, t: Transaction) => sum + t.amount, 0), // Add types
    };
  } else if (role === 'runner') {
    const runnerOrders = orders.filter((o: Order) => // Add type
      o.runner_id === userId &&
      o.status === 'completed'
    );

    const runnerTransactions = transactions.filter((t: Transaction) => // Add type
      t.user_id === userId &&
      t.type === 'earning' &&
      t.status === 'completed'
    );

    const allRunnerOrders = orders.filter((o: Order) => o.runner_id === userId); // Add type
    const completionRate = allRunnerOrders.length > 0
      ? (runnerOrders.length / allRunnerOrders.length) * 100
      : 0;

    const userReviews = reviews.filter((r: Review) => r.runner_id === userId); // Add type
    const averageRating = userReviews.length > 0
      ? userReviews.reduce((sum: number, r: Review) => sum + r.rating, 0) / userReviews.length // Add types
      : undefined;

    stats = {
      ...stats,
      totalOrders: runnerOrders.length,
      totalEarned: runnerTransactions.reduce((sum: number, t: Transaction) => sum + t.amount, 0), // Add types
      completionRate,
      averageRating
    };
  }

  await updateUserProfile(userId, {
    ...profile,
    stats
  });

  return stats;
}

async function createOrder(orderData: Omit<Order, 'id' | 'order_id' | 'status' | 'payment_status' | 'customer_confirmation' | 'runner_confirmation'>) {
  initializeStorage();

  const id = nanoid();
  const orderId = generateOrderId();

  // Get customer profile for name and contact info
  const customerProfile = await getUserProfile(orderData.user_id);

  const order: Order = {
    ...orderData, // Spread orderData first
    id,
    order_id: orderId,
    status: 'created',
    payment_status: 'pending',
    customer_confirmation: 'pending',
    runner_confirmation: 'pending',
    customer_name: customerProfile.name, // These will overwrite if present in orderData, but needed if not
    customer_telegram: customerProfile.telegram, // These will overwrite if present in orderData, but needed if not
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const orders: Order[] = JSON.parse(localStorage.getItem('orders') || '[]'); // Add type
  orders.unshift(order); // Add to beginning of array
  localStorage.setItem('orders', JSON.stringify(orders));

  // Create order log
  createOrderLog(orderId, 'Order created', 'info');

  // Create notification for customer
  createNotification(
    orderData.user_id,
    'Order Created',
    `Your order #${orderId} has been created and is waiting for a runner.`,
    'success'
  );

  return order;
}

// Modified getOrder to fetch from backend API and return the API structure
async function getOrder(orderId: string, token: string | null): Promise<ApiOrderResponse | null> {
  // Removed localStorage logic
  // return orders.find((order: Order) => order.order_id === orderId) || null;

  if (!token) {
    console.error("GetOrder Error: Authentication token is missing.");
    // Returning null will keep the loading state in the component
    return null;
  }

  if (!orderId) {
    console.error("GetOrder Error: Order ID is missing.");
    return null;
  }

  // --- Fetch from Backend (Order Service) ---
  // Use the Order Service endpoint: /getOrderDetails?orderId=...
  const apiUrl = `http://localhost:3002/getOrderDetails?orderId=${orderId}`;
  console.log(`[api.ts] Fetching order details from Order Service: ${apiUrl}`); // Log the URL being fetched

  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json', // Good practice, though not always needed for GET
      },
    });

    console.log(`[api.ts] Fetch response status for ${orderId}: ${response.status}`); // Log status

    if (!response.ok) {
      // Log detailed error information if possible
      let errorBody = 'Could not read error body';
      try {
        errorBody = await response.text(); // Try reading response body for more details
      } catch { /* Ignore if body cannot be read - removed unused 'e' */ }
      console.error(`GetOrder Error: Failed to fetch order ${orderId}. Status: ${response.status} ${response.statusText}. Body: ${errorBody}`);
      return null; // Indicate failure
    }

    // Expect the backend to return the ApiOrderResponse structure
    const orderData: ApiOrderResponse = await response.json();
    console.log(`[api.ts] Successfully fetched order data for ${orderId}:`, orderData);
    return orderData; // Return the fetched API data structure

  } catch (error) {
    console.error(`GetOrder Error: Network or parsing error fetching order ${orderId}:`, error);
    return null; // Indicate failure due to network/parsing issues
  }
}


async function updateOrderStatus(orderId: string, status: OrderStatus) {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  const order = orders.find((o: Order) => o.order_id === orderId);
  
  if (!order) return;

  const updatedOrders = orders.map((o: Order) => 
    o.order_id === orderId ? { ...o, status, updated_at: new Date().toISOString() } : o
  );
  localStorage.setItem('orders', JSON.stringify(updatedOrders));

  // Create order log
  createOrderLog(orderId, `Order status updated to ${status}`, 'info');

  // Create notifications based on status
  if (order.user_id) {
    const title = 'Order Status Updated'; // Use const
    let message = '';

    switch (status) {
      case 'order_placed':
        message = `Your order #${orderId} has been placed by the runner`;
        break;
      case 'picked_up':
        message = `Your order #${orderId} has been picked up and is on its way`;
        break;
      case 'delivered':
        message = `Your order #${orderId} has been delivered. Please confirm receipt`;
        break;
      default:
        message = `Your order #${orderId} is now ${status.replace('_', ' ')}`;
    }

    createNotification(order.user_id, title, message, 'info');
  }

  if (order.runner_id) {
    createNotification(
      order.runner_id,
      'Order Status Updated',
      `Order #${orderId} is now ${status.replace('_', ' ')}`,
      'info'
    );
  }
}

async function confirmDelivery(orderId: string, userId: string, role: 'customer' | 'runner') {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  const order = orders.find((o: Order) => o.order_id === orderId);
  
  if (!order) return;

  // Only allow confirmation if order is in picked_up or delivered status
  if (!['picked_up', 'delivered'].includes(order.status)) {
    throw new Error('Order must be picked up before confirming delivery');
  }

  const confirmationField = role === 'customer' ? 'customer_confirmation' : 'runner_confirmation';
  
  // Update the confirmation status
  const updatedOrders = orders.map((o: Order) => {
    if (o.order_id === orderId) {
      const updatedOrder = { 
        ...o, 
        [confirmationField]: 'confirmed',
        updated_at: new Date().toISOString()
      };

      // If both parties have confirmed, mark as completed
      if (
        (role === 'customer' && o.runner_confirmation === 'confirmed') ||
        (role === 'runner' && o.customer_confirmation === 'confirmed')
      ) {
        updatedOrder.status = 'completed';
      } else {
        updatedOrder.status = 'delivered';
      }

      return updatedOrder;
    }
    return o;
  });

  localStorage.setItem('orders', JSON.stringify(updatedOrders));

  // Create order log
  createOrderLog(orderId, `Delivery confirmed by ${role}`, 'success');

  // Create notifications
  const updatedOrder = updatedOrders.find(o => o.order_id === orderId);
  
  if (updatedOrder?.status === 'completed') {
    // Both parties have confirmed
    if (order.user_id) {
      createNotification(
        order.user_id,
        'Order Completed',
        `Order #${orderId} has been completed. Payment released to runner.`,
        'success'
      );
    }
    if (order.runner_id) {
      createNotification(
        order.runner_id,
        'Order Completed',
        `Order #${orderId} completed. Payment has been released.`,
        'success'
      );
    }
    await releasePayment(orderId);
  } else {
    // Only one party has confirmed
    // const otherRole = role === 'customer' ? 'runner' : 'customer'; // Removed unused variable
    const otherUserId = role === 'customer' ? order.runner_id : order.user_id;

    if (otherUserId) {
      createNotification(
        otherUserId,
        'Delivery Confirmation Needed',
        `Please confirm delivery for order #${orderId}`,
        'info'
      );
    }
  }
}

async function releasePayment(orderId: string) {
  const orders: Order[] = JSON.parse(localStorage.getItem('orders') || '[]'); // Add type
  const order = orders.find((o: Order) => o.order_id === orderId);

  if (!order || !order.runner_id) return;

  // Update payment status
  const updatedOrders = orders.map((o: Order) => // Ensure type is specified here
    o.order_id === orderId ? { ...o, payment_status: 'released' } : o
  );
  localStorage.setItem('orders', JSON.stringify(updatedOrders));

  // Complete customer's payment transaction
  const transactions: Transaction[] = JSON.parse(localStorage.getItem('transactions') || '[]'); // Add type
  const updatedTransactions = transactions.map((t: Transaction) =>
    t.order_id === orderId ? { ...t, status: 'completed' } : t
  );

  // Create earning transaction for runner
  const runnerTransaction: Transaction = {
    id: nanoid(),
    user_id: order.runner_id,
    order_id: orderId,
    amount: order.deliveryFee,
    type: 'earning',
    status: 'completed',
    created_at: new Date().toISOString()
  };
  updatedTransactions.push(runnerTransaction);

  localStorage.setItem('transactions', JSON.stringify(updatedTransactions));

  // Create order log
  createOrderLog(orderId, 'Payment released to runner', 'success');

  // Recalculate stats for both customer and runner
  await recalculateUserStats(order.user_id, 'customer');
  await recalculateUserStats(order.runner_id, 'runner');
}

async function acceptOrder(orderId: string, runnerId: string) {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  const order = orders.find((o: Order) => o.order_id === orderId);
  
  if (!order) return;

  // Get runner's name from profile
  const runnerProfile = await getUserProfile(runnerId);
  const runnerName = runnerProfile.name;

  const updatedOrders = orders.map((o: Order) => 
    o.order_id === orderId ? { 
      ...o, 
      runner_id: runnerId,
      runner_name: runnerName,
      status: 'runner_assigned',
      updated_at: new Date().toISOString()
    } : o
  );
  localStorage.setItem('orders', JSON.stringify(updatedOrders));

  // Create order log
  createOrderLog(orderId, `Order accepted by runner ${runnerName}`, 'success');

  // Create notifications
  createNotification(
    order.user_id,
    'Runner Assigned',
    `${runnerName} has accepted your order #${orderId}`,
    'success'
  );
  createNotification(
    runnerId,
    'Order Accepted',
    `You have successfully accepted order #${orderId}`,
    'success'
  );
}

async function getAvailableOrders() {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  return orders.filter((order: Order) => order.status === 'created');
}

async function getActiveOrders(runnerId: string) {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  return orders.filter((order: Order) => 
    order.runner_id === runnerId && 
    ['runner_assigned', 'order_placed', 'picked_up', 'delivered'].includes(order.status)
  );
}

async function getCompletedOrders(runnerId: string) {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  return orders.filter((order: Order) => 
    order.runner_id === runnerId && 
    order.status === 'completed'
  );
}

async function getUserOrders(userId: string) {
  initializeStorage();
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  return orders.filter((order: Order) => order.user_id === userId);
}

async function getWallet(userId: string): Promise<Wallet> {
  initializeStorage();
  const transactions: Transaction[] = JSON.parse(localStorage.getItem('transactions') || '[]'); // Add type

  const userTransactions = transactions.filter((t: Transaction) => t.user_id === userId);
  const balance = userTransactions.reduce((sum: number, t: Transaction) => {
    if (t.status !== 'completed') return sum;
    return t.type === 'earning' ? sum + t.amount : sum - t.amount;
  }, 0);

  return {
    user_id: userId,
    balance,
    transactions: userTransactions
  };
}

async function createNotification(
  userId: string,
  title: string,
  message: string,
  type: 'info' | 'success' | 'warning' | 'error'
) {
  initializeStorage();
  const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
  
  const notification: Notification = {
    id: nanoid(),
    user_id: userId,
    title,
    message,
    type,
    read: false,
    created_at: new Date().toISOString()
  };

  notifications.push(notification);
  localStorage.setItem('notifications', JSON.stringify(notifications));
  return notification;
}

async function getNotifications(userId: string) {
  initializeStorage();
  const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
  return notifications.filter((n: Notification) => n.user_id === userId);
}

async function markNotificationAsRead(notificationId: string) {
  initializeStorage();
  const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
  const updatedNotifications = notifications.map((n: Notification) =>
    n.id === notificationId ? { ...n, read: true } : n
  );
  localStorage.setItem('notifications', JSON.stringify(updatedNotifications));
}

async function createOrderLog(
  orderId: string,
  message: string,
  type: 'info' | 'success' | 'warning' | 'error'
) {
  initializeStorage();
  const logs = JSON.parse(localStorage.getItem('orderLogs') || '[]');
  
  const log: OrderLog = {
    id: nanoid(),
    order_id: orderId,
    message,
    type,
    created_at: new Date().toISOString()
  };

  logs.push(log);
  localStorage.setItem('orderLogs', JSON.stringify(logs));
  return log;
}

async function getOrderLogs(orderId: string) {
  initializeStorage();
  const logs: OrderLog[] = JSON.parse(localStorage.getItem('orderLogs') || '[]'); // Add type
  return logs.filter((log: OrderLog) => log.order_id === orderId);
}

async function getUserProfile(userId: string): Promise<UserProfile> {
  initializeStorage();
  const profiles = JSON.parse(localStorage.getItem('profiles') || '{}');

  if (!profiles[userId]) {
    const orders: Order[] = JSON.parse(localStorage.getItem('orders') || '[]'); // Add type
    const wallet = await getWallet(userId);

    const userOrders = orders.filter((o: Order) =>
      o.user_id === userId || o.runner_id === userId
    );

    const profile: UserProfile = {
      id: userId,
      name: userId === 'alice' ? 'Alice' : 'Ray',
      email: `${userId}@campus.edu`,
      telegram: userId === 'alice' ? 'AliceLee2367' : 'Rayrae404',
      roles: userId === 'alice' ? ['customer'] : ['runner'],
      stats: {
        totalOrders: userOrders.length,
        totalSpent: userId === 'alice' 
          ? wallet.transactions
              .filter(t => t.type === 'payment' && t.status === 'completed')
              .reduce((sum, t) => sum + t.amount, 0)
          : undefined,
        totalEarned: userId === 'ray'
          ? wallet.transactions
              .filter(t => t.type === 'earning' && t.status === 'completed')
              .reduce((sum, t) => sum + t.amount, 0)
          : undefined,
        completionRate: userId === 'ray'
          ? userOrders.length > 0
            ? (userOrders.filter(o => o.status === 'completed').length / userOrders.length) * 100
            : 0
          : undefined,
        averageRating: userId === 'ray' ? 4.8 : undefined
      },
      created_at: new Date().toISOString()
    };

    profiles[userId] = profile;
    localStorage.setItem('profiles', JSON.stringify(profiles));
  }

  return profiles[userId];
}

async function updateUserProfile(userId: string, profile: Partial<UserProfile>) {
  initializeStorage();
  const profiles = JSON.parse(localStorage.getItem('profiles') || '{}');
  profiles[userId] = { ...profiles[userId], ...profile };
  localStorage.setItem('profiles', JSON.stringify(profiles));
  return profiles[userId];
}

async function submitReview(
  orderId: string,
  runnerId: string,
  customerId: string,
  rating: number,
  comment: string
): Promise<void> {
  initializeStorage();
  const reviews = JSON.parse(localStorage.getItem('reviews') || '[]');
  const customerProfile = await getUserProfile(customerId);
  
  const review: Review = {
    id: nanoid(),
    order_id: orderId,
    runner_id: runnerId,
    customer_id: customerId,
    customer_name: customerProfile.name,
    rating,
    comment,
    created_at: new Date().toISOString()
  };
  
  reviews.push(review);
  localStorage.setItem('reviews', JSON.stringify(reviews));

  // Update order status to reviewed
  const orders = JSON.parse(localStorage.getItem('orders') || '[]');
  const updatedOrders = orders.map((o: Order) =>
    o.order_id === orderId ? { ...o, status: 'reviewed', review } : o
  );
  localStorage.setItem('orders', JSON.stringify(updatedOrders));
  
  // Create notification for runner
  createNotification(
    runnerId,
    'New Review',
    `You received a ${rating}-star review for order #${orderId}`,
    'info'
  );
  
  // Recalculate runner's stats
  await recalculateUserStats(runnerId, 'runner');
}

async function getReviews(runnerId: string): Promise<Review[]> {
  initializeStorage();
  const reviews: Review[] = JSON.parse(localStorage.getItem('reviews') || '[]'); // Add type
  return reviews.filter((r: Review) => r.runner_id === runnerId);
}

export {
  createOrder,
  getOrder,
  updateOrderStatus,
  confirmDelivery,
  acceptOrder,
  getAvailableOrders,
  getActiveOrders,
  getCompletedOrders,
  getUserOrders,
  getWallet,
  getNotifications,
  markNotificationAsRead,
  getOrderLogs,
  getUserProfile,
  updateUserProfile,
  submitReview,
  getReviews,
  recalculateUserStats
};

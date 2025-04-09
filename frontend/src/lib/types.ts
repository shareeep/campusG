// Removed unused import { z } from 'zod';

export type UserRole = 'customer' | 'runner';

export type OrderStatus = 
  | 'created'           // Order created and payment auto-approved
  | 'runner_assigned'   // Runner has accepted the order
  | 'order_placed'      // Runner has placed the order
  | 'picked_up'        // Runner has picked up the order
  | 'delivered'        // Order has been delivered
  | 'completed'        // Both parties confirmed and payment released
  | 'reviewed';        // Customer has submitted a review

export type PaymentStatus = 'pending' | 'held' | 'released';
export type DeliveryConfirmation = 'pending' | 'confirmed';

export interface Review {
  id: string;
  order_id: string;
  runner_id: string;
  customer_id: string;
  customer_name: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface OrderItem {
  id?: string;
  name: string;
  quantity: number;
  price: number;
}

export interface StoreDetails {
  name: string;
  postalCode: string;
}

export interface DeliveryDetails {
  building: string;
  level: string;
  roomNumber: string;
  school: string;
  meetingPoint?: string;
}

export interface Order {
  id: string;
  order_id: string;
  user_id: string;
  customer_name: string;
  customer_telegram: string;
  runner_id?: string;
  runner_name?: string;
  store: StoreDetails;
  status: OrderStatus;
  payment_status: PaymentStatus;
  customer_confirmation: DeliveryConfirmation;
  runner_confirmation: DeliveryConfirmation;
  items: OrderItem[];
  deliveryDetails: DeliveryDetails;
  deliveryFee: number;
  total: number;
  instructions?: string;
  review?: Review;
  created_at?: string;
  updated_at?: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  order_id: string;
  amount: number;
  type: 'payment' | 'earning';
  status: 'pending' | 'completed';
  created_at: string;
}

export interface Wallet {
  user_id: string;
  balance: number;
  transactions: Transaction[];
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  created_at: string;
}

export interface OrderLog {
  id: string;
  order_id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  created_at: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  telegram: string;
  roles: UserRole[];
  stats: {
    totalOrders: number;
    totalSpent?: number;  // For customers
    totalEarned?: number; // For runners
    completionRate?: number; // For runners
    averageRating?: number; // For runners
  };
  reviews?: Review[];
  created_at: string;
}


// --- API Specific Types ---

// Structure returned by the Order Service /getOrderDetails endpoint
export interface ApiOrderResponse {
  orderId: string;
  custId: string;
  runnerId: string | null;
  orderDescription: string; // JSON string of items
  foodFee: number;
  deliveryFee: number;
  deliveryLocation: string;
  storeLocation?: string; // Added optional store location
  orderStatus: string; // e.g., "CREATED", "ACCEPTED"
  sagaId: string | null;
  createdAt: string;
  updatedAt: string;
  // Add new optional timestamp fields from backend
  acceptedAt?: string | null;
  placedAt?: string | null;
  pickedUpAt?: string | null;
  deliveredAt?: string | null;
  completedAt: string | null;
  cancelledAt?: string | null;
  // Add other potential fields from the actual API response if needed
  // e.g., instructions?: string; runner_name?: string; etc.
}

// Add other API-specific response types here if needed

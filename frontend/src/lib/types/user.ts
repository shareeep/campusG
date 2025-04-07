/**
 * Backend user type definition from user service
 */
export interface BackendUser {
  // The API is returning camelCase fields but we're looking for snake_case
  // Let's support both formats with optional fields
  
  // snake_case fields (original)
  clerk_user_id?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  username?: string;
  stripe_customer_id?: string;
  stripe_connect_account_id?: string;
  customer_rating?: number;
  runner_rating?: number;
  created_at?: string;
  updated_at?: string;
  user_stripe_card?: StripeCard;
  
  // camelCase fields (from API response)
  clerkUserId?: string;
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  stripeCustomerId?: string;
  stripeConnectAccountId?: string;
  customerRating?: number;
  runnerRating?: number;
  createdAt?: string;
  updatedAt?: string;
  userStripeCard?: StripeCard;
}

/**
 * Stripe card information stored in the user record
 */
export interface StripeCard {
  // Original snake_case fields
  payment_method_id?: string;
  card_type?: string;
  last_four?: string;
  expiry_month?: string;
  expiry_year?: string;
  
  // camelCase fields from API
  paymentMethodId?: string;
  cardType?: string;
  last4?: string;
  exp_month?: number;
  exp_year?: number;
  brand?: string;
  updated_at?: string;
}

/**
 * Backend user type definition from user service
 */
export interface BackendUser {
  clerk_user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number?: string;
  username?: string;
  stripe_customer_id?: string;
  stripe_connect_account_id?: string;
  customer_rating?: number;
  runner_rating?: number;
  created_at: string;
  updated_at: string;
}

/**
 * Type definitions for CampusG application
 */

/**
 * Backend User model
 */
export interface BackendUser {
  userId: string;
  clerkUserId: string;
  email: string;
  firstName: string;
  lastName: string;
  phoneNumber: string | null;
  customerRating: number;
  runnerRating: number;
  createdAt: string;
  updatedAt: string;
  userStripeCard?: object;
}

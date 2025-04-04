# Stripe and Clerk Integration Files

This directory contains backups of all frontend files that provide connectivity with Stripe and Clerk. These files are organized in the same directory structure as the original frontend to make merging easier.

## Stripe Integration Files

1. **src/providers/StripeProvider.tsx**
   - Core provider that initializes Stripe using `loadStripe` and wraps the application with Stripe's `Elements` provider
   - Sets up the Stripe context with publishable key for the entire application

2. **src/components/PaymentHandler.tsx**
   - Handles the 3D Secure authentication flow with Stripe
   - Manages payment responses and authentication challenges
   - Provides the `handlePaymentResponse` function for processing Stripe payment results

3. **src/components/payments/CreditCardForm.tsx**
   - Form component for collecting and validating credit card information
   - Uses Stripe Elements (`CardElement`) for secure card input
   - Handles creating payment methods through Stripe's API

4. **src/components/payments/SavedCardDisplay.tsx**
   - Display component for showing saved card information
   - Displays card last 4 digits, brand, and expiry date
   - Provides delete functionality for removing saved cards

## Clerk Integration Files

1. **src/App.tsx**
   - Initializes Clerk authentication with `ClerkProvider` at the root level
   - Configures Clerk with the publishable key

2. **src/lib/useBackendUser.ts**
   - Custom hook that bridges Clerk authentication with backend user data
   - Uses Clerk's `useUser` hook to access authenticated user information
   - Fetches corresponding backend user data based on Clerk user ID

3. **src/lib/api-client.ts**
   - Contains functions for backend API communication using Clerk user IDs
   - Includes `getUserByClerkId` to fetch user data from the backend

4. **src/app/layout.tsx** and **src/app/page.tsx**
   - Next.js app router integration with Clerk
   - Sets up ClerkProvider at the layout level

5. **src/pages/auth/sign-in.tsx** and **src/pages/auth/sign-up.tsx**
   - Authentication pages using Clerk components

6. **src/components/layout/header.tsx**
   - Implements Clerk's `UserButton` component for user account management
   - Uses `SignedIn` and `SignedOut` components for conditional rendering

7. **src/routes/index.tsx**
   - Uses Clerk's authentication state components for protected routes
   - Implements `SignedIn`, `SignedOut`, and `RedirectToSignIn`

8. **src/components/DebugToken.tsx**
   - Uses Clerk's `useAuth` hook for debugging authentication tokens

## Usage Guide

When merging new frontend code, ensure that these integration files are preserved or properly updated to maintain connectivity with Stripe and Clerk services.

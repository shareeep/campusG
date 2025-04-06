# User Service: Account Creation Guide

This document explains how user accounts are created and synchronized within the User Service, including the integration with Clerk for authentication and Stripe for payments.

## Overview

User creation is primarily driven by the frontend application's integration with Clerk for user authentication and management. The User Service listens for events from Clerk via webhooks to create and update corresponding user records in its own database.

## Creation Flow

1.  **Frontend Signup (Clerk):** A new user signs up or logs in for the first time via the frontend application using Clerk's authentication components (e.g., `<SignUp />`, `<SignIn />`).
2.  **Clerk Event:** Upon successful user creation within Clerk's system, Clerk automatically sends a `user.created` event via a pre-configured webhook.
3.  **User Service Webhook Endpoint:** The User Service exposes an endpoint (typically `/api/webhook/clerk`) to receive these webhooks from Clerk.
4.  **Webhook Processing (`handle_user_created`):**
    *   The User Service receives the `user.created` webhook payload.
    *   It extracts relevant user details (Clerk User ID, email, first name, last name, etc.) from the payload.
    *   It creates a new record in the `users` table of the User Service's PostgreSQL database, storing the `clerk_user_id` and other profile information.
5.  **Stripe Customer Creation:**
    *   Immediately after preparing the user record (before saving to the DB initially, or just after), the `handle_user_created` function makes an API call to Stripe (`POST /v1/customers`).
    *   It passes user details like email and name to Stripe.
    *   Stripe creates a new Customer object and returns its unique ID (`cus_...`).
6.  **Saving Stripe ID:**
    *   The User Service saves the received `stripe_customer_id` to the corresponding user's record in its database.
    *   The user record is then committed to the database.

## Result

After this process:

*   The user exists in Clerk's system.
*   The user has a corresponding record in the User Service database, linked by `clerk_user_id`.
*   The user has a corresponding Customer object in Stripe, linked by `stripe_customer_id` stored in the User Service database.

This ensures that when other services (like the Create Order Saga) need payment information, the User Service can retrieve the necessary `stripeCustomerId` associated with the user's `clerk_user_id`.

## Testing User Creation

To test this flow without using the frontend:

1.  Ensure the User Service is running.
2.  Craft a JSON payload mimicking the Clerk `user.created` webhook event (ensure unique `id` and `email_address`).
3.  Send an HTTP POST request with the JSON payload to the User Service's webhook endpoint (`http://localhost:3001/api/webhook/clerk` if running locally via Docker Compose).
4.  Verify by checking:
    *   User Service logs for successful processing and Stripe customer creation messages.
    *   The User Service database for the new user record with a populated `stripe_customer_id`.
    *   (Optional) The Stripe Dashboard (using test keys) for the newly created customer.

# Frontend Integration Overview (April 8, 2025)

This document summarizes the integration work performed to connect the frontend React application with the backend microservices and saga orchestrators.

## Key Pages Integrated:

1.  **Place Order Page (`frontend/src/pages/customer/create-order.tsx`)**
    *   **Goal:** Allow customers to submit new orders, triggering the Create Order Saga.
    *   **Backend Endpoint:** `POST http://localhost:3101/orders` (Create Order Saga Orchestrator)
    *   **Changes:**
        *   Replaced placeholder submission logic with a `fetch` call to the saga endpoint.
        *   Integrated Clerk `useAuth` hook to get `userId` and auth `token`.
        *   Added `isLoaded` and `isSignedIn` checks from Clerk to prevent submission before authentication is ready.
        *   Added price input field to match UI and backend requirements.
        *   Constructed the JSON payload including `customer_id` (from Clerk `userId`), `order_details` (items with price, delivery location, instructions).
        *   Handled API response (success/error) using toasts.
    *   **Considerations:** Ensured item structure (including price) matched backend expectations. Added auth checks.

2.  **Order History Page (`frontend/src/pages/customer/order-history.tsx`)**
    *   **Goal:** Allow customers to view their past orders.
    *   **Backend Endpoint:** `GET http://localhost:3002/orders/customer/{userId}` (Order Service)
    *   **Changes:**
        *   **Backend:** Added the new `/orders/customer/{userId}` route to `services/order_service/app/api/routes.py` to filter orders by customer.
        *   **Frontend:**
            *   Replaced previous data fetching logic (`useUser`, `getUserOrders`) with a direct `fetch` call using Clerk's `useAuth` for `userId` and `token`.
            *   Updated the `BackendOrder` interface to match the structure returned by the Order Service's `to_dict()` method.
            *   Adjusted status filter options and display logic (`getStatusColor`) to match backend `OrderStatus` enum values.
            *   Made the entire order item clickable via `Link` to the tracking page.
            *   Updated `ReviewDialog` props (passed generic runner name as it's not available from this endpoint).
            *   Added loading and error states.
    *   **Considerations:** Required adding a new backend endpoint for user-specific filtering. Aligned frontend data structure and status handling with the backend.

3.  **Available Orders Page (`frontend/src/pages/runner/available-orders.tsx`)**
    *   **Goal:** Allow runners to view and accept available orders, triggering the Accept Order Saga.
    *   **Backend Endpoints:**
        *   Fetch Orders: `GET http://localhost:3002/orders?status=CREATED` (Order Service)
        *   Accept Order: `POST http://localhost:3102/acceptOrder` (Accept Order Saga Orchestrator)
    *   **Changes:**
        *   **Backend:** Modified `GET /orders` in Order Service to accept an optional `status` query parameter.
        *   **Frontend:**
            *   Replaced previous data fetching/accepting logic with direct `fetch` calls using Clerk `useAuth`.
            *   Fetched orders filtered by `status=CREATED`.
            *   Implemented `handleAcceptOrder` to call the Accept Order Saga endpoint with `orderId` and `runner_id` (from Clerk `userId`).
            *   Updated UI to display order details based on `BackendOrder` type (parsing `orderDescription` for items).
            *   Added loading state for the "Accept" button.
    *   **Considerations:** Required modifying the backend `/orders` endpoint for status filtering. Ensured correct saga endpoint was called for accepting.

4.  **Active Orders Page (`frontend/src/pages/runner/active-orders.tsx`)**
    *   **Goal:** Allow runners to view their assigned active orders and update their status, eventually triggering the Complete Order Saga.
    *   **Backend Endpoints:**
        *   Fetch Orders: `GET http://localhost:3002/orders?runnerId={runnerId}` (Order Service)
        *   Update Status: `POST http://localhost:3002/updateOrderStatus` (Order Service)
        *   Trigger Completion: `POST http://localhost:3103/updateOrderStatus` (Complete Order Saga Orchestrator)
    *   **Changes:**
        *   **Backend:** Modified `GET /orders` in Order Service to accept an optional `runnerId` query parameter.
        *   **Frontend:**
            *   Replaced previous data fetching/updating logic with direct `fetch` calls using Clerk `useAuth`.
            *   Fetched orders filtered by the logged-in `runnerId`.
            *   Separated fetched orders into "active" and "completed" lists for display.
            *   Implemented `handleUpdateStatus` to call the Order Service's `/updateOrderStatus` endpoint for intermediate status changes (e.g., ACCEPTED -> PLACED -> ON_THE_WAY -> DELIVERED).
            *   Implemented `handleCompleteOrderSaga` to call the Complete Order Saga's `/updateOrderStatus` endpoint when the runner marks an order as `DELIVERED`.
            *   Updated UI logic (`getButtonProps`) to determine the correct action (update status vs. trigger completion) based on the current order status.
            *   Added loading state for action buttons.
    *   **Considerations:** Required modifying the backend `/orders` endpoint for runner filtering. Differentiated between direct status updates (to Order Service) and triggering the completion saga (to Complete Order Saga Orchestrator), noting the shared `/updateOrderStatus` route name but different ports.

## Error Fixes:

1.  **CORS Error (Order Service):**
    *   **Issue:** Frontend (`http://localhost:5173`) requests to Order Service (`http://localhost:3002`) were blocked by CORS policy.
    *   **Fix:**
        *   Added `Flask-Cors` to `services/order_service/requirements.txt`.
        *   Initialized `CORS` in `services/order_service/app/__init__.py`, specifically allowing the frontend origin (`http://localhost:5173`).
    *   **Action Required:** The `order-service` Docker container needs to be rebuilt and restarted (`docker-compose up -d --build order-service`) for the CORS fix to take effect.

2.  **Authentication Error (Place Order Page):**
    *   **Issue:** Users saw a "Not logged in" error even when authenticated, likely because the form submitted before Clerk finished loading the user state.
    *   **Fix:** Modified `frontend/src/pages/customer/create-order.tsx` to use `isLoaded` and `isSignedIn` flags from Clerk's `useAuth` hook. The submit button is disabled while `!isLoaded`, and the `onSubmit` function checks `isSignedIn` before proceeding.

## Next Steps / Notes:

*   Ensure the `order-service` Docker container is rebuilt and restarted to apply the CORS fix.
*   Verify the authentication flow on the Place Order page is now working correctly.
*   The `ReviewDialog` component currently uses a placeholder "the runner" as the runner's name is not fetched on the Order History page. This could be enhanced by fetching user details if needed.
*   The `OrderLogs` component was assumed to exist and function correctly.
*   Error handling and loading states have been added/improved on the modified pages.

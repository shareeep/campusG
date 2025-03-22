# Changelog - 21 March 2025

## Fixed Order Service API Connectivity Issues

### Problem
The order service container was starting but immediately crashing due to issues with asynchronous code in Flask API routes. This was causing the following error when trying to access the API via Postman:

```
POST http://localhost:3002/api/createOrder
Error: connect ECONNREFUSED 127.0.0.1:3002
```

### Root Causes
1. Flask does not natively support asynchronous route handlers without additional packages
2. The API routes were using `async def` syntax but Flask was unable to execute them
3. Similarly, `await` was being used to call saga methods, but this requires an async context

### Changes Made
1. Modified `services/order_service/app/api/routes.py`:
   - Changed all route handler functions from `async def` to regular `def` functions
   - Removed `await` keyword when calling saga methods

2. Modified `services/order_service/app/sagas/create_order_saga.py`:
   - Changed all methods from `async def` to regular `def` functions
   - Removed all `async` and `await` keywords throughout the file

3. Fixed timezone issue in `services/order_service/app/models/models.py`:
   - Changed `datetime.UTC` to `timezone.utc` for better compatibility with Python 3.11
   - Added import for `timezone` from `datetime` package

### Results
- The order service now starts and runs properly
- The API endpoints are now accessible at http://localhost:3002/api/
- Confirmed working by testing:
  - GET /api/orders - Returns empty list as expected
  - POST /api/createOrder - Returns user not found error (expected since test user doesn't exist)

### Notes
- The "User not found" error is normal and not related to our fix - it's because we're using a test user ID that doesn't exist
- No database migrations were necessary since the model changes were backward compatible

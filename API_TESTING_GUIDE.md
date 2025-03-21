# CampusG Microservices API Testing Guide

This document provides a comprehensive guide to test all microservices in the CampusG application using tools like Postman or curl. For each endpoint, we provide the URL, HTTP method, required request body, and expected response.

## Table of Contents
- [Setup](#setup)
- [User Service](#user-service)
- [Order Service](#order-service)
- [Payment Service](#payment-service)
- [Escrow Service](#escrow-service)
- [Timer Service](#timer-service)
- [Notification Service](#notification-service)
- [End-to-End Workflows](#end-to-end-workflows)

## Setup

1. Start the Docker containers using:
   ```
   docker-compose up -d
   ```

2. Services are available at the following ports:
   - User Service: http://localhost:3001
   - Order Service: http://localhost:3002
   - Payment Service: http://localhost:3003
   - Escrow Service: http://localhost:3004
   - Scheduler Service: http://localhost:3005
   - Notification Service: http://localhost:3006
   - Timer Service: http://localhost:3007

3. You can use Postman, curl, or any API testing tool to send requests.

## User Service

### Create a User
- **URL**: `http://localhost:3001/api/users`
- **Method**: POST
- **Body**:
  ```json
  {
    "email": "customer@example.com",
    "firstName": "Jane",
    "lastName": "Customer",
    "phoneNumber": "+1234567890"
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "User created successfully",
    "user": {
      "user_id": "generated-uuid",
      "email": "customer@example.com",
      "first_name": "Jane",
      "last_name": "Customer",
      "phone_number": "+1234567890",
      "created_at": "2025-03-21T06:29:27.000Z"
    }
  }
  ```

### Get User by ID
- **URL**: `http://localhost:3001/api/users/{user_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "user": {
      "user_id": "user-uuid",
      "email": "customer@example.com",
      "first_name": "Jane",
      "last_name": "Customer",
      "phone_number": "+1234567890",
      "created_at": "2025-03-21T06:29:27.000Z"
    }
  }
  ```

### Update User Payment Information
- **URL**: `http://localhost:3001/api/users/{user_id}/payment`
- **Method**: PUT
- **Body**:
  ```json
  {
    "cardLast4": "4242",
    "cardType": "Visa",
    "expiryMonth": "12",
    "expiryYear": "2025",
    "stripeToken": "tok_visa"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Payment information updated successfully"
  }
  ```

### Get User Payment Information
- **URL**: `http://localhost:3001/api/users/{user_id}/payment-info`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "payment_info": {
      "last4": "4242",
      "brand": "Visa",
      "exp_month": "12",
      "exp_year": "2025",
      "token": "tok_visa"
    }
  }
  ```

### Update Customer Rating
- **URL**: `http://localhost:3001/api/users/{user_id}/update-customer-rating`
- **Method**: POST
- **Body**:
  ```json
  {
    "rating": 4.5
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Customer rating updated successfully"
  }
  ```

### Update Runner Rating
- **URL**: `http://localhost:3001/api/users/{user_id}/update-runner-rating`
- **Method**: POST
- **Body**:
  ```json
  {
    "rating": 4.8
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Runner rating updated successfully"
  }
  ```

### Get All User IDs
- **URL**: `http://localhost:3001/api/list-users`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "userIds": [
      "user-uuid-1",
      "user-uuid-2",
      "user-uuid-3"
    ]
  }
  ```

## Order Service

### Get All Orders
- **URL**: `http://localhost:3002/api/orders?page=1&limit=10`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "items": [
      {
        "id": "order-uuid",
        "cust_id": "customer-uuid",
        "runner_id": "runner-uuid",
        "order_status": "READY_FOR_PICKUP",
        "order_details": {
          "items": [
            {"name": "Burger", "price": 9.99, "quantity": 2}
          ],
          "restaurant": "Burger Place",
          "deliveryAddress": "123 Campus Rd"
        },
        "created_at": "2025-03-21T06:30:00.000Z"
      }
    ],
    "total": 1,
    "pages": 1,
    "page": 1
  }
  ```

### Get Order Details
- **URL**: `http://localhost:3002/api/getOrderDetails?orderId=order-uuid`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "id": "order-uuid",
    "cust_id": "customer-uuid",
    "runner_id": "runner-uuid",
    "order_status": "READY_FOR_PICKUP",
    "order_details": {
      "items": [
        {"name": "Burger", "price": 9.99, "quantity": 2}
      ],
      "restaurant": "Burger Place",
      "deliveryAddress": "123 Campus Rd"
    },
    "created_at": "2025-03-21T06:30:00.000Z"
  }
  ```

### Create Order
- **URL**: `http://localhost:3002/api/createOrder`
- **Method**: POST
- **Body**:
  ```json
  {
    "customerId": "customer-uuid",
    "orderDetails": {
      "items": [
        {"name": "Burger", "price": 9.99, "quantity": 2}
      ],
      "restaurant": "Burger Place",
      "deliveryAddress": "123 Campus Rd",
      "totalAmount": 19.98
    }
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "message": "Order created successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "order_status": "READY_FOR_PICKUP",
      "order_details": {
        "items": [
          {"name": "Burger", "price": 9.99, "quantity": 2}
        ],
        "restaurant": "Burger Place",
        "deliveryAddress": "123 Campus Rd",
        "totalAmount": 19.98
      },
      "created_at": "2025-03-21T06:32:00.000Z"
    }
  }
  ```

### Update Order Status
- **URL**: `http://localhost:3002/api/updateOrderStatus`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "status": "ON_THE_WAY"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "message": "Order status updated successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_status": "ON_THE_WAY",
      "created_at": "2025-03-21T06:32:00.000Z"
    }
  }
  ```

### Verify and Accept Order (Runner)
- **URL**: `http://localhost:3002/api/verifyAndAcceptOrder`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "runnerId": "runner-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "message": "Order accepted successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_status": "ACCEPTED",
      "created_at": "2025-03-21T06:32:00.000Z"
    }
  }
  ```

### Cancel Order
- **URL**: `http://localhost:3002/api/cancelOrder`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "message": "Order cancelled successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "order_status": "CANCELLED",
      "created_at": "2025-03-21T06:32:00.000Z"
    }
  }
  ```

### Cancel Acceptance (Runner)
- **URL**: `http://localhost:3002/api/cancelAcceptance`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "message": "Order acceptance cancelled successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "runner_id": null,
      "order_status": "READY_FOR_PICKUP",
      "created_at": "2025-03-21T06:32:00.000Z"
    }
  }
  ```

### Complete Order
- **URL**: `http://localhost:3002/api/completeOrder`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "message": "Order completed successfully",
    "order": {
      "id": "order-uuid",
      "cust_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_status": "COMPLETED",
      "created_at": "2025-03-21T06:32:00.000Z",
      "end_time": "2025-03-21T07:15:00.000Z"
    }
  }
  ```

## Payment Service

### Authorize Payment
- **URL**: `http://localhost:3003/api/payments/authorize`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "customerId": "customer-uuid",
    "amount": 19.98
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Payment authorized successfully",
    "paymentId": "payment-uuid",
    "stripePaymentId": "pi_mock123456"
  }
  ```

### Move Payment to Escrow
- **URL**: `http://localhost:3003/api/payments/move-to-escrow`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Payment moved to escrow successfully"
  }
  ```

### Revert Payment
- **URL**: `http://localhost:3003/api/payments/revert`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Payment authorization reverted successfully"
  }
  ```

### Get Payment Details
- **URL**: `http://localhost:3003/api/payments/{payment_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "payment": {
      "payment_id": "payment-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "amount": 19.98,
      "status": "AUTHORIZED",
      "created_at": "2025-03-21T06:35:00.000Z"
    }
  }
  ```

### Get Payments (with filters)
- **URL**: `http://localhost:3003/api/payments?orderId=order-uuid`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "payments": [
      {
        "payment_id": "payment-uuid",
        "order_id": "order-uuid",
        "customer_id": "customer-uuid",
        "amount": 19.98,
        "status": "AUTHORIZED",
        "created_at": "2025-03-21T06:35:00.000Z"
      }
    ]
  }
  ```

## Escrow Service

### Hold Funds in Escrow
- **URL**: `http://localhost:3004/api/escrow/hold`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "customerId": "customer-uuid",
    "amount": 19.98,
    "foodFee": 16.98,
    "deliveryFee": 3.00
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "Funds held successfully",
    "escrow": {
      "escrow_id": "escrow-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "amount": 19.98,
      "food_fee": 16.98,
      "delivery_fee": 3.00,
      "status": "HELD",
      "created_at": "2025-03-21T06:37:00.000Z"
    }
  }
  ```

### Release Funds from Escrow
- **URL**: `http://localhost:3004/api/escrow/release`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "runnerId": "runner-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Funds released successfully",
    "escrow": {
      "escrow_id": "escrow-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "amount": 19.98,
      "status": "RELEASED",
      "created_at": "2025-03-21T06:37:00.000Z"
    }
  }
  ```

### Refund Funds from Escrow
- **URL**: `http://localhost:3004/api/escrow/refund`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Funds refunded successfully",
    "escrow": {
      "escrow_id": "escrow-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "amount": 19.98,
      "status": "REFUNDED",
      "created_at": "2025-03-21T06:37:00.000Z"
    }
  }
  ```

### Get Escrow Details by ID
- **URL**: `http://localhost:3004/api/escrow/{escrow_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "escrow": {
      "escrow_id": "escrow-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "amount": 19.98,
      "food_fee": 16.98,
      "delivery_fee": 3.00,
      "status": "HELD",
      "created_at": "2025-03-21T06:37:00.000Z"
    }
  }
  ```

### Get Escrow by Order ID
- **URL**: `http://localhost:3004/api/escrow/order/{order_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "escrow": {
      "escrow_id": "escrow-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "amount": 19.98,
      "food_fee": 16.98,
      "delivery_fee": 3.00,
      "status": "HELD",
      "created_at": "2025-03-21T06:37:00.000Z"
    }
  }
  ```

## Timer Service

### Start Request Timer
- **URL**: `http://localhost:3007/api/start-request-timer`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "customerId": "customer-uuid"
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "Timer started successfully",
    "timerId": "timer-uuid"
  }
  ```

### Stop Request Timer
- **URL**: `http://localhost:3007/api/stop-request-timer`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "runnerId": "runner-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Timer stopped successfully"
  }
  ```

### Cancel Timer
- **URL**: `http://localhost:3007/api/cancel-timer`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Timer cancelled successfully"
  }
  ```

### Check Order Timeout
- **URL**: `http://localhost:3007/api/check-order-timeout`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "No timed out orders found",
    "timedOutOrders": []
  }
  ```
  or
  ```json
  {
    "success": true,
    "message": "Found 1 timed out orders",
    "timedOutOrders": [
      {
        "orderId": "order-uuid",
        "timerId": "timer-uuid",
        "customerId": "customer-uuid",
        "createdAt": "2025-03-21T06:00:00.000Z"
      }
    ]
  }
  ```

### Get Timer by ID
- **URL**: `http://localhost:3007/api/timers/{timer_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "timer": {
      "timer_id": "timer-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "",
      "runner_accepted": false,
      "created_at": "2025-03-21T06:40:00.000Z"
    }
  }
  ```

### Get Timer by Order ID
- **URL**: `http://localhost:3007/api/timers/order/{order_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "timer": {
      "timer_id": "timer-uuid",
      "order_id": "order-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "",
      "runner_accepted": false,
      "created_at": "2025-03-21T06:40:00.000Z"
    }
  }
  ```

## Notification Service

### Send Notification
- **URL**: `http://localhost:3006/api/send-notification`
- **Method**: POST
- **Body**:
  ```json
  {
    "customerId": "customer-uuid",
    "runnerId": "runner-uuid",
    "orderId": "order-uuid",
    "event": "Your order has been accepted by a runner"
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "Notification created successfully",
    "notification": {
      "notification_id": "notification-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_id": "order-uuid",
      "event": "Your order has been accepted by a runner",
      "status": "SENT",
      "created_at": "2025-03-21T06:42:00.000Z",
      "sent_at": "2025-03-21T06:42:01.000Z"
    }
  }
  ```

### Send Order Accepted Notification
- **URL**: `http://localhost:3006/api/send-notification/order-accepted`
- **Method**: POST
- **Body**:
  ```json
  {
    "customerId": "customer-uuid",
    "runnerId": "runner-uuid",
    "orderId": "order-uuid",
    "runnerName": "John Runner"
  }
  ```
- **Expected Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "Order accepted notification sent successfully",
    "notification": {
      "notification_id": "notification-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_id": "order-uuid",
      "event": "Your order has been accepted by John Runner. They will pick up your order soon.",
      "status": "SENT",
      "created_at": "2025-03-21T06:43:00.000Z",
      "sent_at": "2025-03-21T06:43:01.000Z"
    }
  }
  ```

### Revert Notification
- **URL**: `http://localhost:3006/api/revert-notification`
- **Method**: POST
- **Body**:
  ```json
  {
    "orderId": "order-uuid",
    "event": "Update: Your order has been cancelled"
  }
  ```
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "Notification reverted successfully",
    "notification": {
      "notification_id": "new-notification-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_id": "order-uuid",
      "event": "Update: Your order has been cancelled",
      "status": "SENT",
      "created_at": "2025-03-21T06:44:00.000Z",
      "sent_at": "2025-03-21T06:44:01.000Z"
    }
  }
  ```

### Get Notification by ID
- **URL**: `http://localhost:3006/api/notifications/{notification_id}`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "notification": {
      "notification_id": "notification-uuid",
      "customer_id": "customer-uuid",
      "runner_id": "runner-uuid",
      "order_id": "order-uuid",
      "event": "Your order has been accepted by a runner",
      "status": "SENT",
      "created_at": "2025-03-21T06:42:00.000Z",
      "sent_at": "2025-03-21T06:42:01.000Z"
    }
  }
  ```

### Get Notifications (with filters)
- **URL**: `http://localhost:3006/api/notifications?customerId=customer-uuid&limit=10`
- **Method**: GET
- **Expected Response** (200 OK):
  ```json
  {
    "success": true,
    "notifications": [
      {
        "notification_id": "notification-uuid-1",
        "customer_id": "customer-uuid",
        "runner_id": "runner-uuid",
        "order_id": "order-uuid",
        "event": "Your order has been accepted by a runner",
        "status": "SENT",
        "created_at": "2025-03-21T06:42:00.000Z",
        "sent_at": "2025-03-21T06:42:01.000Z"
      },
      {
        "notification_id": "notification-uuid-2",
        "customer_id": "customer-uuid",
        "runner_id": "runner-uuid",
        "order_id": "order-uuid",
        "event": "Update: Your order has been cancelled",
        "status": "SENT",
        "created_at": "2025-03-21T06:44:00.000Z",
        "sent_at": "2025-03-21T06:44:01.000Z"
      }
    ]
  }
  ```

## End-to-End Workflows

### Complete Order Flow

1. Create a customer user:
   ```
   POST http://localhost:3001/api/users
   {
     "email": "customer@example.com",
     "firstName": "Jane",
     "lastName": "Customer",
     "phoneNumber": "+1234567890"
   }
   ```
   *Save the returned customer_id*

2. Add payment information:
   ```
   PUT http://localhost:3001/api/users/{customer_id}/payment
   {
     "cardLast4": "4242",
     "cardType": "Visa",
     "expiryMonth": "12",
     "expiryYear": "2025",
     "stripeToken": "tok_visa"
   }
   ```

3. Create a runner user:
   ```
   POST http://localhost:3001/api/users
   {
     "email": "runner@example.com",
     "firstName": "Bob",
     "lastName": "Runner",
     "phoneNumber": "+1987654321"
   }
   ```
   *Save the returned runner_id*

4. Create an order:
   ```
   POST http://localhost:3002/api/createOrder
   {
     "customerId": "{customer_id}",
     "orderDetails": {
       "items": [
         {"name": "Burger", "price": 9.99, "quantity": 2}
       ],
       "restaurant": "Burger Place",
       "deliveryAddress": "123 Campus Rd",
       "totalAmount": 19.98
     }
   }
   ```
   *Save the returned order_id*

5. Authorize payment (triggered by saga, but can be tested directly):
   ```
   POST http://localhost:3003/api/payments/authorize
   {
     "orderId": "{order_id}",
     "customerId": "{customer_id}",
     "amount": 19.98
   }
   ```

6. Move payment to escrow (triggered by saga, but can be tested directly):
   ```
   POST http://localhost:3003/api/payments/move-to-escrow
   {
     "orderId": "{order_id}"
   }
   ```

7. Hold funds in escrow (triggered by saga, but can be tested directly):
   ```
   POST http://localhost:3004/api/escrow/hold
   {
     "orderId": "{order_id}",
     "customerId": "{customer_id}",
     "amount": 19.98,
     "foodFee": 16.98,
     "deliveryFee": 3.00
   }
   ```

8. Start timer for runner acceptance (triggered by saga, but can be tested directly):
   ```
   POST http://localhost:3007/api/start-request-timer
   {
     "orderId": "{order_id}",
     "customerId": "{customer_id}"
   }
   ```

9. Runner accepts the order:
   ```
   POST http://localhost:3002/api/verifyAndAcceptOrder
   {
     "orderId": "{order_id}",
     "runnerId": "{runner_id}"
   }
   ```

10. Stop the request timer (triggered by Accept Order Saga, but can be tested directly):
    ```
    POST http://localhost:3007/api/stop-request-timer
    {
      "orderId": "{order_id}",
      "runnerId": "{runner_id}"
    }
    ```

11. Send notification to customer (triggered by Accept Order Saga, but can be tested directly):
    ```
    POST http://localhost:3006/api/send-notification/order-accepted
    {
      "customerId": "{customer_id}",
      "runnerId": "{runner_id}",
      "orderId": "{order_id}",
      "runnerName": "Bob Runner"
    }
    ```

12. Update order status to ON_SITE:
    ```
    POST http://localhost:3002/api/updateOrderStatus
    {
      "orderId": "{order_id}",
      "status": "ON_SITE"
    }
    ```

13. Update order status to ON_THE_WAY:
    ```
    POST http://localhost:3002/api/updateOrderStatus
    {
      "orderId": "{order_id}",
      "status": "ON_THE_WAY"
    }
    ```

14. Update order status to DELIVERED:
    ```
    POST http://localhost:3002/api/updateOrderStatus
    {
      "orderId": "{order_id}",
      "status": "DELIVERED"
    }
    ```

15. Complete the order:
    ```
    POST http://localhost:3002/api/completeOrder
    {
      "orderId": "{order_id}"
    }
    ```

16. Release funds from escrow (triggered by Complete Order Saga, but can be tested directly):
    ```
    POST http://localhost:3004/api/escrow/release
    {
      "orderId": "{order_id}",
      "runnerId": "{runner_id}"
    }
    ```

17. Update customer and runner ratings:
    ```
    POST http://localhost:3001/api/users/{customer_id}/update-customer-rating
    {
      "rating": 4.8
    }
    ```

    ```
    POST http://localhost:3001/api/users/{runner_id}/update-runner-rating
    {
      "rating": 4.9
    }
    ```

### Error Handling Workflows

#### Order Cancellation Flow

1. Create an order (steps 1-8 from Complete Order Flow)

2. Cancel the order:
   ```
   POST http://localhost:3002/api/cancelOrder
   {
     "orderId": "{order_id}"
   }
   ```

3. Refund funds from escrow:
   ```
   POST http://localhost:3004/api/escrow/refund
   {
     "orderId": "{order_id}"
   }
   ```

4. Cancel the timer:
   ```
   POST http://localhost:3007/api/cancel-timer
   {
     "orderId": "{order_id}"
   }
   ```

5. Send cancellation notification:
   ```
   POST http://localhost:3006/api/send-notification
   {
     "customerId": "{customer_id}",
     "orderId": "{order_id}",
     "event": "Your order has been cancelled."
   }
   ```

#### Runner Acceptance Cancellation Flow

1. Create an order and have a runner accept it (steps 1-11 from Complete Order Flow)

2. Runner cancels acceptance:
   ```
   POST http://localhost:3002/api/cancelAcceptance
   {
     "orderId": "{order_id}"
   }
   ```

3. Restart the request timer:
   ```
   POST http://localhost:3007/api/start-request-timer
   {
     "orderId": "{order_id}",
     "customerId": "{customer_id}"
   }
   ```

4. Send notification to customer:
   ```
   POST http://localhost:3006/api/revert-notification
   {
     "orderId": "{order_id}",
     "event": "Update: The runner had to cancel. Your order is available for other runners."
   }
   ```

#### Order Timeout Flow

1. Create an order (steps 1-8 from Complete Order Flow)

2. Check for timed out orders (typically called by a scheduler after 30 minutes):
   ```
   GET http://localhost:3007/api/check-order-timeout
   ```

3. When a timed-out order is found, cancel the order:
   ```
   POST http://localhost:3002/api/cancelOrder
   {
     "orderId": "{order_id}"
   }
   ```

4. Refund funds from escrow:
   ```
   POST http://localhost:3004/api/escrow/refund
   {
     "orderId": "{order_id}"
   }
   ```

5. Send timeout notification:
   ```
   POST http://localhost:3006/api/send-notification
   {
     "customerId": "{customer_id}",
     "orderId": "{order_id}",
     "event": "Your order has timed out. No runners were available. Your payment has been refunded."
   }
   ```

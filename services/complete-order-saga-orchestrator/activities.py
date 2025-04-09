import os # Added for environment variables
from temporalio import activity
from temporalio.exceptions import ApplicationError
from datetime import timedelta
import requests

# Activity to update order status in Order Service
@activity.defn
async def update_order_status(order_id: str, status: str) -> bool:
    order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    try:
        url = f"{order_service_url}/updateOrderStatus"
        response = requests.post(url, json={"orderId": order_id, "status": status})
        response.raise_for_status()
        print(f"Order {order_id} status updated to {status}")
        return True
    except Exception as e:
        print(f"Failed to update order {order_id} to {status}: {e}")
        attempt = activity.info().attempt
        raise ApplicationError(
            f"Error encountered on attempt {attempt}",
        ) from e
    
# @activity.defn
# async def rollback_update_order_status(order_id: str, status: str) -> bool:
#     order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
#     try:
#         url = f"{order_service_url}/updateOrderStatus"
#         response = requests.post(url, json={"orderId": order_id, "status": status})
#         response.raise_for_status()
#         print(f"Rollback successful: Order {order_id} status reverted to {status}")
#         return True
#     except Exception as e:
#         print(f"Failed to rollback order {order_id}: {e}")
#         return False

# Activity to get payment info from User Service
@activity.defn
async def get_user_stripe_connect(clerk_user_id: str) -> dict:
    user_service_url = os.getenv('USER_SERVICE_URL', 'http://localhost:3001')
    try:
        url = f"{user_service_url}/api/user/{clerk_user_id}/connect-account"
        response = requests.get(url)
        response.raise_for_status()
        payment_info = response.json()
        print(f"Retrieved payment info for user {clerk_user_id}")       
        return payment_info.get("stripe_connect_account_id")
    except Exception as e:
        print(f"Failed to get payment info for user {clerk_user_id}: {e}")
        return {}
    
@activity.defn
async def get_payment_status(order_id: str) -> str:
    payment_service_url = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:3003')
    try:
        url = f"{payment_service_url}/payment/{order_id}/status"
        response = requests.get(url)
        response.raise_for_status()
        response_json = response.json()

        # Extracting paymentId from the response
        payment_id = response_json.get("payment", {}).get("paymentId")
        
        if not payment_id:
            raise Exception(f"Payment ID not found for order {order_id}")
        
        print(f"Retrieved payment ID for order {order_id}: {payment_id}")
        return payment_id
    except Exception as e:
        print(f"Failed to get payment ID for order {order_id}: {e}")
        return None

# Activity to release funds via Payment Service
@activity.defn
async def release_funds(payment_id: str, clerk_user_id: str, stripe_connect_id: str) -> bool:
    payment_service_url = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:3003')
    try:
        url = f"{payment_service_url}/payment/{payment_id}/release"
        response = requests.post(url, json={"runner_id": clerk_user_id, "runner_connect_account_id": stripe_connect_id})
        response.raise_for_status()
        print(f"Funds released for {payment_id}")
        return True
    except Exception as e:
        print(f"Failed to release funds: {e}")
        return False

# Rollback Activity: Revert Released Funds
@activity.defn
async def rollback_release_funds(payment_id: str) -> bool:
    payment_service_url = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:3003')
    try:
        url = f"{payment_service_url}/payment/{payment_id}/revert"
        response = requests.post(url)
        response.raise_for_status()
        print(f"Rollback successful: Funds refunded for {payment_id}")
        return True
    except Exception as e:
        print(f"Failed to rollback funds: {e}")
        return False

from temporalio import activity
import requests

# Activity to update order status in Order Service
@activity.defn
async def update_order_status(order_id: str, status: str) -> bool:
    try:
        url = f"http://localhost:3002/updateOrderStatus"
        response = requests.post(url, json={"orderId": order_id, "status": status})
        response.raise_for_status()
        print(f"Order {order_id} status updated to {status}")
        return True
    except Exception as e:
        print(f"Failed to update order {order_id} to {status}: {e}")
        return False
    
@activity.defn
async def rollback_update_order_status(order_id: str, status: str) -> bool:
    try:
        url = f"http://localhost:3002/api/updateOrderStatus"
        response = requests.post(url, json={"orderId": order_id, "status": status})
        response.raise_for_status()
        print(f"Rollback successful: Order {order_id} status reverted to {status}")
        return True
    except Exception as e:
        print(f"Failed to rollback order {order_id}: {e}")
        return False

# Activity to get payment info from User Service
@activity.defn
async def get_user_payment_info(clerk_user_id: str) -> dict:
    try:
        url = f"http://localhost:3001/api/user/{clerk_user_id}/payment"
        response = requests.get(url)
        response.raise_for_status()
        payment_info = response.json()
        print(f"Retrieved payment info for user {clerk_user_id}")
        return payment_info
        # return '123456'
    except Exception as e:
        print(f"Failed to get payment info for user {clerk_user_id}: {e}")
        return {}

# Activity to release funds via Payment Service
@activity.defn
async def release_funds(payment_info: dict) -> bool:
# async def release_funds(clerk_user_id: str) -> bool:
    try:
        url = "http://localhost:3003/payment/{}/release"
        response = requests.post(url, json=payment_info)
        response.raise_for_status()
        print(f"Funds released for {payment_info}")
        return True
    except Exception as e:
        print(f"Failed to release funds: {e}")
        return False

# Rollback Activity: Revert Released Funds
@activity.defn
async def rollback_release_funds(payment_info: dict) -> bool:
    try:
        url = "http://localhost:3003/payment/{}/revert"
        response = requests.post(url, json=payment_info)
        response.raise_for_status()
        print(f"Rollback successful: Funds refunded for {payment_info}")
        return True
    except Exception as e:
        print(f"Failed to rollback funds: {e}")
        return False

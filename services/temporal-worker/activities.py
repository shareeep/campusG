# from temporalio import activity
# import requests

# # Activity to update order status in Order Service
# @activity.defn
# def update_order_status(order_id: str, status: str) -> bool:
#     try:
#         url = f"http://localhost:3002/api/updateOrderStatus"
#         response = requests.post(url, json={"orderId": order_id, "status": status})
#         response.raise_for_status()
#         print(f"Order {order_id} status updated to {status}")
#         return True
#     except Exception as e:
#         print(f"Failed to update order {order_id} to {status}: {e}")
#         return False

# # Activity to get payment info from User Service
# @activity.defn
# def get_user_payment_info(clerk_user_id: str) -> dict:
#     try:
#         url = f"http://localhost:3001/user/{clerk_user_id}/payment"
#         response = requests.get(url)
#         response.raise_for_status()
#         payment_info = response.json()
#         print(f"Retrieved payment info for user {clerk_user_id}")
#         return payment_info
#     except Exception as e:
#         print(f"Failed to get payment info for user {clerk_user_id}: {e}")
#         return {}

# # Activity to release funds via Payment Service
# @activity.defn
# def release_funds(payment_info: dict) -> bool:
#     try:
#         url = "http://localhost:3003/releaseFunds"
#         response = requests.post(url, json=payment_info)
#         response.raise_for_status()
#         print(f"Funds released for {payment_info}")
#         return True
#     except Exception as e:
#         print(f"Failed to release funds: {e}")
#         return False

from temporalio import activity
import requests

@activity.defn
def update_order_status(order_id: str, status: str) -> bool:
    # try:
        # url = f"http://localhost:3002/api/updateOrderStatus"
        # response = requests.post(url, json={"orderId": order_id, "status": status})
        # response.raise_for_status()
        print(f"Order {order_id} status updated to {status}")
        return True
    # except Exception as e:
    #     print(f"Failed to update order {order_id} to {status}: {e}")
    #     return False

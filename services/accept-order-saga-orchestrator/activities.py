import os # Added for environment variables
from temporalio import activity
import requests

# Activity 1: Verify and Accept Order via Order Service
@activity.defn
async def verify_and_accept_order(order_id: str, runner_id: str) -> bool:
    order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    try:
        print(f"Order {order_id} successfully verified and accepted.")
        print(f"what is going on")
        url = f"{order_service_url}/verifyAndAcceptOrder"
        response = requests.post(url, json={
        "orderId": f"{order_id}",
        "runner_id": f"{runner_id}"
        })
        response.raise_for_status()

        return True 
    #false for compensation testing
    except Exception as e:
        print(f"Failed to verify and accept order {order_id}: {e}")
        return False

#compensation for order status to return to CREATED
@activity.defn
async def revert_order_status(order_id: str) -> bool:
    order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://localhost:3002')
    try:
        url = f"{order_service_url}/clearRunner"
        response = requests.post(url, json={"orderId": order_id})
        response.raise_for_status()
        print(f"Order {order_id} status reverted to Created.")
        return True
    except Exception as e:
        print(f"Failed to revert order {order_id} to Created: {e}")
        return False

# Activity 2: Notify Timer Service of Order Acceptance
@activity.defn
async def notify_timer_service(order_id: str) -> bool:
    try:
        # url = "https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI/StopTimer"
        # response = requests.post(url, json={
        # response.raise_for_status()
        print(f"Order {order_id} successfully notified to Timer Service.")
        return True
    except Exception as e:
        print(f"Failed to notify Timer Service for order {order_id}: {e}")
        return False

# # Example of corrected code to call Timer Service (if uncommented):
# @activity.defn
# async def notify_timer_service(order_id: str, runner_id: str) -> bool: # Added runner_id parameter
#     timer_service_url = os.getenv('TIMER_SERVICE_URL', 'https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI/StopTimer') # Read from env var
#     try:
#         url = timer_service_url # Use the variable
#         response = requests.post(url, json={ # Uncommented and corrected JSON keys
#             "OrderId": order_id,
#             "RunnerId": runner_id
#         })
#         response.raise_for_status() # Uncommented
#         print(f"Timer Service notified successfully for order {order_id}.") # Updated print message
#         return True
#     except Exception as e:
#         print(f"Failed to notify Timer Service for order {order_id}: {e}")
#         return False

from temporalio import activity
import requests

# Activity 1: Verify and Accept Order via Order Service
@activity.defn
async def verify_and_accept_order(order_id: str, runner_id: str) -> bool:
    try:
        url = "http://localhost:3002/verifyAndAcceptOrder"
        response = requests.post(url, json={
        "orderId": f"{order_id}",
        "runner_id": f"{runner_id}"
    })
        response.raise_for_status()
        print(f"Order {order_id} successfully verified and accepted.")
        return True
    except Exception as e:
        print(f"Failed to verify and accept order {order_id}: {e}")
        return False

# Activity 2: Notify Timer Service of Order Acceptance
@activity.defn
async def notify_timer_service(order_id: str) -> bool:
    try:
        # url = "https://personal-7ndmvxwm.outsystemscloud.com/Timer_CS/rest/TimersAPI/StopTimer"
        # response = requests.post(url, json={
        #     "orderId": order_id,
        #     "runner_id": runner_id
        # })
        # response.raise_for_status()
        print(f"Order {order_id} successfully notified to Timer Service.")
        return True
    except Exception as e:
        print(f"Failed to notify Timer Service for order {order_id}: {e}")
        return False

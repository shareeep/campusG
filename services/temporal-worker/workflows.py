from temporalio import workflow
from datetime import timedelta
with workflow.unsafe.imports_passed_through():
    from activities import update_order_status, get_user_payment_info, release_funds

@workflow.defn
class CompleteOrderWorkflow:
    @workflow.run
    async def run(self, order_id: str, clerk_user_id: str):
        # Step 2: Update order status to 'Delivered'
        updated = await workflow.execute_activity(
            update_order_status,
            order_id,
            "Delivered",
            start_to_close_timeout=timedelta(seconds=10)
        )
        if not updated:
            raise Exception("Failed to update order to Delivered")

        # Step 3: Get user payment info
        payment_info = await workflow.execute_activity(
            get_user_payment_info,
            clerk_user_id,
            start_to_close_timeout=timedelta(seconds=10)
        )
        if not payment_info:
            raise Exception("Failed to retrieve payment info")

        # Step 4: Release funds
        # funds_released = await workflow.execute_activity(
        #     "release_funds",
        #     payment_info,
        #     start_to_close_timeout=timedelta(seconds=10)
        # )
        # if not funds_released:
        #     raise Exception("Failed to release funds")

        # Step 5: Update order status to 'Completed'
        completed = await workflow.execute_activity(
            update_order_status,
            order_id,
            "Completed",
            start_to_close_timeout=timedelta(seconds=10)
        )
        if not completed:
            raise Exception("Failed to update order to Completed")

        print(f"Order {order_id} processed successfully")
        return "Order Completed"

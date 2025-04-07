from temporalio import workflow
from datetime import timedelta

@workflow.defn
class CompleteOrderWorkflow:
    @workflow.run
    async def run(self, input_data:dict) -> str :
        order_id = input_data.get("order_id", "Unknown")
        clerk_user_id = input_data.get("clerk_user_id", "Unknown")
        payment_info = None
        try:
            # Step 2: Update order status to 'Delivered'
            updated = await workflow.execute_activity(
                "update_order_status",  # Activity name must be a string
                args=[order_id, "DELIVERED"],
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not updated:
                raise Exception("Failed to update order to Delivered")
            
            payment_info = await workflow.execute_activity(
                "get_user_payment_info",
                clerk_user_id,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not payment_info:
                raise Exception("Failed to retrieve payment info")
            
            funds_released = await workflow.execute_activity(
                "release_funds",
                payment_info,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not funds_released:
                raise Exception("Failed to release funds")
            
                    # Step 2: Update order status to 'Delivered'
            updated = await workflow.execute_activity(
                "update_order_status",  # Activity name must be a string
                args=[order_id, "COMPLETED"],
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not updated:
                raise Exception("Failed to update order to Completed")

            print(f"Order {order_id} processed successfully")
            return "Order Completed"
        except Exception as e:
            print(f"Error occurred: {e}. Triggering rollback...")
            # Rollback Step 1: Mark order as 'CANCELLED'
            await workflow.execute_activity(
                "rollback_update_order_status",
                order_id,
                "CANCELLED",
                start_to_close_timeout=timedelta(seconds=10)
            )

            # Rollback Step 2: Reverse funds release if it was processed
            if payment_info:
                await workflow.execute_activity(
                    "rollback_release_funds",
                    payment_info,
                    start_to_close_timeout=timedelta(seconds=10)
                )

            return f"Order {order_id} failed and rollback initiated."


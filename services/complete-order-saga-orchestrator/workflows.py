from temporalio import workflow
from datetime import timedelta
# with workflow.unsafe.imports_passed_through():
#     from activities import {
#         rollback_update_order_status,
#         rollback_release_funds
#     }

class Compensations:
    def __init__(self):
        self.compensations = []

    def __iadd__(self, compensation):
        self.compensations.append(compensation)
        return self
        
    async def compensate(self):
        for compensation in reversed(self.compensations):
            try:
                await workflow.execute_activity(
                    compensation["activity"],
                    args=[*compensation["args"]],
                    start_to_close_timeout=timedelta(seconds=10)
                )
            except Exception as e:
                print(f"Compensation failed for {compensation['activity']} with args {compensation['args']}: {e}")

@workflow.defn
class CompleteOrderWorkflow:
    @workflow.run
    async def run(self, input_data:dict) -> str :
        order_id = input_data.get("order_id", "Unknown")
        clerk_user_id = input_data.get("clerk_user_id", "Unknown")
        compensation = Compensations()
        try:
            # Removed redundant update to 'DELIVERED' status.
            # Workflow assumes order is already DELIVERED when triggered.
            # Removed corresponding compensation for the DELIVERED update.

            stripe_connect_id = await workflow.execute_activity(
                "get_user_stripe_connect",
                clerk_user_id,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not stripe_connect_id:
                raise Exception("Failed to retrieve payment info")
            
            payment_id = await workflow.execute_activity(
                "get_payment_status",
                order_id,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not payment_id:
                raise Exception("Failed to retrieve payment id")

            compensation += {
                                "activity": "rollback_release_funds",
                                "args": (payment_id)
                            }
            funds_released = await workflow.execute_activity(
                "release_funds",
                args = [payment_id, clerk_user_id, stripe_connect_id],
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not funds_released:
                raise Exception("Failed to release funds")

            # Add compensation for the COMPLETED status update
            # If completion fails, roll back status (e.g., to DELIVERED)
            compensation += {
                                "activity": "rollback_update_order_status",
                                "args": (order_id, "DELIVERED") # Rollback COMPLETED to DELIVERED
                            }
            # Update order status to 'COMPLETED'
            updated = await workflow.execute_activity(
                "update_order_status",
                args=[order_id, "COMPLETED"], # Final status update
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not updated:
                raise Exception("Failed to update order to Completed")

            print(f"Order {order_id} processed successfully")
            return "Order Completed"
        except Exception as e:
            print(f"Error occurred: {e}. Triggering rollback...")
            await compensation.compensate()

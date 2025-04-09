from temporalio import workflow
from datetime import timedelta


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
        clerk_user_id = input_data.get("clerk_user_id", "Unknown") # Corrected indent
        compensation = Compensations() # Corrected indent
        try: # Corrected indent
            # Removed redundant update to 'DELIVERED' status.
            # Workflow assumes order is already DELIVERED when triggered.
            # Removed corresponding compensation for the DELIVERED update.

            stripe_connect_id = await workflow.execute_activity( # Corrected indent
                "get_user_stripe_connect",
                clerk_user_id,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not stripe_connect_id: # Corrected indent
                raise Exception("Failed to retrieve payment info") # Corrected indent

            payment_id = await workflow.execute_activity( # Corrected indent
                "get_payment_status",
                order_id,
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not payment_id: # Corrected indent
                raise Exception("Failed to retrieve payment id") # Corrected indent

            compensation += { # Corrected indent
                                "activity": "rollback_release_funds",
                                "args": (payment_id)
                            }
            funds_released = await workflow.execute_activity( # Corrected indent
                "release_funds",
                args = [payment_id, clerk_user_id, stripe_connect_id],
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not funds_released: # Corrected indent
                raise Exception("Failed to release funds") # Corrected indent

            # Add compensation for the COMPLETED status update
            # If completion fails, roll back status (e.g., to DELIVERED)
            # compensation += { # Corrected indent
            #                     "activity": "rollback_update_order_status",
            #                     "args": (order_id, "DELIVERED") # Rollback COMPLETED to DELIVERED
            #                 }
            # Update order status to 'COMPLETED'
            updated = await workflow.execute_activity( # Corrected indent
                "update_order_status",
                args=[order_id, "COMPLETED"], # Final status update
                start_to_close_timeout=timedelta(seconds=10)
            )
            if not updated: # Corrected indent
                raise Exception("Failed to update order to Completed") # Corrected indent

            print(f"Order {order_id} processed successfully") # Corrected indent
            return "Order Completed" # Corrected indent
        except Exception as e: # Corrected indent
            print(f"Error occurred: {e}. Triggering rollback...") # Corrected indent
            await compensation.compensate() # Corrected indent

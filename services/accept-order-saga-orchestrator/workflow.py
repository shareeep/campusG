from temporalio import workflow
from datetime import timedelta
with workflow.unsafe.imports_passed_through():
    from activities import verify_and_accept_order, notify_timer_service, revert_order_status, cancel_timer


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
                    *compensation["args"],
                    start_to_close_timeout=timedelta(seconds=10)
                )
            except Exception as e:
                print(f"Compensation failed for {compensation['activity']} with args {compensation['args']}: {e}")

@workflow.defn
class AcceptOrderWorkflow:
    @workflow.run
    async def run(self, input_data:dict) -> str:
        compensations = Compensations()
        order_id = input_data.get("order_id", "Unknown")
        runner_id = input_data.get("runner_id", "Unknown")
        try:
        # Step 1: Verify and Accept Order
            order_accepted = await workflow.execute_activity(
                verify_and_accept_order,
                args=[order_id, runner_id],
                start_to_close_timeout=timedelta(seconds=10)
            )

            if not order_accepted:
                raise Exception("Failed to verify and accept order.")

            # Step 2: Notify Timer Service
            timer_notified = await workflow.execute_activity(
                notify_timer_service,
                order_id,
                start_to_close_timeout=timedelta(seconds=10)
            )

            if not timer_notified:
                raise Exception("Failed to notify Timer Service.")

            return f"Order {order_id} successfully accepted and timer notified."
        except Exception as e:
            print(f"Workflow failed, triggering compensation: {e}")
            await compensations.compensate()
            # raise e

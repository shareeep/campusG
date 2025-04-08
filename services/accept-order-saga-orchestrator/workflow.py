from temporalio import workflow
from datetime import timedelta
with workflow.unsafe.imports_passed_through():
    from activities import verify_and_accept_order, notify_timer_service

@workflow.defn
class AcceptOrderWorkflow:
    @workflow.run
    async def run(self, input_data:dict) -> str:
        order_id = input_data.get("order_id", "Unknown")
        runner_id = input_data.get("runner_id", "Unknown")
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

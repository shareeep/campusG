from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import workflow
import asyncio

# Define your workflow
@workflow.defn
class CompleteOrderWorkflow:
    @workflow.run
    async def run(self, order_id: dict) -> str:
        print(f"Processing order {order_id}")
        return f"Order {order_id} processed successfully!"

async def main():
    # Connect to the Temporal Server running on Docker (localhost:7233)
    client = await Client.connect("127.0.0.1:7233")

    # Start your worker
    worker = Worker(
        client,
        task_queue="complete-order-task-queue",
        workflows=[CompleteOrderWorkflow],
    )
    
    print("Starting Worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

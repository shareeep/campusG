from temporalio.client import Client
from temporalio.worker import Worker
from workflows import CompleteOrderWorkflow
from activities import update_order_status, get_user_payment_info, release_funds
import asyncio
import concurrent.futures

async def main():
    client = await Client.connect("localhost:7233")

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="complete-order-queue",
            workflows=[CompleteOrderWorkflow],
            activities=[update_order_status, get_user_payment_info, release_funds],
            activity_executor=activity_executor
        )
        print("Starting Worker...")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

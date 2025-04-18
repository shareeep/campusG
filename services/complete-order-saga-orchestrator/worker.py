import os # Added for environment variables
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import CompleteOrderWorkflow
from activities import update_order_status, get_user_stripe_connect, get_payment_status, release_funds, rollback_release_funds
import asyncio
import concurrent.futures

async def main():
    # Read Temporal endpoint from environment variable, default for local running
    temporal_endpoint = os.getenv('TEMPORAL_GRPC_ENDPOINT', 'localhost:7233')
    client = await Client.connect(temporal_endpoint)

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="complete-order-queue",
            workflows=[CompleteOrderWorkflow],
            activities=[update_order_status, get_user_stripe_connect, get_payment_status, release_funds,
            rollback_release_funds],
            activity_executor=activity_executor
        )
        print("Starting Worker...")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

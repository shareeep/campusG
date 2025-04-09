import os # Added for environment variables
from temporalio.client import Client
from temporalio.worker import Worker
from workflow import AcceptOrderWorkflow
from activities import (verify_and_accept_order, notify_timer_service, revert_order_status)
import asyncio
import concurrent.futures
from datetime import timedelta

async def main():
    # Read Temporal endpoint from environment variable, default for local running
    temporal_endpoint = os.getenv('TEMPORAL_GRPC_ENDPOINT', 'localhost:7233')
    client = await Client.connect(temporal_endpoint)

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="accept-order-task-queue",
            workflows=[AcceptOrderWorkflow],
            activities=[verify_and_accept_order, notify_timer_service, revert_order_status],
            activity_executor=activity_executor
        )
        print("Starting Worker...")
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

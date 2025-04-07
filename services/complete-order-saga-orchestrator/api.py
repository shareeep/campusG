from flask import Flask, request, jsonify
from temporalio.client import Client
import asyncio
from workflows import CompleteOrderWorkflow

app = Flask(__name__)

async def start_workflow(order_id: str, clerk_user_id: str):
    client = await Client.connect("temporal:7233", namespace="default")
    handle = await client.execute_workflow(
        CompleteOrderWorkflow.run,
        order_id,
        clerk_user_id,
        id=f"complete-order-{order_id}",
        task_queue="complete-order-queue"
    )
    result = await handle.result()
    print('heloo')
    return result

@app.route('/updateOrderStatus', methods=['POST'])
def update_order_status():
    data = request.json
    order_id = data.get('order_id')
    clerk_user_id = data.get('clerk_user_id')

    if not order_id or not clerk_user_id:
        return jsonify({"error": "Missing order_id or clerk_user_id"}), 400

    result = asyncio.run(start_workflow(order_id, clerk_user_id))
    return jsonify({"message": "Workflow started", "result": result}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)


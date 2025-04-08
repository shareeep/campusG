from temporalio.client import Client
from flask import Flask, request, jsonify
import asyncio
from workflow import AcceptOrderWorkflow
from datetime import timedelta

app = Flask(__name__)

# Define the async function to start the workflow
async def trigger_workflow(input_data):
    order_id = input_data.get("order_id")
    client = await Client.connect("localhost:7233")  # Connect to your Temporal server

    result = await client.start_workflow(
        AcceptOrderWorkflow.run,  # Refer to the actual workflow function here
        input_data,  # This is passed as a positional argument, not a keyword argument
        id=f"accept-order-workflow-{order_id}",  # Unique ID for the workflow
        task_queue="accept-order-task-queue",
        execution_timeout=timedelta(seconds=5)
    )
    return result.id

# Define a Flask route to trigger the workflow
@app.route('/acceptOrder', methods=['POST'])
def trigger():
    input_data = request.json  # Get the JSON input from the request
    order_id = input_data.get("order_id")
    runner_id = input_data.get("runner_id")
    if not input_data or not order_id or not runner_id:
        return jsonify({"error": "Missing required fields: order_id and runner_id"}), 400

    try:
        workflow_id = asyncio.run(trigger_workflow(input_data))  # Trigger the workflow
        return jsonify({"message": "Workflow triggered", "workflow_id": workflow_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)

from temporalio.client import Client
from flask import Flask, request, jsonify
import asyncio
from workflows import CompleteOrderWorkflow
from datetime import timedelta

app = Flask(__name__)

# Define the async function to start a workflow
async def trigger_workflow(input_data):
    order_id = input_data.get("order_id")
    client = await Client.connect("localhost:7233")  # Connect to your Temporal server
    
    result = await client.start_workflow(
        CompleteOrderWorkflow.run,  # Note: Refer to the actual workflow function here
        input_data,  # This should be passed as a positional argument, not a keyword argument
        id=f"complete-order-workflow-{order_id}",  # Unique ID for the workflow
        task_queue="complete-order-queue",
        execution_timeout=timedelta(seconds=5)
    )
    return result.id

# Define a Flask route to trigger the workflow
@app.route('/triggerCompleteOrderWorkflow', methods=['POST'])
def trigger():
    input_data = request.json  # Get the JSON input from the request
    workflow_id = asyncio.run(trigger_workflow(input_data))  # Trigger the workflow
    
    return jsonify({"message": "Workflow triggered", "workflow_id": workflow_id})

if __name__ == "__main__":
    app.run(port=5000, debug=True)

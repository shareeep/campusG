import os # Added for environment variables
from temporalio.client import Client
from flask import Flask, request, jsonify
import asyncio
from workflows import CompleteOrderWorkflow
from datetime import timedelta

app = Flask(__name__)

# Define the async function to start a workflow
async def trigger_workflow(input_data):
    order_id = input_data.get("order_id")
    # Read Temporal endpoint from environment variable, default for local running
    temporal_endpoint = os.getenv('TEMPORAL_GRPC_ENDPOINT', 'localhost:7233')
    client = await Client.connect(temporal_endpoint)
    
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

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # Read DEBUG flag from environment variable, default to False for production
    debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=5000, debug=debug_mode) # Listen on all interfaces

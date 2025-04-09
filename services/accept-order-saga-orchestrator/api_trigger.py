import os # Added for environment variables
from temporalio.client import Client
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import asyncio
from workflow import AcceptOrderWorkflow
from datetime import timedelta

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"]) # Enable CORS for the frontend origin

# Define the async function to start the workflow
async def trigger_workflow(input_data):
    order_id = input_data.get("order_id")
    # Read Temporal endpoint from environment variable, default for local running
    temporal_endpoint = os.getenv('TEMPORAL_GRPC_ENDPOINT', 'localhost:7233')
    client = await Client.connect(temporal_endpoint)

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
        # Log the exception for debugging
        print(f"Error triggering workflow: {e}")
        activity.logger.exception("Failed to trigger workflow") # Use activity logger if available, otherwise standard print/logging
        return jsonify({"error": "Failed to trigger workflow"}), 500

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # Read DEBUG flag from environment variable, default to False
    debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    # Run on port 3000 to match Dockerfile EXPOSE and docker-compose mapping
    app.run(host='0.0.0.0', port=3000, debug=debug_mode)

import os # Added for environment variables
from temporalio.client import Client
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
from flasgger import Swagger, swag_from # Import Swagger
import asyncio
from workflows import CompleteOrderWorkflow
from datetime import timedelta

app = Flask(__name__)
swagger = Swagger(app) # Initialize Flasgger
# More explicit CORS configuration
CORS(
    app,
    origins=["http://localhost:5173"],
    methods=["GET", "POST", "OPTIONS"], # Allow relevant methods + OPTIONS
    allow_headers=["Content-Type", "Authorization"], # Allow common headers
    supports_credentials=True # Allow cookies if needed
)

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
@swag_from({
    'tags': ['Workflow Trigger'],
    'summary': 'Trigger the Complete Order Temporal Workflow.',
    'description': 'Starts the asynchronous Complete Order workflow in Temporal.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'description': 'Input data for the workflow, typically including order_id and runner_id.',
            'schema': {
                'type': 'object',
                'properties': {
                    'order_id': {'type': 'string', 'format': 'uuid'},
                    'runner_id': {'type': 'string'}
                    # Add other necessary fields based on workflow input requirements
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Workflow triggered successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'workflow_id': {'type': 'string'}
                }
            }
        },
        '500': {'description': 'Internal Server Error (failed to trigger workflow)'}
    }
})
def trigger():
    input_data = request.json  # Get the JSON input from the request
    workflow_id = asyncio.run(trigger_workflow(input_data))  # Trigger the workflow
    
    return jsonify({"message": "Workflow triggered", "workflow_id": workflow_id})

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check for the Complete Order API Trigger.',
    'responses': {
        '200': {
            'description': 'Service is healthy.',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'healthy'}
                }
            }
        }
    }
})
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # Read DEBUG flag from environment variable, default to False for production
    debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=5000, debug=debug_mode) # Listen on all interfaces

import requests
import sys
import json
import time
import uuid

def test_complete_order(order_id=None):
    """
    Test the complete order saga flow with a stub for release funds.
    
    Args:
        order_id (str, optional): The ID of the order to complete. If not provided, generates a UUID.
        
    Returns:
        bool: True if the saga completes successfully, False otherwise.
    """
    if not order_id:
        order_id = str(uuid.uuid4())
        print(f"No order ID provided. Using generated ID: {order_id}")
    
    print(f"Testing complete order saga for order {order_id}")
    
    # Start the saga
    try:
        response = requests.post(
            "http://localhost:3000/saga/complete/completeOrder",
            json={"orderId": order_id},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"Failed to start saga: {response.text}")
            return False
        
        data = response.json()
        saga_id = data["sagaId"]
        print(f"Saga started with ID: {saga_id}")
    except Exception as e:
        print(f"Error starting saga: {str(e)}")
        return False
    
    # Monitor saga progress
    print("Monitoring saga progress...")
    success = False
    for i in range(10):  # Try for up to 10 iterations (20 seconds)
        try:
            status_response = requests.get(f"http://localhost:3000/saga/complete/orderUpdateStream/{saga_id}", 
                                          stream=True, timeout=2)
            
            # Read and process the SSE stream for a short time
            for line in status_response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    event_data = json.loads(line[6:])  # Skip 'data: ' prefix and parse JSON
                    status = event_data.get('status')
                    print(f"Current saga status: {status}")
                    
                    if status == "COMPLETED":
                        print("Saga completed successfully!")
                        success = True
                        return True
                    elif status == "FAILED":
                        error = event_data.get('error', 'Unknown error')
                        print(f"Saga failed: {error}")
                        return False
                    
                    # Break after processing one event
                    break
            
            # Close the stream and sleep before checking again
            status_response.close()
        except Exception as e:
            print(f"Error checking saga status: {str(e)}")
        
        # If we've already determined success or failure, break the loop
        if success or (status and status == "FAILED"):
            break
            
        print(f"Waiting for saga to complete... (attempt {i+1}/10)")
        time.sleep(2)  # Wait 2 seconds between status checks
    
    print("Saga did not complete within the expected time.")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_complete_order.py <order_id>")
        print("If no order_id is provided, a random UUID will be generated.")
        order_id = None
    else:
        order_id = sys.argv[1]
        
    success = test_complete_order(order_id)
    sys.exit(0 if success else 1)

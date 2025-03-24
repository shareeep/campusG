"""
User Service - Entry point for the Flask application.
"""
import os
from app import create_app

app = create_app()

@app.route('/', methods=['GET'])
def index():
    """Root endpoint for basic health checking"""
    return {'service': 'user-service', 'status': 'online'}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)

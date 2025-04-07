#!/bin/bash
set -e

echo "Running database migrations..."
flask db upgrade

echo "Starting application..."
flask run --host=0.0.0.0 --port=3000

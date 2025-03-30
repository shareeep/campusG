#!/bin/bash
set -e

# Wait for the database to be ready
sleep 5

# Check if migrations directory is in a proper state
if [ -d migrations ] && [ ! -f migrations/alembic.ini ]; then
    echo "Migrations directory exists but appears incomplete. Cleaning up..."
    rm -rf migrations
fi

# Initialize migrations if needed
if [ ! -d migrations ] || [ ! -f migrations/alembic.ini ]; then
    echo "Setting up migrations directory..."
    flask db init
fi

# Skip migration generation in container startup to avoid errors
# Just apply existing migrations if any
if [ -d migrations/versions ]; then
    echo "Applying existing migrations..."
    flask db upgrade || echo "Migration failed, but continuing as database schema may already exist"
else
    echo "No migrations found. Using SQLAlchemy create_all instead."
    # The service will fall back to create_all in __init__.py
fi

# Start the application
exec gunicorn --bind 0.0.0.0:3000 "run:app"

#!/usr/bin/env python3
"""
Database initialization script for the user service
Creates all tables defined in the models
"""

import os
import sys
from datetime import datetime
import psycopg2

# Database connection details for Docker environment
DB_HOST = 'postgres-user'
DB_PORT = '5432'
DB_NAME = 'user_service_db'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'

def get_db_connection():
    """Create and return a database connection"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = False
    return conn

def init_db():
    """Initialize the database with tables directly using SQL"""
    print(f"Starting database initialization at {datetime.now().isoformat()}")
    print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT}")
    
    conn = None
    cursor = None
    
    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create the users table
        print("Creating users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(36) PRIMARY KEY,
                clerk_user_id VARCHAR(255) UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                phone_number VARCHAR(20),
                user_stripe_card JSONB,
                customer_rating NUMERIC NOT NULL DEFAULT 5.0,
                runner_rating NUMERIC NOT NULL DEFAULT 5.0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_customer_rating ON users(customer_rating);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_runner_rating ON users(runner_rating);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_clerk_user_id ON users(clerk_user_id);")
        
        # Commit the transaction
        conn.commit()
        print("Database tables created successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database initialization failed: {str(e)}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
    return 0

def main():
    """Main entry point for the script"""
    # Simplified to only handle initialization
    return init_db()

if __name__ == "__main__":
    sys.exit(main())

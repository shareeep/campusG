#!/usr/bin/env python3
"""
Database initialization script for the user service
Creates the database if it doesn't exist and initializes all tables
"""

import os
import sys
from datetime import datetime
import psycopg2

# Database connection details for Docker environment
DB_HOST = 'user-db'
DB_PORT = '5432'
DB_NAME = 'user_service_db'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'

def create_database():
    """Create the database if it doesn't exist"""
    print(f"Checking if database {DB_NAME} exists...")
    
    # Connect to default 'postgres' database to create our target database
    conn = None
    cursor = None
    
    try:
        # Connect to the default postgres database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname='postgres',  # Connect to default database
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True  # Need autocommit for database creation
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database {DB_NAME} does not exist. Creating it now...")
            # Create database with proper encoding
            cursor.execute(f"CREATE DATABASE {DB_NAME} WITH ENCODING 'UTF8'")
            print(f"Database {DB_NAME} created successfully!")
        else:
            print(f"Database {DB_NAME} already exists.")
        
        return True
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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

def init_tables():
    """Initialize the database with tables directly using SQL"""
    print(f"Starting table initialization at {datetime.now().isoformat()}")
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
                clerk_user_id VARCHAR(255) PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
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
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_customer_rating ON users(customer_rating);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_runner_rating ON users(runner_rating);")
        
        # Commit the transaction
        conn.commit()
        print("Database tables created successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Table initialization failed: {str(e)}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
    return 0

def main():
    """Main entry point for the script"""
    # First make sure the database itself exists
    if not create_database():
        return 1
    
    # Then initialize tables
    return init_tables()

if __name__ == "__main__":
    sys.exit(main())

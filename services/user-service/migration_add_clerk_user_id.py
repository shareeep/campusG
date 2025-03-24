#!/usr/bin/env python3
"""
Migration script to add clerk_user_id column to the users table
"""

import os
import sys
from datetime import datetime
import psycopg2
from psycopg2 import sql

# Database connection details - should match your existing configuration
# Database connection details for Docker environment
DB_HOST = 'postgres-user'
DB_PORT = '5432'
DB_NAME = 'user_service_db'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'

def migrate():
    """Run the migration to add clerk_user_id column"""
    print(f"Starting migration at {datetime.now().isoformat()}")
    print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT}")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='clerk_user_id';
        """)
        
        if cursor.fetchone():
            print("Column clerk_user_id already exists in users table. Skipping.")
        else:
            print("Adding clerk_user_id column to users table...")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE users ADD COLUMN clerk_user_id VARCHAR(255);
            """)
            
            # Create index
            cursor.execute("""
                CREATE UNIQUE INDEX ix_users_clerk_user_id ON users(clerk_user_id);
            """)
            
            print("Column and index created successfully.")
        
        # Commit transaction
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Migration failed: {str(e)}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(migrate())

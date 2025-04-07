"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM types first
    op.execute("CREATE TYPE sagastatus AS ENUM ('STARTED', 'COMPLETED', 'FAILED', 'COMPENSATING', 'COMPENSATED')")
    op.execute("CREATE TYPE sagastep AS ENUM ('GET_USER_DATA', 'CREATE_ORDER', 'AUTHORIZE_PAYMENT', 'HOLD_FUNDS', 'UPDATE_ORDER_STATUS', 'START_TIMER', 'NOTIFY_USER')")
    
    # Create the table using the ENUM types and appropriate PG types
    op.create_table('create_order_saga_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=True),
        sa.Column('status', sa.Enum('STARTED', 'COMPLETED', 'FAILED', 'COMPENSATING', 'COMPENSATED', name='sagastatus'), 
                 nullable=False, server_default='STARTED'),
        sa.Column('current_step', sa.Enum('GET_USER_DATA', 'CREATE_ORDER', 'AUTHORIZE_PAYMENT', 'HOLD_FUNDS', 
                                          'UPDATE_ORDER_STATUS', 'START_TIMER', 'NOTIFY_USER', name='sagastep'), 
                 nullable=True),
        sa.Column('error', sa.String(255), nullable=True),
        sa.Column('order_details', JSONB, nullable=False),
        sa.Column('payment_amount', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create the trigger function for automatically updating 'updated_at'
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql'
    """)
    
    # Apply the trigger to the table
    op.execute("""
    CREATE TRIGGER update_create_order_saga_states_updated_at
    BEFORE UPDATE ON create_order_saga_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade():
    # Drop the trigger first
    op.execute("DROP TRIGGER IF EXISTS update_create_order_saga_states_updated_at ON create_order_saga_states")
    
    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop the table
    op.drop_table('create_order_saga_states')
    
    # Drop the ENUM types
    op.execute("DROP TYPE IF EXISTS sagastep")
    op.execute("DROP TYPE IF EXISTS sagastatus")

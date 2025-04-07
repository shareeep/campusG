"""Initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2023-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create saga status enum type
    op.execute("CREATE TYPE sagastatus AS ENUM ('STARTED', 'COMPLETED', 'FAILED', 'COMPENSATING', 'COMPENSATED')")
    
    # Create saga step enum type
    op.execute("CREATE TYPE sagastep AS ENUM ('COMPLETE_ORDER')")

    # Create complete_order_saga_states table
    op.create_table(
        'complete_order_saga_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('STARTED', 'COMPLETED', 'FAILED', 'COMPENSATING', 'COMPENSATED', 
                                  name='sagastatus', create_type=False), nullable=False),
        sa.Column('current_step', sa.Enum('COMPLETE_ORDER', name='sagastep', create_type=False), nullable=True),
        sa.Column('error', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True)
    )
    
    # Create index on order_id for quick lookups
    op.create_index(op.f('ix_complete_order_saga_states_order_id'), 'complete_order_saga_states', ['order_id'], unique=True)


def downgrade():
    # Drop table and indices
    op.drop_index(op.f('ix_complete_order_saga_states_order_id'), table_name='complete_order_saga_states')
    op.drop_table('complete_order_saga_states')
    
    # Drop enum types
    op.execute("DROP TYPE sagastatus")
    op.execute("DROP TYPE sagastep")

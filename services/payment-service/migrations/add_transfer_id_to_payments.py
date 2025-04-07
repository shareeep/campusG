"""add_transfer_id_to_payments

Revision ID: add_transfer_id_to_payments
Revises: 
Create Date: 2025-04-05

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('payments', sa.Column('transfer_id', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('payments', 'transfer_id')

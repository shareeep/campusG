"""add_stripe_connect_account_id

Revision ID: add_stripe_connect_account_id
Revises: 
Create Date: 2025-04-05

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('users', sa.Column('stripe_connect_account_id', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('users', 'stripe_connect_account_id')

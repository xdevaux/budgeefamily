"""create_transactions_table

Revision ID: c798c1fce9b0
Revises: a63204724278
Create Date: 2026-01-18 14:12:58.029744

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c798c1fce9b0'
down_revision = 'a63204724278'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('is_positive', sa.Boolean(), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=True),
        sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'], unique=False)
    op.create_index('ix_transactions_transaction_date', 'transactions', ['transaction_date'], unique=False)
    op.create_index('ix_transactions_status', 'transactions', ['status'], unique=False)


def downgrade():
    op.drop_index('ix_transactions_status', table_name='transactions')
    op.drop_index('ix_transactions_transaction_date', table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_table('transactions')

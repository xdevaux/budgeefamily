"""add_is_pointed_field_to_transactions

Revision ID: a63204724278
Revises: de28f2685e23
Create Date: 2026-01-18 13:56:27.686658

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a63204724278'
down_revision = 'de28f2685e23'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter le champ is_pointed aux tables revenues, subscriptions, credits et installment_payments
    op.add_column('revenues', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('credits', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('installment_payments', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Supprimer le champ is_pointed des tables
    op.drop_column('installment_payments', 'is_pointed')
    op.drop_column('credits', 'is_pointed')
    op.drop_column('subscriptions', 'is_pointed')
    op.drop_column('revenues', 'is_pointed')

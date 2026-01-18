"""remove_is_pointed_from_other_tables

Revision ID: 5697eac69a5c
Revises: c798c1fce9b0
Create Date: 2026-01-18 14:13:53.715391

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5697eac69a5c'
down_revision = 'c798c1fce9b0'
branch_labels = None
depends_on = None


def upgrade():
    # Supprimer le champ is_pointed des tables revenues, subscriptions, credits et installment_payments
    op.drop_column('revenues', 'is_pointed')
    op.drop_column('subscriptions', 'is_pointed')
    op.drop_column('credits', 'is_pointed')
    op.drop_column('installment_payments', 'is_pointed')


def downgrade():
    # Rajouter le champ is_pointed si besoin de rollback
    op.add_column('installment_payments', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('credits', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('subscriptions', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('revenues', sa.Column('is_pointed', sa.Boolean(), nullable=False, server_default='0'))

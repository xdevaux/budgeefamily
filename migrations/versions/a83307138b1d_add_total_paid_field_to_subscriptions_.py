"""add total_paid field to subscriptions credits and revenues

Revision ID: a83307138b1d
Revises: 6ab63faa557b
Create Date: 2026-01-16 19:13:36.668971

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a83307138b1d'
down_revision = '6ab63faa557b'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter le champ total_paid aux abonnements
    op.add_column('subscriptions', sa.Column('total_paid', sa.Float(), nullable=False, server_default='0.0'))

    # Ajouter le champ total_paid aux crédits
    op.add_column('credits', sa.Column('total_paid', sa.Float(), nullable=False, server_default='0.0'))

    # Ajouter le champ total_paid aux revenus
    op.add_column('revenues', sa.Column('total_paid', sa.Float(), nullable=False, server_default='0.0'))


def downgrade():
    # Supprimer le champ total_paid des revenus
    op.drop_column('revenues', 'total_paid')

    # Supprimer le champ total_paid des crédits
    op.drop_column('credits', 'total_paid')

    # Supprimer le champ total_paid des abonnements
    op.drop_column('subscriptions', 'total_paid')

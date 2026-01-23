"""refactor_checkbooks_status

Revision ID: e9c3db0655d7
Revises: 7b529cffecdd
Create Date: 2026-01-23 13:39:51.749499

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9c3db0655d7'
down_revision = '7b529cffecdd'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Ajouter le champ status à la table checkbooks
    op.add_column('checkbooks',
        sa.Column('status', sa.String(20), server_default='active', nullable=False))

    # 2. Migrer les statuts des chèques
    # pending -> available (chèques non utilisés)
    # cashed -> used (chèques encaissés/utilisés)
    # cancelled -> cancelled (reste inchangé)
    op.execute("UPDATE checks SET status='available' WHERE status='pending'")
    op.execute("UPDATE checks SET status='used' WHERE status='cashed'")


def downgrade():
    # Restaurer les anciens statuts
    op.execute("UPDATE checks SET status='pending' WHERE status='available'")
    op.execute("UPDATE checks SET status='cashed' WHERE status='used'")

    # Supprimer la colonne status de checkbooks
    op.drop_column('checkbooks', 'status')

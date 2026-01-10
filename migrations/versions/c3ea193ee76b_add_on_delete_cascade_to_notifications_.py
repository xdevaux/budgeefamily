"""Add ON DELETE CASCADE to notifications subscription_id

Revision ID: c3ea193ee76b
Revises: 78396f74e9e7
Create Date: 2025-12-31 17:30:01.319714

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3ea193ee76b'
down_revision = '78396f74e9e7'
branch_labels = None
depends_on = None


def upgrade():
    # Supprimer l'ancienne contrainte de clé étrangère
    op.execute('ALTER TABLE notifications DROP CONSTRAINT notifications_subscription_id_fkey')

    # Recréer la contrainte avec ON DELETE CASCADE
    op.execute('''
        ALTER TABLE notifications
        ADD CONSTRAINT notifications_subscription_id_fkey
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(id)
        ON DELETE CASCADE
    ''')


def downgrade():
    # Supprimer la contrainte avec CASCADE
    op.execute('ALTER TABLE notifications DROP CONSTRAINT notifications_subscription_id_fkey')

    # Recréer la contrainte sans CASCADE (état original)
    op.execute('''
        ALTER TABLE notifications
        ADD CONSTRAINT notifications_subscription_id_fkey
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(id)
    ''')

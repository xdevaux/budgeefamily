"""add last_login to users

Revision ID: add_last_login
Revises: add_entry_method_category
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_last_login'
down_revision = 'add_entry_method_category'

def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_login')

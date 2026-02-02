"""add_english_descriptions_to_category_and_service

Revision ID: bd6057eae65d
Revises: 1d2bdefb8b4b
Create Date: 2026-02-02 07:28:22.424196

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd6057eae65d'
down_revision = '1d2bdefb8b4b'
branch_labels = None
depends_on = None


def upgrade():
    # Add description_en column to categories table
    op.add_column('categories', sa.Column('description_en', sa.Text(), nullable=True))

    # Add description_en column to services table
    op.add_column('services', sa.Column('description_en', sa.Text(), nullable=True))


def downgrade():
    # Remove description_en column from services table
    op.drop_column('services', 'description_en')

    # Remove description_en column from categories table
    op.drop_column('categories', 'description_en')

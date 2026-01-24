"""add entry_method to card_purchases and category_type to categories

Revision ID: add_entry_method_category
Revises: 
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_entry_method_category'
down_revision = '1c7fdfad036e'

def upgrade():
    # Ajouter entry_method dans card_purchases
    op.add_column('card_purchases', sa.Column('entry_method', sa.String(20), nullable=True))
    
    # Mettre à jour les valeurs existantes
    # Si ocr_confidence > 0, alors c'est 'ocr', sinon 'manual'
    op.execute("""
        UPDATE card_purchases 
        SET entry_method = CASE 
            WHEN ocr_confidence > 0 THEN 'ocr'
            ELSE 'manual'
        END
        WHERE entry_method IS NULL
    """)
    
    # Rendre entry_method non nullable après mise à jour
    op.alter_column('card_purchases', 'entry_method', nullable=False)
    
    # Ajouter category_type dans categories
    op.add_column('categories', sa.Column('category_type', sa.String(20), nullable=True, server_default='all'))
    
    # Mettre à jour toutes les catégories existantes à 'all'
    op.execute("UPDATE categories SET category_type = 'all' WHERE category_type IS NULL")
    
    # Rendre category_type non nullable
    op.alter_column('categories', 'category_type', nullable=False)


def downgrade():
    op.drop_column('card_purchases', 'entry_method')
    op.drop_column('categories', 'category_type')

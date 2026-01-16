"""add banks and credit documents tables

Revision ID: daba4518c167
Revises: a83307138b1d
Create Date: 2026-01-16 19:23:53.936495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'daba4518c167'
down_revision = 'a83307138b1d'
branch_labels = None
depends_on = None


def upgrade():
    # Créer la table banks
    op.create_table('banks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('logo_data', sa.Text(), nullable=True),
        sa.Column('logo_mime_type', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('account_number', sa.String(length=100), nullable=True),
        sa.Column('iban', sa.String(length=34), nullable=True),
        sa.Column('bic', sa.String(length=11), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Créer la table bank_documents
    op.create_table('bank_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bank_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bank_id'], ['banks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Créer la table credit_documents
    op.create_table('credit_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credit_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['credit_id'], ['credits.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Ajouter le champ bank_id à la table credits
    op.add_column('credits', sa.Column('bank_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_credits_bank_id', 'credits', 'banks', ['bank_id'], ['id'])


def downgrade():
    # Supprimer la foreign key et le champ bank_id de credits
    op.drop_constraint('fk_credits_bank_id', 'credits', type_='foreignkey')
    op.drop_column('credits', 'bank_id')

    # Supprimer les tables
    op.drop_table('credit_documents')
    op.drop_table('bank_documents')
    op.drop_table('banks')

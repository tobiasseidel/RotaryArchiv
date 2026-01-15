"""Add DocumentPage and composite document support

Revision ID: b8ddf80205d7
Revises: b1c02dcedbfd
Create Date: 2026-01-15 21:45:22.333884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8ddf80205d7'
down_revision: Union[str, None] = 'b1c02dcedbfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Prüfe ob Spalten bereits existieren (für SQLite)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('documents')]
    
    # SQLite benötigt Batch-Modus für ALTER TABLE
    with op.batch_alter_table('documents', schema=None) as batch_op:
        if 'parent_document_id' not in existing_columns:
            batch_op.add_column(sa.Column('parent_document_id', sa.Integer(), nullable=True))
        if 'is_composite' not in existing_columns:
            batch_op.add_column(sa.Column('is_composite', sa.Integer(), nullable=False, server_default='0'))
        if 'page_number' not in existing_columns:
            batch_op.add_column(sa.Column('page_number', sa.Integer(), nullable=True))
        
        # Index nur erstellen wenn Spalte existiert
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('documents')]
        if 'ix_documents_parent_document_id' not in existing_indexes and 'parent_document_id' in existing_columns:
            batch_op.create_index('ix_documents_parent_document_id', ['parent_document_id'], unique=False)
        # Foreign Key wird in SQLite nicht unterstützt, nur Index
    
    # Erstelle document_pages Tabelle
    op.create_table('document_pages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('page_number', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(length=512), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=False),
    sa.Column('ocr_text', sa.Text(), nullable=True),
    sa.Column('ocr_confidence', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_pages_document_id'), 'document_pages', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_pages_id'), 'document_pages', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_pages_id'), table_name='document_pages')
    op.drop_index(op.f('ix_document_pages_document_id'), table_name='document_pages')
    op.drop_table('document_pages')
    
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_parent_document_id')
        batch_op.drop_column('page_number')
        batch_op.drop_column('is_composite')
        batch_op.drop_column('parent_document_id')

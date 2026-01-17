"""make documentpage file_path nullable add is_extracted add ocrjob document_page_id

Revision ID: make_documentpage_nullable
Revises: 9b7e44430d4d
Create Date: 2025-01-17 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "make_documentpage_nullable"
down_revision: Union[str, None] = "9b7e44430d4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite benötigt Batch-Modus für ALTER TABLE
    with op.batch_alter_table("document_pages", schema=None) as batch_op:
        # Mache file_path nullable
        batch_op.alter_column("file_path", existing_type=sa.String(512), nullable=True)

        # Füge is_extracted Spalte hinzu
        batch_op.add_column(
            sa.Column("is_extracted", sa.Boolean(), nullable=False, server_default="0")
        )

    # Füge document_page_id zu ocr_jobs hinzu
    with op.batch_alter_table("ocr_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("document_page_id", sa.Integer(), nullable=True))

        # Erstelle Foreign Key (SQLite unterstützt das, aber mit Einschränkungen)
        try:
            batch_op.create_foreign_key(
                "fk_ocr_jobs_document_page_id",
                "document_pages",
                ["document_page_id"],
                ["id"],
            )
        except Exception:
            # SQLite unterstützt möglicherweise keine Foreign Keys nach ALTER TABLE
            # Index wird trotzdem erstellt
            pass

        # Erstelle Index
        batch_op.create_index("ix_ocr_jobs_document_page_id", ["document_page_id"])


def downgrade() -> None:
    with op.batch_alter_table("ocr_jobs", schema=None) as batch_op:
        # Entferne Index
        batch_op.drop_index("ix_ocr_jobs_document_page_id")

        # Entferne Foreign Key falls vorhanden
        try:
            batch_op.drop_constraint("fk_ocr_jobs_document_page_id", type_="foreignkey")
        except Exception:
            pass

        # Entferne document_page_id Spalte
        batch_op.drop_column("document_page_id")

    with op.batch_alter_table("document_pages", schema=None) as batch_op:
        # Entferne is_extracted Spalte
        batch_op.drop_column("is_extracted")

        # Mache file_path wieder NOT NULL (setze NULL auf leere Strings vorher)
        op.execute("UPDATE document_pages SET file_path = '' WHERE file_path IS NULL")
        batch_op.alter_column("file_path", existing_type=sa.String(512), nullable=False)

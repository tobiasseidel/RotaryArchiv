"""add_document_unit_suggestions

Revision ID: 20250301000000
Revises: 20250215100000
Create Date: 2026-03-01

Tabelle document_unit_suggestions für Vorschläge aus der Grenzen-Analyse.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250301000000"
down_revision: Union[str, None] = "20250215100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_unit_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_ids", sa.JSON(), nullable=False),
        sa.Column(
            "belongs_with_next",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("source_job_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_job_id"], ["ocr_jobs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        op.f("ix_document_unit_suggestions_document_id"),
        "document_unit_suggestions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_unit_suggestions_source_job_id"),
        "document_unit_suggestions",
        ["source_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_unit_suggestions_source_job_id"),
        table_name="document_unit_suggestions",
    )
    op.drop_index(
        op.f("ix_document_unit_suggestions_document_id"),
        table_name="document_unit_suggestions",
    )
    op.drop_table("document_unit_suggestions")

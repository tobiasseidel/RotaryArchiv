"""add_document_units

Revision ID: 20250215100000
Revises: 20250215000000
Create Date: 2026-02-15

Tabelle document_units für Content-Analyse (Zusammenfassung, Personen, Thema,
Ort/Datum, extracted_phrases, extracted_names).
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250215100000"
down_revision: Union[str, None] = "20250215000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_ids", sa.JSON(), nullable=False),
        sa.Column(
            "belongs_with_next",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("persons", sa.JSON(), nullable=True),
        sa.Column("topic", sa.String(length=512), nullable=True),
        sa.Column("place", sa.String(length=512), nullable=True),
        sa.Column("event_date", sa.String(length=100), nullable=True),
        sa.Column("extracted_phrases", sa.JSON(), nullable=True),
        sa.Column("extracted_names", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_document_units_document_id"),
        "document_units",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_units_document_id"), table_name="document_units")
    op.drop_table("document_units")

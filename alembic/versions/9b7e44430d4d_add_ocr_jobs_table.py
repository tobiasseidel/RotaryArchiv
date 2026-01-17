"""add_ocr_jobs_table

Revision ID: 9b7e44430d4d
Revises: c9da3c6a7513
Create Date: 2026-01-17 09:40:20.960949

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b7e44430d4d"
down_revision: Union[str, None] = "c9da3c6a7513"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Erstelle ocr_jobs Tabelle mit batch_alter_table für SQLite-Kompatibilität
    with op.batch_alter_table("ocr_jobs", schema=None) as batch_op:
        # Tabelle existiert noch nicht, daher create_table verwenden
        pass

    # Erstelle Tabelle direkt (batch_alter_table funktioniert nicht für create_table)
    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False
        ),  # String statt Enum für SQLite
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("use_correction", sa.Boolean(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("current_step", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Foreign Key mit batch_alter_table für SQLite
    with op.batch_alter_table("ocr_jobs", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_ocr_jobs_document_id", "documents", ["document_id"], ["id"]
        )
        batch_op.create_index("ix_ocr_jobs_document_id", ["document_id"])
        batch_op.create_index("ix_ocr_jobs_status", ["status"])


def downgrade() -> None:
    # Entferne ocr_jobs Tabelle
    with op.batch_alter_table("ocr_jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_ocr_jobs_status")
        batch_op.drop_index("ix_ocr_jobs_document_id")
        batch_op.drop_constraint("fk_ocr_jobs_document_id", type_="foreignkey")

    op.drop_table("ocr_jobs")

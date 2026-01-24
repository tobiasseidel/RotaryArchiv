"""add_priority_to_ocr_job

Revision ID: add_priority_to_ocr_job
Revises: add_job_type_to_ocr_job
Create Date: 2026-01-22 17:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_priority_to_ocr_job"
down_revision = "add_job_type_to_ocr_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Füge priority Spalte hinzu
    op.add_column(
        "ocr_jobs",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    # Erstelle Index für priority
    op.create_index(
        op.f("ix_ocr_jobs_priority"), "ocr_jobs", ["priority"], unique=False
    )


def downgrade() -> None:
    # Entferne Index
    op.drop_index(op.f("ix_ocr_jobs_priority"), table_name="ocr_jobs")
    # Entferne priority Spalte
    op.drop_column("ocr_jobs", "priority")

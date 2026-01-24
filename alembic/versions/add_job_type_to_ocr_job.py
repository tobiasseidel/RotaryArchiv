"""add_job_type_to_ocr_job

Revision ID: add_job_type_to_ocr_job
Revises: 11622d710e83
Create Date: 2026-01-22 12:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_job_type_to_ocr_job"
down_revision = "3a3080cf7542"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Füge job_type Spalte hinzu
    op.add_column(
        "ocr_jobs",
        sa.Column(
            "job_type", sa.String(length=50), nullable=False, server_default="ocr"
        ),
    )
    # Erstelle Index für job_type
    op.create_index(
        op.f("ix_ocr_jobs_job_type"), "ocr_jobs", ["job_type"], unique=False
    )


def downgrade() -> None:
    # Entferne Index
    op.drop_index(op.f("ix_ocr_jobs_job_type"), table_name="ocr_jobs")
    # Entferne job_type Spalte
    op.drop_column("ocr_jobs", "job_type")

"""add_quality_metrics_to_ocr_results

Revision ID: 20250125000001
Revises: 20250125000000
Create Date: 2026-01-25

Qualitätsmetriken: JSON mit Coverage und Density-Metriken.
NULL = noch nicht berechnet. Bestehende Zeilen bleiben NULL.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250125000001"
down_revision: Union[str, None] = "20250125000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ocr_results",
        sa.Column("quality_metrics", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ocr_results", "quality_metrics")

"""add_deskew_angle_to_document_pages

Revision ID: 20250125000000
Revises: 20250123120000
Create Date: 2026-01-25

Deskew: Winkel (Grad), der beim Erzeugen von OCR/BBox angewandt wurde.
NULL = Rohbild (Legacy). Bestehende Zeilen bleiben NULL.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250125000000"
down_revision: Union[str, None] = "20250123120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_pages",
        sa.Column("deskew_angle", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_pages", "deskew_angle")

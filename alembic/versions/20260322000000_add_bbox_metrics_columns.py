"""add bbox metrics columns for SQL-based filtering

Revision ID: 20260322000000
Revises: 20260321000000
Create Date: 2026-03-22

Fügt Qualitätsmetriken-Spalten zu bboxes hinzu für SQL-basierte Filterung.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260322000000"
down_revision: str | None = "20260321000000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Neue Spalten für Qualitätsmetriken
    op.add_column("bboxes", sa.Column("char_count", sa.Integer(), nullable=True))
    op.add_column(
        "bboxes", sa.Column("chars_per_1k_px", sa.Float(), nullable=True)
    )
    op.add_column("bboxes", sa.Column("area_px", sa.Integer(), nullable=True))
    op.add_column("bboxes", sa.Column("black_pixels", sa.Integer(), nullable=True))
    op.add_column(
        "bboxes", sa.Column("black_pixels_per_char", sa.Float(), nullable=True)
    )
    op.add_column("bboxes", sa.Column("left_pct", sa.Float(), nullable=True))
    op.add_column("bboxes", sa.Column("right_pct", sa.Float(), nullable=True))
    op.add_column("bboxes", sa.Column("width_pct", sa.Float(), nullable=True))

    # Indizes für schnelle Filterung
    op.create_index("ix_bboxes_chars_per_1k_px", "bboxes", ["chars_per_1k_px"])
    op.create_index(
        "ix_bboxes_black_pixels_per_char", "bboxes", ["black_pixels_per_char"]
    )
    op.create_index("ix_bboxes_left_pct", "bboxes", ["left_pct"])
    op.create_index("ix_bboxes_right_pct", "bboxes", ["right_pct"])


def downgrade() -> None:
    op.drop_index("ix_bboxes_right_pct", table_name="bboxes")
    op.drop_index("ix_bboxes_left_pct", table_name="bboxes")
    op.drop_index("ix_bboxes_black_pixels_per_char", table_name="bboxes")
    op.drop_index("ix_bboxes_chars_per_1k_px", table_name="bboxes")

    op.drop_column("bboxes", "width_pct")
    op.drop_column("bboxes", "right_pct")
    op.drop_column("bboxes", "left_pct")
    op.drop_column("bboxes", "black_pixels_per_char")
    op.drop_column("bboxes", "black_pixels")
    op.drop_column("bboxes", "area_px")
    op.drop_column("bboxes", "chars_per_1k_px")
    op.drop_column("bboxes", "char_count")

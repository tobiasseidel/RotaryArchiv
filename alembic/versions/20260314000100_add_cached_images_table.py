"""add cached_images table

Revision ID: 20260314000100
Revises: 20250314000000
Create Date: 2026-03-14 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260314000100"
down_revision: str | None = "20250314000000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cached_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_key", sa.String(length=1024), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("original_path", sa.String(length=1024), nullable=False),
        sa.Column("variants_json", sa.JSON(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cached_images_id"), "cached_images", ["id"], unique=False)
    op.create_index(
        op.f("ix_cached_images_source_key"),
        "cached_images",
        ["source_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_cached_images_source_type"),
        "cached_images",
        ["source_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cached_images_source_type"), table_name="cached_images")
    op.drop_index(op.f("ix_cached_images_source_key"), table_name="cached_images")
    op.drop_index(op.f("ix_cached_images_id"), table_name="cached_images")
    op.drop_table("cached_images")

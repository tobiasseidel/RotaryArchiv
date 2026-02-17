"""add_app_settings_and_job_params

Revision ID: 20250215000000
Revises: 20250125000001
Create Date: 2026-02-15

App-Settings für OCR-Sichtung (Key-Value).
job_params (JSON) auf ocr_jobs für llm_sight (bbox_indices).
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250215000000"
down_revision: Union[str, None] = "20250125000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
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
    )
    op.create_index(op.f("ix_app_settings_key"), "app_settings", ["key"], unique=True)

    op.add_column(
        "ocr_jobs",
        sa.Column("job_params", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ocr_jobs", "job_params")
    op.drop_index(op.f("ix_app_settings_key"), table_name="app_settings")
    op.drop_table("app_settings")

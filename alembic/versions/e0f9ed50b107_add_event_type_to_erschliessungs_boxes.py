"""Add event_type to erschliessungs_boxes

Revision ID: e0f9ed50b107
Revises: f612a3035f71
Create Date: 2026-05-16 18:48:18.209947

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e0f9ed50b107"
down_revision: Union[str, None] = "f612a3035f71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "erschliessungs_boxes",
        sa.Column("event_type", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_erschliessungs_boxes_event_type"),
        "erschliessungs_boxes",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_erschliessungs_boxes_event_type"), table_name="erschliessungs_boxes"
    )
    op.drop_column("erschliessungs_boxes", "event_type")

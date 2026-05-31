"""Add start_date, end_date to erschliessungs_boxes

Revision ID: a1234567890ab
Revises: e0f9ed50b107
Create Date: 2026-05-17 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1234567890ab"
down_revision: Union[str, None] = "e0f9ed50b107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "erschliessungs_boxes",
        sa.Column("start_date", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "erschliessungs_boxes",
        sa.Column("end_date", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("erschliessungs_boxes", "end_date")
    op.drop_column("erschliessungs_boxes", "start_date")

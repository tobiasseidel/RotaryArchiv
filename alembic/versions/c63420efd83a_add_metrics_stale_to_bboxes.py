"""add metrics_stale to bboxes

Revision ID: c63420efd83a
Revises: 50ec95ee0ac6
Create Date: 2026-05-31 09:33:54.500276

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c63420efd83a"
down_revision: Union[str, None] = "50ec95ee0ac6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bboxes",
        sa.Column("metrics_stale", sa.Boolean(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bboxes", "metrics_stale")

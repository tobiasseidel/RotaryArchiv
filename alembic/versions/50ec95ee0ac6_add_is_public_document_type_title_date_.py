"""add_is_public_document_type_title_date_to_document_units

Revision ID: 50ec95ee0ac6
Revises: a1234567890ab
Create Date: 2026-05-22 22:34:45.093364

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50ec95ee0ac6"
down_revision: Union[str, None] = "a1234567890ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_units",
        sa.Column(
            "is_public", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "document_units",
        sa.Column("document_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "document_units", sa.Column("title", sa.String(length=512), nullable=True)
    )
    op.add_column("document_units", sa.Column("date", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_units", "date")
    op.drop_column("document_units", "title")
    op.drop_column("document_units", "document_type")
    op.drop_column("document_units", "is_public")

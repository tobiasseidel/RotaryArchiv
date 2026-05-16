"""Add date to document_pages

Revision ID: f612a3035f71
Revises: 20260322000000
Create Date: 2026-05-16 18:38:23.040078

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f612a3035f71"
down_revision: Union[str, None] = "20260322000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_pages", sa.Column("date", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_document_pages_date"), "document_pages", ["date"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_pages_date"), table_name="document_pages")
    op.drop_column("document_pages", "date")

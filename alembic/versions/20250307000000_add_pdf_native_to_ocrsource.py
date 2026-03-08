"""add_pdf_native_to_ocrsource

Revision ID: 20250307000000
Revises: 20250301000000
Create Date: 2026-03-07

Fügt PDF_NATIVE zum Enum ocrsource hinzu (für native PDF-Text-Boxen ohne OCR).
"""
from contextlib import suppress
from typing import Sequence, Union

from alembic import op

revision: str = "20250307000000"
down_revision: Union[str, None] = "20250301000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        with suppress(Exception):
            op.execute("ALTER TYPE ocrsource ADD VALUE IF NOT EXISTS 'pdf_native'")
    elif dialect_name == "sqlite":
        # SQLite: Spalte ist TEXT, neuer Wert wird akzeptiert
        pass


def downgrade() -> None:
    # PostgreSQL: Enum-Werte können nicht einfach entfernt werden
    pass

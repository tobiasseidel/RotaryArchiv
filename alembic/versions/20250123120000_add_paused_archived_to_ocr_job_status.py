"""add_paused_archived_to_ocr_job_status

Revision ID: 20250123120000
Revises: add_priority_to_ocr_job
Create Date: 2026-01-23 12:00:00.000000

"""
from contextlib import suppress

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250123120000"
down_revision = "add_priority_to_ocr_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Füge 'paused' und 'archived' zum ocrjobstatus Enum hinzu
    # Prüfe Datenbank-Dialekt
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # PostgreSQL: ALTER TYPE ... ADD VALUE
        # Prüfe ob die Werte bereits existieren (PostgreSQL 9.1+ unterstützt IF NOT EXISTS)
        with suppress(Exception):
            op.execute("ALTER TYPE ocrjobstatus ADD VALUE IF NOT EXISTS 'paused'")
        with suppress(Exception):
            op.execute("ALTER TYPE ocrjobstatus ADD VALUE IF NOT EXISTS 'archived'")
    elif dialect_name == "sqlite":
        # SQLite verwendet keine ENUM-Typen, sondern TEXT-Spalten
        # Die neuen Werte können direkt verwendet werden, keine Migration nötig
        pass
    else:
        # Andere Datenbanken: Versuche PostgreSQL-Syntax (kann fehlschlagen)
        with suppress(Exception):
            op.execute("ALTER TYPE ocrjobstatus ADD VALUE IF NOT EXISTS 'paused'")
            op.execute("ALTER TYPE ocrjobstatus ADD VALUE IF NOT EXISTS 'archived'")


def downgrade() -> None:
    # PostgreSQL Enum-Werte können nicht einfach entfernt werden
    # Wir können nur die Spalte ändern, aber das ist komplex und riskant
    # Für jetzt: downgrade ist ein No-Op (Warnung: Enum-Werte bleiben in DB)
    # In Produktion sollte man eine neue Migration erstellen, die die Spalte neu erstellt
    pass

"""add bboxes table for normalized box storage

Revision ID: 20260321000000
Revises: 20260314000100
Create Date: 2026-03-21

Neue Tabelle 'bboxes' zur Normalisierung der Box-Daten.
Ersetzt die JSON-basierte bbox_data Speicherung.
"""

from collections.abc import Sequence
from datetime import datetime
import json

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260321000000"
down_revision: str | None = "20260314000100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Neue Tabelle erstellen
    op.create_table(
        "bboxes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ocr_result_id", sa.Integer(), nullable=False),
        sa.Column(
            "box_type", sa.String(length=50), nullable=False, server_default="ocr"
        ),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("bbox_pixel", sa.JSON(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("ocr_results_data", sa.JSON(), nullable=True),
        sa.Column("differences", sa.JSON(), nullable=True),
        sa.Column("note_author", sa.String(length=255), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=True),
        sa.Column("note_created_at", sa.String(length=50), nullable=True),
        sa.Column("deskew_angle", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["ocr_result_id"], ["ocr_results.id"], ondelete="CASCADE"
        ),
    )

    # 2. Indizes erstellen
    op.create_index("ix_bboxes_ocr_result_id", "bboxes", ["ocr_result_id"])
    op.create_index("ix_bboxes_box_type", "bboxes", ["box_type"])
    op.create_index("ix_bboxes_review_status", "bboxes", ["review_status"])

    # 3. Daten aus bbox_data migrieren (Python-basiert)
    _migrate_bbox_data()


def downgrade() -> None:
    op.drop_index("ix_bboxes_review_status", table_name="bboxes")
    op.drop_index("ix_bboxes_box_type", table_name="bboxes")
    op.drop_index("ix_bboxes_ocr_result_id", table_name="bboxes")
    op.drop_table("bboxes")


def _migrate_bbox_data() -> None:
    """Migriert Daten aus bbox_data JSON zur neuen bboxes Tabelle."""
    from sqlalchemy import text

    bind = op.get_bind()

    # Alle OCRResult Zeilen mit bbox_data holen
    result = bind.execute(
        text("SELECT id, bbox_data FROM ocr_results WHERE bbox_data IS NOT NULL")
    ).fetchall()

    migrated_count = 0
    error_count = 0

    for row in result:
        ocr_result_id = row[0]
        bbox_data = row[1]

        if not bbox_data:
            continue

        # Falls bbox_data als String gespeichert ist
        if isinstance(bbox_data, str):
            try:
                bbox_data = json.loads(bbox_data)
            except json.JSONDecodeError:
                error_count += 1
                continue

        if not isinstance(bbox_data, list):
            continue

        for item in bbox_data:
            if not isinstance(item, dict):
                continue

            # box_type bestimmen (fehlend = "ocr")
            box_type = item.get("box_type") or "ocr"

            # Reviewed_at parsen
            import contextlib

            reviewed_at = None
            ra = item.get("reviewed_at")
            if ra and isinstance(ra, str):
                with contextlib.suppress(ValueError):
                    reviewed_at = datetime.fromisoformat(ra.replace("Z", "+00:00"))

            # JSON-Werte für SQLite vorbereiten
            bbox_val = json.dumps(item.get("bbox")) if item.get("bbox") else None
            bbox_pixel_val = (
                json.dumps(item.get("bbox_pixel")) if item.get("bbox_pixel") else None
            )
            ocr_results_val = (
                json.dumps(item.get("ocr_results")) if item.get("ocr_results") else None
            )
            differences_val = (
                json.dumps(item.get("differences")) if item.get("differences") else None
            )

            # Eintrag erstellen
            try:
                bind.execute(
                    text(
                        """
                        INSERT INTO bboxes (
                            ocr_result_id, box_type, bbox, bbox_pixel, text,
                            review_status, reviewed_at, reviewed_by,
                            ocr_results_data, differences, deskew_angle,
                            note_author, note_text, note_created_at
                        ) VALUES (
                            :ocr_result_id, :box_type, :bbox, :bbox_pixel, :text,
                            :review_status, :reviewed_at, :reviewed_by,
                            :ocr_results_data, :differences, :deskew_angle,
                            :note_author, :note_text, :note_created_at
                        )
                    """
                    ),
                    {
                        "ocr_result_id": ocr_result_id,
                        "box_type": box_type,
                        "bbox": bbox_val,
                        "bbox_pixel": bbox_pixel_val,
                        "text": item.get("text"),
                        "review_status": item.get("review_status"),
                        "reviewed_at": reviewed_at,
                        "reviewed_by": item.get("reviewed_by"),
                        "ocr_results_data": ocr_results_val,
                        "differences": differences_val,
                        "deskew_angle": item.get("deskew_angle"),
                        "note_author": item.get("note_author"),
                        "note_text": item.get("note_text"),
                        "note_created_at": item.get("note_created_at"),
                    },
                )
                migrated_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Nur erste 5 Fehler anzeigen
                    print(f"  Fehler bei ocr_result_id={ocr_result_id}: {e}")

    # Status ausgeben (wird in Alembic Log sichtbar)
    print(f"Migration: {migrated_count} BBox-Einträge migriert, {error_count} Fehler")

"""Add OCR results, review and entity occurrences

Revision ID: c9da3c6a7513
Revises: b8ddf80205d7
Create Date: 2026-01-15 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9da3c6a7513"
down_revision: str | None = "b8ddf80205d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Prüfe ob Tabellen bereits existieren (für SQLite)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Erstelle ocr_results Tabelle
    if "ocr_results" not in existing_tables:
        op.create_table(
            "ocr_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("document_page_id", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column("engine_version", sa.String(length=50), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("confidence_details", sa.JSON(), nullable=True),
            sa.Column("processing_time_ms", sa.Integer(), nullable=True),
            sa.Column("language", sa.String(length=50), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["document_page_id"], ["document_pages.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_ocr_results_document_id"),
            "ocr_results",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_ocr_results_document_page_id"),
            "ocr_results",
            ["document_page_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_ocr_results_source"), "ocr_results", ["source"], unique=False
        )

    # Erstelle ocr_reviews Tabelle
    if "ocr_reviews" not in existing_tables:
        op.create_table(
            "ocr_reviews",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("reviewed_ocr_result_id", sa.Integer(), nullable=True),
            sa.Column("final_text", sa.Text(), nullable=True),
            sa.Column("reviewer_id", sa.Integer(), nullable=True),
            sa.Column("reviewer_name", sa.String(length=255), nullable=True),
            sa.Column("review_notes", sa.Text(), nullable=True),
            sa.Column("review_round", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("previous_review_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
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
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["reviewed_ocr_result_id"], ["ocr_results.id"]),
            sa.ForeignKeyConstraint(["previous_review_id"], ["ocr_reviews.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_ocr_reviews_document_id"),
            "ocr_reviews",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_ocr_reviews_reviewed_ocr_result_id"),
            "ocr_reviews",
            ["reviewed_ocr_result_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_ocr_reviews_status"), "ocr_reviews", ["status"], unique=False
        )

    # Erstelle entity_occurrences Tabelle
    if "entity_occurrences" not in existing_tables:
        op.create_table(
            "entity_occurrences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("ocr_result_id", sa.Integer(), nullable=True),
            sa.Column("start_char", sa.Integer(), nullable=False),
            sa.Column("end_char", sa.Integer(), nullable=False),
            sa.Column("text_snippet", sa.String(length=512), nullable=True),
            sa.Column("context_before", sa.String(length=255), nullable=True),
            sa.Column("context_after", sa.String(length=255), nullable=True),
            sa.Column("detection_method", sa.String(length=50), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_rejected", sa.Boolean(), nullable=False, server_default="0"),
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
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
            sa.ForeignKeyConstraint(["ocr_result_id"], ["ocr_results.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_entity_occurrences_document_id"),
            "entity_occurrences",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_entity_occurrences_entity_id"),
            "entity_occurrences",
            ["entity_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_entity_occurrences_ocr_result_id"),
            "entity_occurrences",
            ["ocr_result_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_entity_occurrences_detection_method"),
            "entity_occurrences",
            ["detection_method"],
            unique=False,
        )
        op.create_index(
            op.f("ix_entity_occurrences_is_confirmed"),
            "entity_occurrences",
            ["is_confirmed"],
            unique=False,
        )

    # Erweitere documents Tabelle
    existing_columns = [col["name"] for col in inspector.get_columns("documents")]

    with op.batch_alter_table("documents", schema=None) as batch_op:
        if "ocr_text_final" not in existing_columns:
            batch_op.add_column(sa.Column("ocr_text_final", sa.Text(), nullable=True))

    # Erweitere annotations Tabelle (wenn sie existiert)
    if "annotations" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("annotations")]

        with op.batch_alter_table("annotations", schema=None) as batch_op:
            if "entity_occurrence_id" not in existing_columns:
                batch_op.add_column(
                    sa.Column("entity_occurrence_id", sa.Integer(), nullable=True)
                )
                batch_op.create_index(
                    op.f("ix_annotations_entity_occurrence_id"),
                    ["entity_occurrence_id"],
                    unique=False,
                )
                # Foreign Key wird später hinzugefügt, wenn entity_occurrences Tabelle existiert
                # SQLite unterstützt keine Foreign Keys in batch_alter_table, daher nur Index


def downgrade() -> None:
    # Prüfe ob Tabellen/Spalten existieren
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Entferne neue Spalten (wenn sie existieren)
    if "annotations" in existing_tables:
        existing_columns = [col["name"] for col in inspector.get_columns("annotations")]
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("annotations")]

        with op.batch_alter_table("annotations", schema=None) as batch_op:
            if "ix_annotations_entity_occurrence_id" in existing_indexes:
                batch_op.drop_index(op.f("ix_annotations_entity_occurrence_id"))
            if "entity_occurrence_id" in existing_columns:
                batch_op.drop_column("entity_occurrence_id")

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("ocr_text_final")

    # Entferne neue Tabellen
    op.drop_index(
        op.f("ix_entity_occurrences_is_confirmed"), table_name="entity_occurrences"
    )
    op.drop_index(
        op.f("ix_entity_occurrences_detection_method"), table_name="entity_occurrences"
    )
    op.drop_index(
        op.f("ix_entity_occurrences_ocr_result_id"), table_name="entity_occurrences"
    )
    op.drop_index(
        op.f("ix_entity_occurrences_entity_id"), table_name="entity_occurrences"
    )
    op.drop_index(
        op.f("ix_entity_occurrences_document_id"), table_name="entity_occurrences"
    )
    op.drop_table("entity_occurrences")

    op.drop_index(op.f("ix_ocr_reviews_status"), table_name="ocr_reviews")
    op.drop_index(
        op.f("ix_ocr_reviews_reviewed_ocr_result_id"), table_name="ocr_reviews"
    )
    op.drop_index(op.f("ix_ocr_reviews_document_id"), table_name="ocr_reviews")
    op.drop_table("ocr_reviews")

    op.drop_index(op.f("ix_ocr_results_source"), table_name="ocr_results")
    op.drop_index(op.f("ix_ocr_results_document_page_id"), table_name="ocr_results")
    op.drop_index(op.f("ix_ocr_results_document_id"), table_name="ocr_results")
    op.drop_table("ocr_results")

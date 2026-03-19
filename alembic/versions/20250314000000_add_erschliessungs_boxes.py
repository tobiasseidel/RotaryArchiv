"""add_erschliessungs_boxes

Revision ID: 20250314000000
Revises: 20250307000000
Create Date: 2026-03-14

Tabelle erschliessungs_boxes: Box auf der Seite verknüpft mit Triple Store
(entity: Person/Ort-Erwähnung; beleg: Aussage mit Referenz).
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20250314000000"
down_revision: Union[str, None] = "20250307000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "erschliessungs_boxes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_page_id", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("box_type", sa.String(length=20), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=True),
        sa.Column("entity_uri", sa.String(length=512), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("subject_uri", sa.String(length=512), nullable=True),
        sa.Column("predicate_uri", sa.String(length=512), nullable=True),
        sa.Column("object_uri", sa.String(length=512), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["document_page_id"],
            ["document_pages.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_erschliessungs_boxes_document_page_id"),
        "erschliessungs_boxes",
        ["document_page_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_erschliessungs_boxes_box_type"),
        "erschliessungs_boxes",
        ["box_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_erschliessungs_boxes_box_type"),
        table_name="erschliessungs_boxes",
    )
    op.drop_index(
        op.f("ix_erschliessungs_boxes_document_page_id"),
        table_name="erschliessungs_boxes",
    )
    op.drop_table("erschliessungs_boxes")

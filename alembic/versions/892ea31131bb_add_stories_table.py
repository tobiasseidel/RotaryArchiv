"""add_stories_table

Revision ID: 892ea31131bb
Revises: c63420efd83a
Create Date: 2026-06-02 22:19:06.682546

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "892ea31131bb"
down_revision: Union[str, None] = "c63420efd83a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("teaser", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("epoch", sa.String(length=50), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
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
    )
    op.create_index(op.f("ix_stories_slug"), "stories", ["slug"], unique=True)
    op.create_index(op.f("ix_stories_epoch"), "stories", ["epoch"], unique=False)
    with op.batch_alter_table("bboxes") as batch_op:
        batch_op.add_column(sa.Column("story_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_bboxes_story_id", ["story_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_bboxes_story_id", "stories", ["story_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("bboxes") as batch_op:
        batch_op.drop_constraint("fk_bboxes_story_id", type_="foreignkey")
        batch_op.drop_index("ix_bboxes_story_id")
        batch_op.drop_column("story_id")
    op.drop_index(op.f("ix_stories_epoch"), table_name="stories")
    op.drop_index(op.f("ix_stories_slug"), table_name="stories")
    op.drop_table("stories")

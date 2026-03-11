"""add dataset chunk table

Revision ID: 20260309_0002
Revises: 20260308_0001
Create Date: 2026-03-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260309_0002"
down_revision = "20260308_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_chunk",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("dataset.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_file_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("dataset_file.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "dataset_file_id",
            "chunk_index",
            name="uq_dataset_chunk_file_index",
        ),
    )
    op.create_index("ix_dataset_chunk_workspace_id", "dataset_chunk", ["workspace_id"])
    op.create_index("ix_dataset_chunk_project_id", "dataset_chunk", ["project_id"])
    op.create_index("ix_dataset_chunk_dataset_id", "dataset_chunk", ["dataset_id"])
    op.create_index("ix_dataset_chunk_dataset_file_id", "dataset_chunk", ["dataset_file_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_chunk_dataset_file_id", table_name="dataset_chunk")
    op.drop_index("ix_dataset_chunk_dataset_id", table_name="dataset_chunk")
    op.drop_index("ix_dataset_chunk_project_id", table_name="dataset_chunk")
    op.drop_index("ix_dataset_chunk_workspace_id", table_name="dataset_chunk")
    op.drop_table("dataset_chunk")

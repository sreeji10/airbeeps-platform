"""add agent platform tables

Revision ID: 20260311_0003
Revises: 20260309_0002
Create Date: 2026-03-11 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260311_0003"
down_revision = "20260309_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_template",
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
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "name",
            "version",
            name="uq_prompt_template_name_version",
        ),
    )
    op.create_index("ix_prompt_template_workspace_id", "prompt_template", ["workspace_id"])
    op.create_index("ix_prompt_template_project_id", "prompt_template", ["project_id"])

    op.create_table(
        "agent_config",
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
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planner_model", sa.String(length=255), nullable=True),
        sa.Column("generation_model", sa.String(length=255), nullable=True),
        sa.Column("fallback_model", sa.String(length=255), nullable=True),
        sa.Column(
            "prompt_template_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("prompt_template.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("enabled_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dataset_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_config_workspace_id", "agent_config", ["workspace_id"])
    op.create_index("ix_agent_config_project_id", "agent_config", ["project_id"])

    op.create_table(
        "background_job",
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
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_background_job_workspace_id", "background_job", ["workspace_id"])
    op.create_index("ix_background_job_project_id", "background_job", ["project_id"])
    op.create_index("ix_background_job_kind", "background_job", ["kind"])

    op.create_table(
        "memory_entry",
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
            "agent_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("agent_config.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_chat_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("chat.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_entry_workspace_id", "memory_entry", ["workspace_id"])
    op.create_index("ix_memory_entry_project_id", "memory_entry", ["project_id"])
    op.create_index("ix_memory_entry_agent_id", "memory_entry", ["agent_id"])

    op.create_table(
        "evaluation_dataset",
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
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_dataset_workspace_id", "evaluation_dataset", ["workspace_id"])
    op.create_index("ix_evaluation_dataset_project_id", "evaluation_dataset", ["project_id"])

    op.create_table(
        "evaluation_case",
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
            "evaluation_dataset_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evaluation_dataset.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("expected_text", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_case_workspace_id", "evaluation_case", ["workspace_id"])
    op.create_index("ix_evaluation_case_project_id", "evaluation_case", ["project_id"])
    op.create_index(
        "ix_evaluation_case_evaluation_dataset_id", "evaluation_case", ["evaluation_dataset_id"]
    )

    op.create_table(
        "evaluation_run",
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
            "evaluation_dataset_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evaluation_dataset.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("agent_config.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluation_run_workspace_id", "evaluation_run", ["workspace_id"])
    op.create_index("ix_evaluation_run_project_id", "evaluation_run", ["project_id"])
    op.create_index(
        "ix_evaluation_run_evaluation_dataset_id", "evaluation_run", ["evaluation_dataset_id"]
    )
    op.create_index("ix_evaluation_run_agent_id", "evaluation_run", ["agent_id"])

    op.create_table(
        "evaluation_result",
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
            "evaluation_run_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evaluation_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_case_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evaluation_case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_result_workspace_id", "evaluation_result", ["workspace_id"])
    op.create_index("ix_evaluation_result_project_id", "evaluation_result", ["project_id"])
    op.create_index(
        "ix_evaluation_result_evaluation_run_id", "evaluation_result", ["evaluation_run_id"]
    )
    op.create_index(
        "ix_evaluation_result_evaluation_case_id", "evaluation_result", ["evaluation_case_id"]
    )

    op.create_table(
        "usage_record",
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
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("run.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_record_workspace_id", "usage_record", ["workspace_id"])
    op.create_index("ix_usage_record_project_id", "usage_record", ["project_id"])
    op.create_index("ix_usage_record_user_id", "usage_record", ["user_id"])
    op.create_index("ix_usage_record_category", "usage_record", ["category"])


def downgrade() -> None:
    op.drop_index("ix_usage_record_category", table_name="usage_record")
    op.drop_index("ix_usage_record_user_id", table_name="usage_record")
    op.drop_index("ix_usage_record_project_id", table_name="usage_record")
    op.drop_index("ix_usage_record_workspace_id", table_name="usage_record")
    op.drop_table("usage_record")

    op.drop_index("ix_evaluation_result_evaluation_case_id", table_name="evaluation_result")
    op.drop_index("ix_evaluation_result_evaluation_run_id", table_name="evaluation_result")
    op.drop_index("ix_evaluation_result_project_id", table_name="evaluation_result")
    op.drop_index("ix_evaluation_result_workspace_id", table_name="evaluation_result")
    op.drop_table("evaluation_result")

    op.drop_index("ix_evaluation_run_agent_id", table_name="evaluation_run")
    op.drop_index("ix_evaluation_run_evaluation_dataset_id", table_name="evaluation_run")
    op.drop_index("ix_evaluation_run_project_id", table_name="evaluation_run")
    op.drop_index("ix_evaluation_run_workspace_id", table_name="evaluation_run")
    op.drop_table("evaluation_run")

    op.drop_index("ix_evaluation_case_evaluation_dataset_id", table_name="evaluation_case")
    op.drop_index("ix_evaluation_case_project_id", table_name="evaluation_case")
    op.drop_index("ix_evaluation_case_workspace_id", table_name="evaluation_case")
    op.drop_table("evaluation_case")

    op.drop_index("ix_evaluation_dataset_project_id", table_name="evaluation_dataset")
    op.drop_index("ix_evaluation_dataset_workspace_id", table_name="evaluation_dataset")
    op.drop_table("evaluation_dataset")

    op.drop_index("ix_memory_entry_agent_id", table_name="memory_entry")
    op.drop_index("ix_memory_entry_project_id", table_name="memory_entry")
    op.drop_index("ix_memory_entry_workspace_id", table_name="memory_entry")
    op.drop_table("memory_entry")

    op.drop_index("ix_background_job_kind", table_name="background_job")
    op.drop_index("ix_background_job_project_id", table_name="background_job")
    op.drop_index("ix_background_job_workspace_id", table_name="background_job")
    op.drop_table("background_job")

    op.drop_index("ix_agent_config_project_id", table_name="agent_config")
    op.drop_index("ix_agent_config_workspace_id", table_name="agent_config")
    op.drop_table("agent_config")

    op.drop_index("ix_prompt_template_project_id", table_name="prompt_template")
    op.drop_index("ix_prompt_template_workspace_id", table_name="prompt_template")
    op.drop_table("prompt_template")

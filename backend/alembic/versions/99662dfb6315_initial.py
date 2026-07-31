"""initial schema — all current models

Revision ID: 99662dfb6315
Revises:
Create Date: 2026-02-25 10:43:04.137537
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "99662dfb6315"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- AgentStatus enum updated: now IDLE/WORKING/PAUSED/ERROR ---
    sa.Enum("IDLE", "WORKING", "PAUSED", "ERROR", name="agentstatus").create(op.get_bind())

    op.create_table(
        "agents",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=True),
        sa.Column(
            "role",
            sa.Enum("DEV", "OPS", "QA", "PM", "RD", "COMMS", "FIN", "ADMIN", name="agentrole"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum("SYSTEM", "CUSTOM", "MARKETPLACE", name="agenttype"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("IDLE", "WORKING", "PAUSED", "ERROR", name="agentstatus"),
            nullable=True,
        ),
        sa.Column("current_task_id", UUID(), nullable=True),
        sa.Column("capabilities", JSON(), nullable=True),
        sa.Column("config", JSON(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column(
            "autonomy_level",
            sa.Enum("FULL", "PREVIEW", "APPROVAL", name="autonomylevel"),
            nullable=True,
        ),
        sa.Column("cost_per_execution", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # --- Projects ---
    op.create_table(
        "projects",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", "ARCHIVED", "COMPLETED", name="projectstatus"),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Enum("P0", "P1", "P2", "P3", name="projectpriority"),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.Enum("CORE", "LEGACY", "PORTFOLIO", "HARDWARE", "EDUCATION", name="projectcategory"),
            nullable=True,
        ),
        sa.Column("github_repo", sa.String(255), nullable=True),
        sa.Column("tech_stack", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Users (new) ---
    op.create_table(
        "users",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # --- Sprints (new) ---
    op.create_table(
        "sprints",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PLANNING", "ACTIVE", "COMPLETED", "CANCELLED", name="sprintstatus"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("goals", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("project_id", UUID(), nullable=False),
        sa.Column("sprint_id", UUID(), nullable=True),
        sa.Column("parent_id", UUID(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("BACKLOG", "TODO", "IN_PROGRESS", "REVIEW", "DONE", "CANCELLED", name="taskstatus"),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="taskpriority"),
            nullable=True,
        ),
        sa.Column(
            "type",
            sa.Enum("FEATURE", "BUG", "RESEARCH", "CONTENT", "OPS", name="tasktype"),
            nullable=True,
        ),
        sa.Column("assignee_type", sa.String(10), nullable=True),
        sa.Column("assignee_id", UUID(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("github_issue", sa.String(255), nullable=True),
        sa.Column("github_pr", sa.String(255), nullable=True),
        sa.Column("custom_fields", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Activities ---
    op.create_table(
        "activities",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("project_id", UUID(), nullable=True),
        sa.Column("agent_id", UUID(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("COMMIT", "PR", "DEPLOY", "RELEASE", "COMMENT", "TASK_CHANGE", "AGENT_ACTION", name="activitytype"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("extra_data", JSON(), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Agent Executions (new) ---
    sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="executionstatus").create(op.get_bind())

    op.create_table(
        "agent_executions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("agent_id", UUID(), nullable=False),
        sa.Column("task_id", UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="executionstatus"),
            nullable=True,
        ),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Metrics ---
    op.create_table(
        "metrics",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("project_id", UUID(), nullable=True),
        sa.Column("agent_id", UUID(), nullable=True),
        sa.Column(
            "category",
            sa.Enum("INDUSTRY", "PERSONAL", "CUSTOM", name="metriccategory"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("target", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column(
            "period",
            sa.Enum("DAILY", "WEEKLY", "MONTHLY", name="metricperiod"),
            nullable=True,
        ),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- JobScout tables ---
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "FULL_TIME", "PART_TIME", "FREELANCE", "MICROTASK",
                "SURVEY", "GIG", "INTERNSHIP", name="opportunitytype",
            ),
            nullable=False,
        ),
        sa.Column(
            "application_type",
            sa.Enum(
                "CV_EMAIL", "PLATFORM_FORM", "REGISTRATION_REQUIRED",
                "ASSESSMENT_FIRST", "QUICK_START", name="applicationtype",
            ),
            nullable=False,
        ),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", JSON(), nullable=True),
        sa.Column("tags", JSON(), nullable=True),
        sa.Column("location_type", sa.String(), nullable=True),
        sa.Column("location_restrictions", JSON(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(), nullable=True),
        sa.Column("salary_period", sa.String(), nullable=True),
        sa.Column("salary_text", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("apply_url", sa.String(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("NEW", "SEEN", "APPLIED", "INTERVIEW", "REJECTED", "ACCEPTED", "EXPIRED", name="opportunitystatus"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("application_notes", sa.Text(), nullable=True),
        sa.Column("raw_data", JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_source", "opportunities", ["source"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    op.create_table(
        "opportunity_views",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scout_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("jobs_found", sa.Integer(), nullable=True),
        sa.Column("jobs_new", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_executions")
    op.drop_table("scout_runs")
    op.drop_table("opportunity_views")
    op.drop_table("opportunities")
    op.drop_table("metrics")
    op.drop_table("activities")
    op.drop_table("tasks")
    op.drop_table("sprints")
    op.drop_table("users")
    op.drop_table("projects")
    op.drop_table("agents")

    op.execute("DROP TYPE IF EXISTS agentstatus")
    op.execute("DROP TYPE IF EXISTS agentrole")
    op.execute("DROP TYPE IF EXISTS agenttype")
    op.execute("DROP TYPE IF EXISTS autonomylevel")
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("DROP TYPE IF EXISTS projectpriority")
    op.execute("DROP TYPE IF EXISTS projectcategory")
    op.execute("DROP TYPE IF EXISTS sprintstatus")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS taskpriority")
    op.execute("DROP TYPE IF EXISTS tasktype")
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS metriccategory")
    op.execute("DROP TYPE IF EXISTS metricperiod")
    op.execute("DROP TYPE IF EXISTS opportunitytype")
    op.execute("DROP TYPE IF EXISTS applicationtype")
    op.execute("DROP TYPE IF EXISTS opportunitystatus")
    op.execute("DROP TYPE IF EXISTS executionstatus")

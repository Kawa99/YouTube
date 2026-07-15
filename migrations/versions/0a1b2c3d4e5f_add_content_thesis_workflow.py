"""add content thesis workflow

Revision ID: 0a1b2c3d4e5f
Revises: f8a9b0c1d2e3
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0a1b2c3d4e5f"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "content_theses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("target_viewer", sa.Text()),
        sa.Column("viewer_promise", sa.Text()),
        sa.Column("format", sa.String()),
        sa.Column("topic_universe", sa.Text()),
        sa.Column("production_edge", sa.Text()),
        sa.Column("packaging_edge", sa.Text()),
        sa.Column("monetization_path", sa.Text()),
        sa.Column("policy_risk_argument", sa.Text()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thesis_id"),
    )
    op.create_index(
        op.f("ix_content_theses_thesis_id"),
        "content_theses",
        ["thesis_id"],
        unique=False,
    )

    op.create_table(
        "thesis_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("channel_id", sa.Integer()),
        sa.Column("video_id", sa.Integer()),
        sa.Column("source_url", sa.String()),
        sa.Column("note", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "thesis_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("title_angle", sa.String()),
        sa.Column("demand_evidence", sa.Text()),
        sa.Column("source_availability", sa.String()),
        sa.Column("production_complexity", sa.String()),
        sa.Column("packaging_potential", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "thesis_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("factor", sa.String(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("weighted_score", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "red_team_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thesis_id", sa.Integer(), nullable=False),
        sa.Column("reviewer", sa.String()),
        sa.Column("decision_under_review", sa.String(), nullable=False),
        sa.Column("core_objections", sa.JSON(), nullable=False),
        sa.Column("competitor_challenges", sa.JSON(), nullable=False),
        sa.Column("failure_premortem", sa.Text()),
        sa.Column("early_warning_signs", sa.Text()),
        sa.Column("preventive_actions", sa.Text()),
        sa.Column("kill_criteria", sa.Text()),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("decision_rationale", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["content_theses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("red_team_reviews")
    op.drop_table("thesis_scores")
    op.drop_table("thesis_topics")
    op.drop_table("thesis_evidence")
    op.drop_index(op.f("ix_content_theses_thesis_id"), table_name="content_theses")
    op.drop_table("content_theses")

"""add owned analytics integration

Revision ID: 3d4e5f607182
Revises: 2c3d4e5f6071
Create Date: 2026-05-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "3d4e5f607182"
down_revision = "2c3d4e5f6071"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "owned_analytics_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer()),
        sa.Column("google_account_email", sa.String()),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("token_secret_ref", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "owned_video_analytics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer()),
        sa.Column("impressions", sa.Integer()),
        sa.Column("impression_ctr", sa.Float()),
        sa.Column("average_view_duration_seconds", sa.Float()),
        sa.Column("average_view_percentage", sa.Float()),
        sa.Column("watch_time_minutes", sa.Float()),
        sa.Column("subscribers_gained", sa.Integer()),
        sa.Column("estimated_revenue", sa.Float()),
        sa.Column("traffic_source_type", sa.String()),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "retention_diagnostics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("ctr", sa.Float()),
        sa.Column("average_view_duration_seconds", sa.Float()),
        sa.Column("average_view_percentage", sa.Float()),
        sa.Column("impressions", sa.Integer()),
        sa.Column("dominant_traffic_source", sa.String()),
        sa.Column("retention_pattern", sa.String()),
        sa.Column("likely_cause", sa.Text()),
        sa.Column("evidence", sa.Text()),
        sa.Column("next_change", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer()),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("variable_tested", sa.String(), nullable=False),
        sa.Column("title", sa.String()),
        sa.Column("thumbnail_variant", sa.String()),
        sa.Column("publish_date", sa.Date()),
        sa.Column("success_metric", sa.String()),
        sa.Column("production_hours", sa.Float()),
        sa.Column("production_cost", sa.Float()),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "experiment_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint", sa.String(), nullable=False),
        sa.Column("views", sa.Integer()),
        sa.Column("impressions", sa.Integer()),
        sa.Column("impression_ctr", sa.Float()),
        sa.Column("average_view_duration_seconds", sa.Float()),
        sa.Column("average_view_percentage", sa.Float()),
        sa.Column("watch_time_minutes", sa.Float()),
        sa.Column("subscribers_gained", sa.Integer()),
        sa.Column("main_traffic_source", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("experiment_checkpoints")
    op.drop_table("experiments")
    op.drop_table("retention_diagnostics")
    op.drop_table("owned_video_analytics")
    op.drop_table("owned_analytics_credentials")

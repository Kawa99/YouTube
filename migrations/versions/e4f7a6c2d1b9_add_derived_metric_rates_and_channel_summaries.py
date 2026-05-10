"""add derived metric rates and channel summaries

Revision ID: e4f7a6c2d1b9
Revises: c2f4c8d1e9a0
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e4f7a6c2d1b9"
down_revision = "c2f4c8d1e9a0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("video_derived_metrics") as batch_op:
        batch_op.add_column(sa.Column("performance_tier", sa.String()))
        batch_op.add_column(sa.Column("like_rate", sa.Float()))
        batch_op.add_column(sa.Column("comment_rate", sa.Float()))
        batch_op.add_column(sa.Column("engagement_rate", sa.Float()))

    op.create_table(
        "channel_derived_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("median_recent_views", sa.Float()),
        sa.Column("median_views_per_subscriber", sa.Float()),
        sa.Column("upload_cadence_days", sa.Float()),
        sa.Column("average_duration_seconds", sa.Float()),
        sa.Column("top_outlier_topics", sa.JSON(), nullable=False),
        sa.Column("format_distribution", sa.JSON(), nullable=False),
        sa.Column("packaging_pattern_distribution", sa.JSON(), nullable=False),
        sa.Column("visible_monetization_signals", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("channel_derived_summaries")
    with op.batch_alter_table("video_derived_metrics") as batch_op:
        batch_op.drop_column("engagement_rate")
        batch_op.drop_column("comment_rate")
        batch_op.drop_column("like_rate")
        batch_op.drop_column("performance_tier")

"""add research engine schema

Revision ID: 9b7d2f4a6c31
Revises: 0d2f4f59d9ab
Create Date: 2026-05-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9b7d2f4a6c31"
down_revision = "0d2f4f59d9ab"
branch_labels = None
depends_on = None


def _columns(table_name):
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_table(table_name):
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def upgrade():
    channel_columns = _columns("channels")
    with op.batch_alter_table("channels") as batch_op:
        if "youtube_channel_id" not in channel_columns:
            batch_op.add_column(sa.Column("youtube_channel_id", sa.String()))
        if "channel_name" not in channel_columns:
            batch_op.add_column(sa.Column("channel_name", sa.String()))
        if "handle" not in channel_columns:
            batch_op.add_column(sa.Column("handle", sa.String()))
        if "custom_url" not in channel_columns:
            batch_op.add_column(sa.Column("custom_url", sa.String()))
        if "canonical_url" not in channel_columns:
            batch_op.add_column(sa.Column("canonical_url", sa.String()))
        if "description" not in channel_columns:
            batch_op.add_column(sa.Column("description", sa.Text()))
        if "published_at" not in channel_columns:
            batch_op.add_column(sa.Column("published_at", sa.DateTime()))
        if "subscriber_count" not in channel_columns:
            batch_op.add_column(sa.Column("subscriber_count", sa.Integer()))
        if "view_count" not in channel_columns:
            batch_op.add_column(sa.Column("view_count", sa.Integer()))
        if "video_count" not in channel_columns:
            batch_op.add_column(sa.Column("video_count", sa.Integer()))
        if "country" not in channel_columns:
            batch_op.add_column(sa.Column("country", sa.String()))
        if "default_language" not in channel_columns:
            batch_op.add_column(sa.Column("default_language", sa.String()))
        if "created_at" not in channel_columns:
            batch_op.add_column(
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )
        if "updated_at" not in channel_columns:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )
        if "last_collected_at" not in channel_columns:
            batch_op.add_column(sa.Column("last_collected_at", sa.DateTime()))
        batch_op.create_index(
            "ix_channels_youtube_channel_id", ["youtube_channel_id"], unique=True
        )
        batch_op.create_index("ix_channels_handle", ["handle"])

    video_columns = _columns("videos")
    with op.batch_alter_table("videos") as batch_op:
        if "youtube_channel_id" not in video_columns:
            batch_op.add_column(sa.Column("youtube_channel_id", sa.String()))
        if "description_excerpt" not in video_columns:
            batch_op.add_column(sa.Column("description_excerpt", sa.Text()))
        if "description_full" not in video_columns:
            batch_op.add_column(sa.Column("description_full", sa.Text()))
        if "published_at" not in video_columns:
            batch_op.add_column(sa.Column("published_at", sa.DateTime()))
        if "duration_seconds" not in video_columns:
            batch_op.add_column(sa.Column("duration_seconds", sa.Integer()))
        if "category_id" not in video_columns:
            batch_op.add_column(sa.Column("category_id", sa.String()))
        if "default_language" not in video_columns:
            batch_op.add_column(sa.Column("default_language", sa.String()))
        if "caption_available" not in video_columns:
            batch_op.add_column(sa.Column("caption_available", sa.Boolean()))
        if "thumbnail_url" not in video_columns:
            batch_op.add_column(sa.Column("thumbnail_url", sa.String()))
        if "transcript_status" not in video_columns:
            batch_op.add_column(sa.Column("transcript_status", sa.String()))
        if "transcript_text" not in video_columns:
            batch_op.add_column(sa.Column("transcript_text", sa.Text()))
        if "created_at" not in video_columns:
            batch_op.add_column(
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )
        if "updated_at" not in video_columns:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )
        if "last_collected_at" not in video_columns:
            batch_op.add_column(sa.Column("last_collected_at", sa.DateTime()))
        batch_op.create_index("ix_videos_youtube_channel_id", ["youtube_channel_id"])
        batch_op.create_foreign_key(
            "fk_videos_youtube_channel_id_channels",
            "channels",
            ["youtube_channel_id"],
            ["youtube_channel_id"],
        )

    if not _has_table("video_metadata_history"):
        op.create_table(
            "video_metadata_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("video_id", sa.Integer(), nullable=False),
            sa.Column("old_title", sa.String(), nullable=False),
            sa.Column("new_title", sa.String(), nullable=False),
            sa.Column("old_thumbnail", sa.String(), nullable=False),
            sa.Column("new_thumbnail", sa.String(), nullable=False),
            sa.Column("changed_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_type", sa.String()),
        sa.Column("input_value", sa.String()),
        sa.Column("requested_limit", sa.Integer()),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("quota_estimate", sa.Integer()),
        sa.Column("items_found", sa.Integer(), nullable=False),
        sa.Column("items_saved", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_by", sa.String()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "api_raw_payloads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("external_id", sa.String()),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("collection_run_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_run_id"], ["collection_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_api_raw_payloads_external_id", "api_raw_payloads", ["external_id"]
    )
    op.create_table(
        "video_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("comment_count", sa.Integer(), nullable=False),
        sa.Column("subscriber_count_at_snapshot", sa.Integer()),
        sa.Column("collection_run_id", sa.Integer()),
        sa.ForeignKeyConstraint(["collection_run_id"], ["collection_runs.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "channel_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("subscriber_count", sa.Integer(), nullable=False),
        sa.Column("view_count", sa.Integer()),
        sa.Column("video_count", sa.Integer()),
        sa.Column("collection_run_id", sa.Integer()),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["collection_run_id"], ["collection_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "video_metadata_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("collection_run_id", sa.Integer()),
        sa.ForeignKeyConstraint(["collection_run_id"], ["collection_runs.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "video_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("niche", sa.String()),
        sa.Column("format", sa.String()),
        sa.Column("faceless_status", sa.String()),
        sa.Column("ai_use_visible", sa.String()),
        sa.Column("visual_style", sa.String()),
        sa.Column("packaging_pattern", sa.String()),
        sa.Column("topic_type", sa.String()),
        sa.Column("production_complexity", sa.String()),
        sa.Column("policy_risk", sa.String()),
        sa.Column("monetization_signals", sa.Text()),
        sa.Column("reviewer", sa.String()),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "channel_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("primary_niche", sa.String()),
        sa.Column("primary_format", sa.String()),
        sa.Column("faceless_status", sa.String()),
        sa.Column("sponsor_fit", sa.String()),
        sa.Column("policy_risk", sa.String()),
        sa.Column("production_complexity", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column("reviewer", sa.String()),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "video_derived_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("age_days", sa.Float()),
        sa.Column("views_per_day", sa.Float()),
        sa.Column("views_per_subscriber", sa.Float()),
        sa.Column("channel_recent_median_views", sa.Float()),
        sa.Column("relative_performance", sa.Float()),
        sa.Column("duration_bucket", sa.String()),
        sa.Column("outlier_flag", sa.Boolean(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(sa.text("""
            UPDATE channels
            SET subscriber_count = subscribers,
                handle = CASE
                    WHEN channel_username LIKE '@%' THEN channel_username
                    ELSE handle
                END,
                channel_name = COALESCE(channel_name, channel_username),
                canonical_url = COALESCE(
                    canonical_url,
                    'https://www.youtube.com/' || channel_username
                )
            """))
    op.execute(sa.text("""
            UPDATE videos
            SET description_full = description,
                description_excerpt = substr(COALESCE(description, ''), 1, 500),
                transcript_text = transcript,
                transcript_status = CASE
                    WHEN transcript IS NOT NULL AND transcript != '' THEN 'available'
                    ELSE 'missing'
                END
            """))
    op.execute(sa.text("""
            INSERT INTO video_snapshots (
                video_id,
                snapshot_at,
                view_count,
                like_count,
                comment_count,
                subscriber_count_at_snapshot
            )
            SELECT
                video_history.video_id,
                video_history.timestamp,
                video_history.views,
                video_history.likes,
                video_history.comments,
                channels.subscribers
            FROM video_history
            JOIN videos ON videos.id = video_history.video_id
            LEFT JOIN channels ON channels.id = videos.channel_id
            """))
    op.execute(sa.text("""
            INSERT INTO channel_snapshots (
                channel_id,
                snapshot_at,
                subscriber_count,
                view_count,
                video_count
            )
            SELECT
                id,
                CURRENT_TIMESTAMP,
                subscribers,
                view_count,
                video_count
            FROM channels
            """))
    op.execute(sa.text("""
            INSERT INTO video_metadata_changes (
                video_id,
                field_name,
                old_value,
                new_value,
                changed_at
            )
            SELECT video_id, 'title', old_title, new_title, changed_at
            FROM video_metadata_history
            WHERE old_title != new_title
            """))
    op.execute(sa.text("""
            INSERT INTO video_metadata_changes (
                video_id,
                field_name,
                old_value,
                new_value,
                changed_at
            )
            SELECT
                video_id,
                'thumbnail_url',
                old_thumbnail,
                new_thumbnail,
                changed_at
            FROM video_metadata_history
            WHERE old_thumbnail != new_thumbnail
            """))


def downgrade():
    op.drop_table("video_derived_metrics")
    op.drop_table("channel_labels")
    op.drop_table("video_labels")
    op.drop_table("video_metadata_changes")
    op.drop_table("channel_snapshots")
    op.drop_table("video_snapshots")
    op.drop_index("ix_api_raw_payloads_external_id", table_name="api_raw_payloads")
    op.drop_table("api_raw_payloads")
    op.drop_table("collection_runs")

    with op.batch_alter_table("videos") as batch_op:
        batch_op.drop_constraint(
            "fk_videos_youtube_channel_id_channels", type_="foreignkey"
        )
        batch_op.drop_index("ix_videos_youtube_channel_id")
        batch_op.drop_column("last_collected_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("transcript_text")
        batch_op.drop_column("transcript_status")
        batch_op.drop_column("caption_available")
        batch_op.drop_column("default_language")
        batch_op.drop_column("category_id")
        batch_op.drop_column("duration_seconds")
        batch_op.drop_column("published_at")
        batch_op.drop_column("description_full")
        batch_op.drop_column("description_excerpt")
        batch_op.drop_column("youtube_channel_id")

    with op.batch_alter_table("channels") as batch_op:
        batch_op.drop_index("ix_channels_handle")
        batch_op.drop_index("ix_channels_youtube_channel_id")
        batch_op.drop_column("last_collected_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("default_language")
        batch_op.drop_column("country")
        batch_op.drop_column("video_count")
        batch_op.drop_column("view_count")
        batch_op.drop_column("subscriber_count")
        batch_op.drop_column("published_at")
        batch_op.drop_column("description")
        batch_op.drop_column("canonical_url")
        batch_op.drop_column("custom_url")
        batch_op.drop_column("handle")
        batch_op.drop_column("channel_name")
        batch_op.drop_column("youtube_channel_id")

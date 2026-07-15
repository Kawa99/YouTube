"""add performance indexes

Revision ID: 4e5f60718293
Revises: 3d4e5f607182
Create Date: 2026-05-11 00:00:00.000000

"""

from alembic import op

revision = "4e5f60718293"
down_revision = "3d4e5f607182"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_channels_published_at", "channels", ("published_at",)),
    ("ix_videos_youtube_video_id", "videos", ("youtube_video_id",)),
    ("ix_videos_published_at", "videos", ("published_at",)),
    (
        "ix_api_raw_payloads_collection_run_id",
        "api_raw_payloads",
        ("collection_run_id",),
    ),
    (
        "ix_video_snapshots_collection_run_id",
        "video_snapshots",
        ("collection_run_id",),
    ),
    ("ix_video_snapshots_snapshot_at", "video_snapshots", ("snapshot_at",)),
    (
        "ix_video_snapshots_video_snapshot_at",
        "video_snapshots",
        ("video_id", "snapshot_at"),
    ),
    (
        "ix_channel_snapshots_collection_run_id",
        "channel_snapshots",
        ("collection_run_id",),
    ),
    ("ix_channel_snapshots_snapshot_at", "channel_snapshots", ("snapshot_at",)),
    (
        "ix_channel_snapshots_channel_snapshot_at",
        "channel_snapshots",
        ("channel_id", "snapshot_at"),
    ),
    (
        "ix_video_metadata_changes_collection_run_id",
        "video_metadata_changes",
        ("collection_run_id",),
    ),
    ("ix_video_labels_video_id", "video_labels", ("video_id",)),
    ("ix_video_labels_niche", "video_labels", ("niche",)),
    ("ix_video_labels_format", "video_labels", ("format",)),
    ("ix_video_labels_niche_format", "video_labels", ("niche", "format")),
    ("ix_channel_labels_channel_id", "channel_labels", ("channel_id",)),
    ("ix_channel_labels_primary_niche", "channel_labels", ("primary_niche",)),
    ("ix_channel_labels_primary_format", "channel_labels", ("primary_format",)),
    (
        "ix_channel_labels_primary_niche_format",
        "channel_labels",
        ("primary_niche", "primary_format"),
    ),
    ("ix_video_derived_metrics_video_id", "video_derived_metrics", ("video_id",)),
    (
        "ix_video_derived_metrics_snapshot_at",
        "video_derived_metrics",
        ("snapshot_at",),
    ),
    (
        "ix_video_derived_metrics_outlier_flag",
        "video_derived_metrics",
        ("outlier_flag",),
    ),
    (
        "ix_video_derived_metrics_outlier_relative",
        "video_derived_metrics",
        ("outlier_flag", "relative_performance"),
    ),
)


def upgrade():
    for index_name, table_name, columns in INDEXES:
        op.create_index(index_name, table_name, list(columns))


def downgrade():
    for index_name, table_name, _columns in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name)

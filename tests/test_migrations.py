import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect

EXPECTED_INDEXES = {
    "channels": {"ix_channels_published_at"},
    "videos": {"ix_videos_youtube_video_id", "ix_videos_published_at"},
    "video_snapshots": {
        "ix_video_snapshots_collection_run_id",
        "ix_video_snapshots_snapshot_at",
        "ix_video_snapshots_video_snapshot_at",
    },
    "channel_snapshots": {
        "ix_channel_snapshots_collection_run_id",
        "ix_channel_snapshots_snapshot_at",
        "ix_channel_snapshots_channel_snapshot_at",
    },
    "video_labels": {
        "ix_video_labels_niche",
        "ix_video_labels_format",
        "ix_video_labels_niche_format",
    },
    "video_derived_metrics": {
        "ix_video_derived_metrics_snapshot_at",
        "ix_video_derived_metrics_outlier_flag",
        "ix_video_derived_metrics_outlier_relative",
    },
}


def test_alembic_upgrade_reaches_head(tmp_path):
    db_path = tmp_path / "migration-smoke.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "FLASK_APP": "app.py",
        "SOCKETIO_ASYNC_MODE": "threading",
    }

    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    try:
        for table_name, expected_index_names in EXPECTED_INDEXES.items():
            actual_index_names = {
                index["name"] for index in inspector.get_indexes(table_name)
            }
            assert expected_index_names <= actual_index_names
    finally:
        engine.dispose()


def test_alembic_can_downgrade_last_revision(tmp_path):
    db_path = tmp_path / "migration-downgrade.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "FLASK_APP": "app.py",
        "SOCKETIO_ASYNC_MODE": "threading",
    }

    upgrade = subprocess.run(  # nosec B603
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = subprocess.run(  # nosec B603
        [sys.executable, "-m", "flask", "db", "downgrade", "3d4e5f607182"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert downgrade.returncode == 0, downgrade.stderr

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    try:
        video_index_names = {
            index["name"] for index in inspector.get_indexes("video_derived_metrics")
        }
        assert "ix_video_derived_metrics_outlier_relative" not in video_index_names
        assert inspector.has_table("owned_video_analytics")
    finally:
        engine.dispose()

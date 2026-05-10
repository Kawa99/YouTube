from datetime import datetime, timedelta

from flask import Flask

from metrics import classify_performance, compute_derived_metrics, duration_bucket
from models import (
    Channel,
    ChannelDerivedSummary,
    Video,
    VideoDerivedMetric,
    VideoLabel,
    VideoSnapshot,
    db,
)


def create_app_and_db():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


def test_duration_bucket_and_performance_classification():
    assert duration_bucket(None) == "unknown"
    assert duration_bucket(200) == "<4m"
    assert duration_bucket(300) == "4-8m"
    assert duration_bucket(800) == "8-15m"
    assert duration_bucket(1200) == "15-30m"
    assert duration_bucket(2500) == "30m+"

    assert classify_performance(None) == "unknown"
    assert classify_performance(5) == "breakout"
    assert classify_performance(2) == "outlier"
    assert classify_performance(1) == "normal"
    assert classify_performance(0.4) == "underperformer"


def test_compute_derived_metrics_creates_video_metrics_and_channel_summary():
    app = create_app_and_db()
    with app.app_context():
        db.create_all()
        channel = Channel(
            channel_username="@metrics_channel",
            subscribers=1000,
            subscriber_count=1000,
        )
        db.session.add(channel)
        db.session.flush()

        published_at = datetime(2026, 1, 1, 0, 0, 0)
        videos = [
            Video(
                youtube_video_id="baseline_1",
                title="Baseline 1",
                views=1000,
                likes=50,
                comments=10,
                duration_seconds=600,
                published_at=published_at,
                channel_id=channel.id,
            ),
            Video(
                youtube_video_id="baseline_2",
                title="Baseline 2",
                views=1000,
                likes=40,
                comments=10,
                duration_seconds=900,
                published_at=published_at + timedelta(days=2),
                channel_id=channel.id,
            ),
            Video(
                youtube_video_id="outlier",
                title="Outlier Topic",
                views=6000,
                likes=600,
                comments=60,
                duration_seconds=1200,
                published_at=published_at + timedelta(days=4),
                channel_id=channel.id,
            ),
        ]
        db.session.add_all(videos)
        db.session.flush()

        snapshot_at = datetime(2026, 1, 11, 0, 0, 0)
        db.session.add_all(
            [
                VideoSnapshot(
                    video_id=videos[0].id,
                    snapshot_at=snapshot_at,
                    view_count=1000,
                    like_count=50,
                    comment_count=10,
                    subscriber_count_at_snapshot=1000,
                ),
                VideoSnapshot(
                    video_id=videos[1].id,
                    snapshot_at=snapshot_at,
                    view_count=1000,
                    like_count=40,
                    comment_count=10,
                    subscriber_count_at_snapshot=1000,
                ),
                VideoSnapshot(
                    video_id=videos[2].id,
                    snapshot_at=snapshot_at,
                    view_count=6000,
                    like_count=600,
                    comment_count=60,
                    subscriber_count_at_snapshot=1000,
                ),
                VideoLabel(
                    video_id=videos[2].id,
                    niche="education",
                    format="explainer",
                    topic_type="evergreen",
                    packaging_pattern="how_to",
                    monetization_signals="Sponsor fit",
                    review_status="reviewed",
                ),
            ]
        )
        db.session.commit()

        summary = compute_derived_metrics()

        assert summary == {"videos_computed": 3, "channels_computed": 1}
        outlier_metric = (
            VideoDerivedMetric.query.join(Video)
            .filter(Video.youtube_video_id == "outlier")
            .one()
        )
        assert outlier_metric.relative_performance == 6
        assert outlier_metric.performance_tier == "breakout"
        assert outlier_metric.outlier_flag is True
        assert outlier_metric.like_rate == 10.0
        assert outlier_metric.comment_rate == 1.0
        assert outlier_metric.engagement_rate == 11.0
        assert outlier_metric.duration_bucket == "15-30m"
        assert outlier_metric.algorithm_version == "derived-metrics-v1"

        channel_summary = ChannelDerivedSummary.query.one()
        assert channel_summary.median_recent_views == 1000
        assert channel_summary.upload_cadence_days == 2
        assert channel_summary.format_distribution == {"explainer": 1}
        assert channel_summary.packaging_pattern_distribution == {"how_to": 1}
        assert channel_summary.visible_monetization_signals == ["Sponsor fit"]

        db.session.expunge_all()
        compute_derived_metrics()
        assert VideoDerivedMetric.query.count() == 3
        assert ChannelDerivedSummary.query.count() == 1

        db.session.remove()
        db.drop_all()

from datetime import UTC, datetime

from flask import Flask
import pytest
from sqlalchemy.exc import IntegrityError

from models import (
    ApiRawPayload,
    Channel,
    ChannelLabel,
    CollectionRun,
    Video,
    VideoDerivedMetric,
    VideoLabel,
    db,
)


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def app_and_db():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app, db
        db.session.remove()
        db.drop_all()


def test_youtube_channel_id_is_unique_when_present(app_and_db):
    db.session.add_all(
        [
            Channel(channel_username="@one", subscribers=1, youtube_channel_id="UC1"),
            Channel(channel_username="@two", subscribers=2, youtube_channel_id="UC1"),
        ]
    )

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_collection_payload_labels_and_derived_metrics_crud(app_and_db):
    channel = Channel(
        channel_username="@research",
        subscribers=1000,
        youtube_channel_id="UC_RESEARCH",
        subscriber_count=1000,
    )
    db.session.add(channel)
    db.session.flush()

    video = Video(
        youtube_video_id="research_video",
        youtube_channel_id="UC_RESEARCH",
        title="Research video",
        views=10000,
        likes=500,
        comments=100,
        channel_id=channel.id,
    )
    db.session.add(video)
    db.session.flush()

    run = CollectionRun(
        run_type="single_video",
        status="completed",
        input_type="video_id",
        input_value="research_video",
        requested_limit=1,
        started_at=utc_now(),
        completed_at=utc_now(),
        quota_estimate=3,
        items_found=1,
        items_saved=1,
        items_failed=0,
        created_by="pytest",
    )
    db.session.add(run)
    db.session.flush()

    db.session.add(
        ApiRawPayload(
            source="youtube_data_api",
            endpoint="videos.list",
            external_id="research_video",
            payload_json={"items": [{"id": "research_video"}]},
            collection_run_id=run.id,
        )
    )
    db.session.add(
        VideoLabel(
            video_id=video.id,
            niche="education",
            format="listicle",
            faceless_status="faceless",
            review_status="reviewed",
            reviewer="pytest",
        )
    )
    db.session.add(
        ChannelLabel(
            channel_id=channel.id,
            primary_niche="education",
            primary_format="listicle",
            faceless_status="faceless",
            sponsor_fit="medium",
            reviewer="pytest",
        )
    )
    db.session.add(
        VideoDerivedMetric(
            video_id=video.id,
            snapshot_at=utc_now(),
            age_days=10,
            views_per_day=1000,
            views_per_subscriber=10,
            channel_recent_median_views=5000,
            relative_performance=2,
            duration_bucket="8-15m",
            outlier_flag=True,
            algorithm_version="test-v1",
        )
    )

    db.session.commit()

    assert CollectionRun.query.count() == 1
    assert ApiRawPayload.query.one().payload_json["items"][0]["id"] == "research_video"
    assert VideoLabel.query.one().faceless_status == "faceless"
    assert ChannelLabel.query.one().sponsor_fit == "medium"
    assert VideoDerivedMetric.query.one().relative_performance == 2

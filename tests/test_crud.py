from flask import Flask
import pytest

from crud import save_video
from models import (
    Channel,
    ChannelHistory,
    ChannelSnapshot,
    ChannelVideo,
    Video,
    VideoHistory,
    VideoMetadataChange,
    VideoMetadataHistory,
    VideoSnapshot,
    db,
)


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


def test_save_video_creates_new_records(app_and_db):
    result = save_video(
        {
            "youtube_video_id": "video_1",
            "channel_username": "@channel_one",
            "subscribers": 100,
            "title": "My Setup 2025",
            "thumbnail_url": "https://img.youtube.com/vi/video_1/default.jpg",
            "views": 250,
        }
    )

    assert result == {"video_id": 1, "created": True}
    assert Video.query.count() == 1
    assert Channel.query.count() == 1
    assert ChannelVideo.query.count() == 1
    assert ChannelHistory.query.count() == 0
    assert VideoHistory.query.count() == 1
    assert VideoSnapshot.query.count() == 1
    assert ChannelSnapshot.query.count() == 1
    assert VideoMetadataHistory.query.count() == 0

    history_row = VideoHistory.query.one()
    assert history_row.views == 250
    assert history_row.likes == 0
    assert history_row.comments == 0
    assert history_row.timestamp is not None

    video_snapshot = VideoSnapshot.query.one()
    assert video_snapshot.view_count == 250
    assert video_snapshot.subscriber_count_at_snapshot == 100

    channel = Channel.query.one()
    assert channel.subscriber_count == 100
    assert channel.handle == "@channel_one"


def test_save_video_updates_existing_and_tracks_history(app_and_db):
    save_video(
        {
            "youtube_video_id": "video_1",
            "channel_username": "@channel_one",
            "subscribers": 100,
            "title": "My Setup 2025",
            "thumbnail_url": "https://img.youtube.com/vi/video_1/default.jpg",
            "views": 1000,
        }
    )

    result = save_video(
        {
            "youtube_video_id": "video_1",
            "channel_username": "@channel_one",
            "subscribers": 200,
            "title": "Ultimate Desk Setup 2025!",
            "thumbnail_url": "https://img.youtube.com/vi/video_1/default.jpg",
            "views": 2000,
        }
    )

    assert result == {"video_id": 1, "created": False}
    assert Video.query.count() == 1
    assert Channel.query.count() == 1

    video = Video.query.one()
    assert video.views == 2000
    assert video.title == "Ultimate Desk Setup 2025!"

    history_records = ChannelHistory.query.all()
    assert len(history_records) == 1
    assert history_records[0].previous_subscribers == 100

    video_history_rows = VideoHistory.query.order_by(VideoHistory.id.asc()).all()
    assert len(video_history_rows) == 2
    assert video_history_rows[0].views == 1000
    assert video_history_rows[1].views == 2000

    metadata_rows = VideoMetadataHistory.query.order_by(
        VideoMetadataHistory.id.asc()
    ).all()
    assert len(metadata_rows) == 1
    assert metadata_rows[0].old_title == "My Setup 2025"
    assert metadata_rows[0].new_title == "Ultimate Desk Setup 2025!"

    metadata_changes = VideoMetadataChange.query.order_by(
        VideoMetadataChange.id.asc()
    ).all()
    assert len(metadata_changes) == 1
    assert metadata_changes[0].field_name == "title"
    assert metadata_changes[0].old_value == "My Setup 2025"
    assert metadata_changes[0].new_value == "Ultimate Desk Setup 2025!"


def test_save_video_does_not_log_metadata_history_without_metadata_changes(app_and_db):
    payload = {
        "youtube_video_id": "video_1",
        "channel_username": "@channel_one",
        "subscribers": 100,
        "title": "Stable Title",
        "thumbnail_url": "https://img.youtube.com/vi/video_1/default.jpg",
        "views": 1000,
    }

    save_video(payload)
    save_video({**payload, "views": 2000, "subscribers": 150})

    assert VideoMetadataHistory.query.count() == 0
    assert VideoMetadataChange.query.count() == 0


def test_save_video_populates_normalized_research_fields(app_and_db):
    save_video(
        {
            "youtube_video_id": "video_2",
            "youtube_channel_id": "UC123",
            "channel_username": "@normalized_channel",
            "channel_name": "Normalized Channel",
            "channel_view_count": "50000",
            "channel_video_count": "42",
            "subscribers": "1200",
            "title": "Research schema video",
            "description": "A" * 600,
            "views": "2400",
            "likes": "120",
            "comments": "12",
            "posted": "2026-01-01",
            "published_at": "2026-01-01T12:30:00Z",
            "video_length": "1:02:03",
            "thumbnail_url": "https://img.youtube.com/vi/video_2/default.jpg",
            "transcript": "Transcript text",
            "category_id": "27",
            "default_language": "en",
        }
    )

    channel = Channel.query.one()
    assert channel.youtube_channel_id == "UC123"
    assert channel.channel_name == "Normalized Channel"
    assert channel.subscriber_count == 1200
    assert channel.view_count == 50000
    assert channel.video_count == 42

    video = Video.query.one()
    assert video.youtube_channel_id == "UC123"
    assert video.description_full == "A" * 600
    assert video.description_excerpt == "A" * 500
    assert video.duration_seconds == 3723
    assert video.transcript_text == "Transcript text"
    assert video.transcript_status == "available"
    assert video.category_id == "27"
    assert video.default_language == "en"
    assert video.last_collected_at is not None

    channel_snapshot = ChannelSnapshot.query.one()
    assert channel_snapshot.subscriber_count == 1200
    assert channel_snapshot.view_count == 50000

    video_snapshot = VideoSnapshot.query.one()
    assert video_snapshot.view_count == 2400
    assert video_snapshot.like_count == 120
    assert video_snapshot.comment_count == 12


def test_save_video_records_thumbnail_metadata_change(app_and_db):
    payload = {
        "youtube_video_id": "video_3",
        "channel_username": "@thumbnail_channel",
        "subscribers": 100,
        "title": "Stable Title",
        "thumbnail_url": "https://img.youtube.com/vi/video_3/default.jpg",
        "views": 1000,
    }

    save_video(payload)
    save_video(
        {
            **payload,
            "thumbnail_url": "https://img.youtube.com/vi/video_3/hqdefault.jpg",
            "views": 1500,
        }
    )

    metadata_change = VideoMetadataChange.query.one()
    assert metadata_change.field_name == "thumbnail_url"
    assert metadata_change.old_value.endswith("default.jpg")
    assert metadata_change.new_value.endswith("hqdefault.jpg")


def test_save_video_rejects_mismatched_stable_channel_identity(app_and_db):
    payload = {
        "youtube_video_id": "video_4",
        "youtube_channel_id": "UC_ORIGINAL",
        "channel_username": "@identity_channel",
        "subscribers": 100,
        "title": "Identity test",
    }

    save_video(payload)

    with pytest.raises(ValueError, match="existing channel identity"):
        save_video(
            {
                **payload,
                "youtube_video_id": "video_5",
                "youtube_channel_id": "UC_DIFFERENT",
            }
        )

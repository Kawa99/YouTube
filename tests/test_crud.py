from flask import Flask
import pytest

from crud import save_video
from models import (
    Channel,
    ChannelHistory,
    ChannelVideo,
    Video,
    VideoHistory,
    VideoMetadataHistory,
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
    assert VideoMetadataHistory.query.count() == 0

    history_row = VideoHistory.query.one()
    assert history_row.views == 250
    assert history_row.likes == 0
    assert history_row.comments == 0
    assert history_row.timestamp is not None


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

    metadata_rows = VideoMetadataHistory.query.order_by(VideoMetadataHistory.id.asc()).all()
    assert len(metadata_rows) == 1
    assert metadata_rows[0].old_title == "My Setup 2025"
    assert metadata_rows[0].new_title == "Ultimate Desk Setup 2025!"


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

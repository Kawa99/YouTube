from flask import Flask
import pytest

from crud import save_video
from models import Channel, ChannelHistory, ChannelVideo, Video, db


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
            "views": 250,
        }
    )

    assert result == {"video_id": 1, "created": True}
    assert Video.query.count() == 1
    assert Channel.query.count() == 1
    assert ChannelVideo.query.count() == 1
    assert ChannelHistory.query.count() == 0


def test_save_video_updates_existing_and_tracks_history(app_and_db):
    save_video(
        {
            "youtube_video_id": "video_1",
            "channel_username": "@channel_one",
            "subscribers": 100,
            "views": 1000,
        }
    )

    result = save_video(
        {
            "youtube_video_id": "video_1",
            "channel_username": "@channel_one",
            "subscribers": 200,
            "views": 2000,
        }
    )

    assert result == {"video_id": 1, "created": False}
    assert Video.query.count() == 1
    assert Channel.query.count() == 1

    video = Video.query.one()
    assert video.views == 2000

    history_records = ChannelHistory.query.all()
    assert len(history_records) == 1
    assert history_records[0].previous_subscribers == 100

from flask import Flask
import pytest

import tasks
from models import Channel, db


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


def test_scrape_tracked_channels_enqueues_only_tracked_channels(
    app_and_db, monkeypatch
):
    app, _ = app_and_db

    with app.app_context():
        db.session.add_all(
            [
                Channel(
                    channel_username="@tracked_one", subscribers=10, is_tracked=True
                ),
                Channel(
                    channel_username="@tracked_two", subscribers=20, is_tracked=True
                ),
                Channel(
                    channel_username="@tracked_three", subscribers=30, is_tracked=True
                ),
                Channel(
                    channel_username="@not_tracked_one",
                    subscribers=40,
                    is_tracked=False,
                ),
                Channel(
                    channel_username="@not_tracked_two",
                    subscribers=50,
                    is_tracked=False,
                ),
            ]
        )
        db.session.commit()

    enqueued = []

    def fake_enqueue(channel_id, max_videos):
        enqueued.append((channel_id, max_videos))
        return f"job-{len(enqueued)}"

    monkeypatch.setattr(tasks, "enqueue_channel_job", fake_enqueue)
    monkeypatch.setattr(
        tasks,
        "get_channel_id_from_url",
        lambda url: f"UC_{url.rsplit('/', 1)[-1].replace('@', '')}",
    )

    with app.app_context():
        summary = tasks.scrape_tracked_channels()

    assert summary["tracked_channels"] == 3
    assert summary["enqueued_jobs"] == 3
    assert summary["failed"] == 0
    assert len(enqueued) == 3

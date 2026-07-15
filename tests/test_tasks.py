from flask import Flask
import pytest

import tasks
from models import ApiRawPayload, Channel, CollectionRun, Video, VideoSnapshot, db


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


def test_process_channel_background_batches_and_records_collection_run(
    app_and_db, monkeypatch
):
    app, _ = app_and_db

    monkeypatch.setattr(
        tasks,
        "get_channel_videos_with_metadata",
        lambda channel_id, max_videos: {
            "video_ids": ["video_1", "video_2"],
            "mode": "uploads_playlist",
            "quota_estimate": 3,
            "sampling_metadata": {
                "channelId": channel_id,
                "playlistId": "UU123",
                "maxResults": max_videos,
            },
        },
    )
    monkeypatch.setattr(
        tasks,
        "get_videos_data",
        lambda video_ids: {
            video_id: {
                "youtube_video_id": video_id,
                "youtube_channel_id": "UC123",
                "channel_username": "@test_channel",
                "subscribers": 100,
                "title": f"Title {video_id}",
                "views": 1000,
            }
            for video_id in video_ids
        },
    )
    job_meta_updates = []
    monkeypatch.setattr(
        tasks,
        "_update_current_job_meta",
        lambda **updates: job_meta_updates.append(updates),
    )

    with app.app_context():
        summary = tasks._process_channel_background_impl("UC123", 2)

        assert summary == {
            "inserted": 2,
            "updated_or_skipped": 0,
            "failed": 0,
            "total_videos": 2,
        }
        collection_run = CollectionRun.query.one()
        assert collection_run.run_type == "channel_uploads"
        assert collection_run.status == "completed"
        assert collection_run.items_found == 2
        assert collection_run.items_saved == 2
        assert collection_run.quota_estimate == 3
        assert ApiRawPayload.query.one().endpoint == "sampling_metadata"
        assert Video.query.count() == 2
        assert {
            snapshot.collection_run_id for snapshot in VideoSnapshot.query.all()
        } == {collection_run.id}
        final_update = job_meta_updates[-1]
        assert final_update["processed"] == 2
        assert final_update["skipped"] == 0
        assert final_update["failed"] == 0
        assert final_update["inserted"] == 2

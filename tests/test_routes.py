import io

import pytest
from openpyxl import load_workbook

import routes
from app import create_app
from models import Channel, ChannelHistory, Video, db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()
        with app.test_client() as test_client:
            yield test_client
        db.session.remove()
        db.drop_all()


def test_api_data_empty(client):
    response = client.get("/api/data")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["total_videos"] == 0


def test_api_data_pagination_limits(client):
    with client.application.app_context():
        channels = [
            Channel(channel_username=f"@channel_{idx}", subscribers=idx)
            for idx in range(30)
        ]
        db.session.add_all(channels)
        db.session.commit()

    response = client.get("/api/data?page=1&limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["channels"]["items"]) == 10

    pagination = payload["channels"]["pagination"]
    assert pagination["total_items"] == 30
    assert pagination["total_pages"] == 3
    assert pagination["current_page"] == 1
    assert pagination["has_next"] is True


def test_api_data_invalid_parameters_fallback(client):
    response = client.get("/api/data?page=-5&limit=invalid_string")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["query"]["page"] == 1
    assert payload["query"]["limit"] == 25


def test_api_data_includes_and_sorts_by_engagement_rate(client):
    with client.application.app_context():
        channel = Channel(channel_username="@engagement_sort_channel", subscribers=2000)
        db.session.add(channel)
        db.session.flush()

        high_engagement = Video(
            youtube_video_id="engagement_sort_high",
            title="High engagement",
            views=100,
            likes=8,
            comments=2,
            channel_id=channel.id,
        )
        low_engagement = Video(
            youtube_video_id="engagement_sort_low",
            title="Low engagement",
            views=100,
            likes=1,
            comments=1,
            channel_id=channel.id,
        )
        zero_views = Video(
            youtube_video_id="engagement_sort_zero",
            title="Zero views",
            views=0,
            likes=999,
            comments=999,
            channel_id=channel.id,
        )
        db.session.add_all([high_engagement, low_engagement, zero_views])
        db.session.commit()

    response = client.get("/api/data?sort_column=engagement_rate&sort_direction=desc")

    assert response.status_code == 200
    payload = response.get_json()
    items = payload["videos"]["items"]
    assert payload["query"]["sort_column"] == "engagement_rate"
    assert len(items) >= 3
    assert "engagement_rate" in items[0]
    assert items[0]["youtube_video_id"] == "engagement_sort_high"
    assert items[0]["engagement_rate"] == 10.0
    assert items[-1]["youtube_video_id"] == "engagement_sort_zero"
    assert items[-1]["engagement_rate"] == 0.0


def test_api_data_sorts_by_like_and_comment_rate(client):
    with client.application.app_context():
        channel = Channel(channel_username="@rate_sort_channel", subscribers=1500)
        db.session.add(channel)
        db.session.flush()

        highest_like_rate = Video(
            youtube_video_id="like_rate_high",
            title="Highest like rate",
            views=100,
            likes=20,
            comments=1,
            channel_id=channel.id,
        )
        highest_comment_rate = Video(
            youtube_video_id="comment_rate_high",
            title="Highest comment rate",
            views=100,
            likes=1,
            comments=30,
            channel_id=channel.id,
        )
        baseline = Video(
            youtube_video_id="rate_baseline",
            title="Baseline",
            views=100,
            likes=2,
            comments=2,
            channel_id=channel.id,
        )
        db.session.add_all([highest_like_rate, highest_comment_rate, baseline])
        db.session.commit()

    like_rate_response = client.get(
        "/api/data?sort_column=like_rate&sort_direction=desc"
    )
    assert like_rate_response.status_code == 200
    like_rate_items = like_rate_response.get_json()["videos"]["items"]
    assert like_rate_items[0]["youtube_video_id"] == "like_rate_high"
    assert like_rate_items[0]["like_rate"] == 20.0

    comment_rate_response = client.get(
        "/api/data?sort_column=comment_rate&sort_direction=desc"
    )
    assert comment_rate_response.status_code == 200
    comment_rate_items = comment_rate_response.get_json()["videos"]["items"]
    assert comment_rate_items[0]["youtube_video_id"] == "comment_rate_high"
    assert comment_rate_items[0]["comment_rate"] == 30.0


def test_single_video_scraper_displays_engagement_rates(client, monkeypatch):
    monkeypatch.setattr(routes, "YOUTUBE_API_KEY", "test-api-key")
    monkeypatch.setattr(
        routes,
        "get_video_data",
        lambda _video_id: {
            "youtube_video_id": "dQw4w9WgXcQ",
            "channel_username": "@test_channel",
            "subscribers": "1000",
            "title": "Single video test",
            "views": "10000",
            "likes": "500",
            "comments": "200",
            "posted": "2025-01-01",
            "video_length": "0:05:00",
            "transcript": "Test transcript",
            "description": "Test description",
        },
    )

    response = client.post(
        "/",
        data={"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Engagement Rate" in body
    assert "Like Rate" in body
    assert "Comment Rate" in body
    assert "5.00%" in body
    assert "2.00%" in body
    assert "7.00%" in body


def test_export_csv_success(client):
    response = client.get("/export?format=csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.get_data(as_text=True)
    assert "=== VIDEOS ===" in body
    assert "=== CHANNELS ===" in body
    assert "=== CHANNEL_VIDEOS ===" in body
    assert "=== CHANNEL_HISTORY ===" in body


def test_export_xlsx_success(client):
    response = client.get("/export?format=xlsx")

    assert response.status_code == 200
    assert (
        response.mimetype
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    workbook = load_workbook(io.BytesIO(response.data), read_only=True)
    try:
        assert set(workbook.sheetnames) == {
            "videos",
            "channels",
            "channel_videos",
            "channel_history",
        }
    finally:
        workbook.close()


def test_video_detail_route_success(client):
    with client.application.app_context():
        channel = Channel(channel_username="@video_detail_channel", subscribers=1200)
        db.session.add(channel)
        db.session.flush()

        video = Video(
            youtube_video_id="video_detail_123",
            title="Video detail test",
            views=100,
            likes=10,
            comments=1,
            posted="2025-01-01",
            video_length="5:00",
            channel_id=channel.id,
        )
        db.session.add(video)
        db.session.commit()
        video_id = video.id

    response = client.get(f"/video/{video_id}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Video detail test" in body


def test_video_like_rate_bdd_scenario(client):
    with client.application.app_context():
        channel = Channel(channel_username="@engagement_channel", subscribers=8000)
        db.session.add(channel)
        db.session.flush()

        video = Video(
            youtube_video_id="engagement_1",
            title="Engagement baseline",
            views=10000,
            likes=500,
            comments=200,
            channel_id=channel.id,
        )
        db.session.add(video)
        db.session.commit()
        video_id = video.id

        assert video.like_rate == 5.0
        assert video.comment_rate == 2.0
        assert video.engagement_rate == 7.0

    response = client.get(f"/video/{video_id}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "5.00%" in body
    assert "2.00%" in body
    assert "7.00%" in body


def test_video_engagement_handles_zero_views_and_none(client):
    with client.application.app_context():
        channel = Channel(channel_username="@zero_metrics_channel", subscribers=900)
        db.session.add(channel)
        db.session.flush()

        zero_video = Video(
            youtube_video_id="engagement_zero",
            title="Zero Engagement",
            views=0,
            likes=0,
            comments=0,
            channel_id=channel.id,
        )
        none_video = Video(
            youtube_video_id="engagement_none",
            title="None Engagement",
            views=None,
            likes=None,
            comments=None,
            channel_id=channel.id,
        )
        db.session.add_all([zero_video, none_video])
        db.session.commit()
        zero_video_id = zero_video.id

        assert zero_video.like_rate == 0.0
        assert zero_video.comment_rate == 0.0
        assert zero_video.engagement_rate == 0.0
        assert none_video.like_rate == 0.0
        assert none_video.comment_rate == 0.0
        assert none_video.engagement_rate == 0.0

    response = client.get(f"/video/{zero_video_id}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "0.00%" in body


def test_channel_detail_route_success(client):
    with client.application.app_context():
        channel = Channel(channel_username="@channel_detail_channel", subscribers=5000)
        db.session.add(channel)
        db.session.flush()

        video = Video(
            youtube_video_id="channel_detail_video_1",
            title="Linked channel video",
            views=250,
            likes=25,
            comments=3,
            channel_id=channel.id,
        )
        history = ChannelHistory(
            channel_id=channel.id,
            previous_subscribers=4900,
        )
        db.session.add_all([video, history])
        db.session.commit()
        channel_id = channel.id

    response = client.get(f"/channel/{channel_id}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "@channel_detail_channel" in body
    assert "Linked channel video" in body
    assert "4,900" in body

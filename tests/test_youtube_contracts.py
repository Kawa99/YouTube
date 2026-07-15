import json
from pathlib import Path

import youtube_api
from services.youtube.parsers import parse_channel_item, parse_video_item
from services.youtube.quota import (
    QuotaTracker,
    estimate_channel_batch_cost,
    estimate_channel_uploads_cost,
    estimate_search_cost,
    estimate_video_batch_cost,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "youtube"


def load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text())


def test_youtube_fixture_contract_parses_video_and_channel_payloads():
    video_item = load_fixture("videos_list_response.json")["items"][0]
    channel_item = load_fixture("channels_list_response.json")["items"][0]

    channel = parse_channel_item(channel_item)
    video = parse_video_item(
        video_item,
        channel_item,
        transcript="Fixture transcript.",
        transcript_status="available",
    )

    assert channel == {
        "youtube_channel_id": "UC38IQsAvIsxxjztdMZQtwHA",
        "channel_username": "@RickAstleyYT",
        "channel_name": "Rick Astley",
        "handle": "@RickAstleyYT",
        "custom_url": "@RickAstleyYT",
        "canonical_url": "https://www.youtube.com/channel/UC38IQsAvIsxxjztdMZQtwHA",
        "channel_description": "Official channel fixture.",
        "channel_published_at": "2009-01-01T00:00:00Z",
        "channel_view_count": "500000000",
        "channel_video_count": "200",
        "subscribers": "1000000",
        "country": "GB",
        "channel_default_language": "en",
    }
    assert video["youtube_video_id"] == "dQw4w9WgXcQ"
    assert video["youtube_channel_id"] == "UC38IQsAvIsxxjztdMZQtwHA"
    assert video["thumbnail_quality"] == "high"
    assert video["duration_seconds"] == 213
    assert video["video_length"] == "0:03:33"
    assert video["caption_available"] is True
    assert video["transcript_status"] == "available"


def test_get_videos_data_uses_saved_fixture_payloads_without_live_api(monkeypatch):
    videos_payload = load_fixture("videos_list_response.json")
    channels_payload = load_fixture("channels_list_response.json")

    def fake_youtube_api_get(endpoint, _params):
        if endpoint == "videos":
            return videos_payload
        if endpoint == "channels":
            return channels_payload
        return {}

    monkeypatch.setattr(youtube_api, "youtube_api_get", fake_youtube_api_get)
    monkeypatch.setattr(youtube_api, "get_transcript", lambda _video_id: "Fixture")

    result = youtube_api.get_videos_data(["dQw4w9WgXcQ"], include_transcripts=True)

    assert set(result) == {"dQw4w9WgXcQ"}
    assert result["dQw4w9WgXcQ"]["channel_username"] == "@RickAstleyYT"
    assert result["dQw4w9WgXcQ"]["transcript_text"] == "Fixture"


def test_quota_estimation_is_deterministic_for_collection_modes():
    assert estimate_video_batch_cost(0) == 0
    assert estimate_video_batch_cost(1) == 1
    assert estimate_video_batch_cost(50) == 1
    assert estimate_video_batch_cost(51) == 2
    assert estimate_channel_batch_cost(51) == 2
    assert estimate_channel_uploads_cost(120) == 4
    assert estimate_search_cost(3) == 300

    tracker = QuotaTracker(daily_budget=105)
    assert tracker.add("search") == 100
    assert tracker.remaining == 5
    assert tracker.would_exceed(6) is True
    assert tracker.would_exceed(5) is False

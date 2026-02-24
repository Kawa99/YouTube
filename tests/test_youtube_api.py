from unittest.mock import MagicMock, patch

import pytest

import youtube_api
from youtube_api import extract_video_id, get_video_data


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_valid_urls(url):
    assert extract_video_id(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.google.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=123",
        "https://youtu.be/",
        "",
        None,
    ],
)
def test_extract_video_id_invalid_urls(url):
    assert extract_video_id(url) is None


def test_get_video_data_parses_expected_dictionary():
    fake_video_payload = {
        "items": [
            {
                "snippet": {
                    "title": "Never Gonna Give You Up",
                    "description": "Test description",
                    "publishedAt": "2009-10-25T06:57:33Z",
                    "channelId": "UC38IQsAvIsxxjztdMZQtwHA",
                },
                "statistics": {
                    "viewCount": "12345",
                    "likeCount": "678",
                    "commentCount": "90",
                },
                "contentDetails": {"duration": "PT3M33S"},
            }
        ]
    }
    fake_channel_payload = {
        "items": [
            {
                "snippet": {"customUrl": "@RickAstleyYT"},
                "statistics": {"subscriberCount": "1000000"},
            }
        ]
    }

    with (
        patch.object(
            youtube_api.session,
            "get",
            side_effect=[
                FakeResponse(fake_video_payload),
                FakeResponse(fake_channel_payload),
            ],
        ) as mocked_get,
        patch("youtube_api.get_transcript", return_value="Mock transcript"),
    ):
        result = get_video_data("dQw4w9WgXcQ")

    assert mocked_get.call_count == 2
    assert result == {
        "youtube_video_id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "description": "Test description",
        "views": "12345",
        "likes": "678",
        "comments": "90",
        "posted": "2009-10-25",
        "channel_username": "@RickAstleyYT",
        "subscribers": "1000000",
        "video_length": "0:03:33",
        "transcript": "Mock transcript",
    }


@patch("youtube_api.get_transcript")
@patch("youtube_api.youtube_api_get")
def test_get_video_data_success(mock_youtube_api_get, mock_get_transcript):
    mock_videos_response = {
        "items": [
            {
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "title": "Test Video",
                    "description": "Test Desc",
                    "channelId": "UC123",
                    "publishedAt": "2023-10-01T12:00:00Z",
                },
                "statistics": {
                    "viewCount": "1000",
                    "likeCount": "50",
                    "commentCount": "10",
                },
                "contentDetails": {"duration": "PT1H2M10S"},
            }
        ]
    }
    mock_channels_response = {
        "items": [
            {
                "snippet": {"customUrl": "@TestChannel"},
                "statistics": {"subscriberCount": "5000"},
            }
        ]
    }

    def mock_api_side_effect(endpoint, params):
        if endpoint == "videos":
            return mock_videos_response
        if endpoint == "channels":
            return mock_channels_response
        return {}

    mock_youtube_api_get.side_effect = mock_api_side_effect
    mock_get_transcript.return_value = "Mocked transcript text"

    # Keep an explicit MagicMock use so the imported symbol is intentional.
    result_sink = MagicMock()

    result = get_video_data("dQw4w9WgXcQ")
    result_sink(result)

    assert result["title"] == "Test Video"
    assert result["views"] == "1000"
    assert result["posted"] == "2023-10-01"
    assert result["channel_username"] == "@TestChannel"
    assert result["subscribers"] == "5000"
    assert result["video_length"] == "1:02:10"
    assert result["transcript"] == "Mocked transcript text"


@patch("youtube_api.get_transcript")
@patch("youtube_api.youtube_api_get")
def test_get_video_data_missing_fields(mock_youtube_api_get, mock_get_transcript):
    mock_videos_response = {
        "items": [
            {
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "title": "Video Without Stats",
                    "description": "No stats available",
                    "channelId": "UC123",
                },
                "contentDetails": {"duration": "PT45S"},
            }
        ]
    }
    mock_channels_response = {"items": []}

    def mock_api_side_effect(endpoint, params):
        if endpoint == "videos":
            return mock_videos_response
        if endpoint == "channels":
            return mock_channels_response
        return {}

    mock_youtube_api_get.side_effect = mock_api_side_effect
    mock_get_transcript.return_value = (
        "Transcript unavailable or disabled by the uploader."
    )

    result = get_video_data("dQw4w9WgXcQ")

    assert result["views"] in (0, "0")
    assert result["likes"] in (0, "0")
    assert result["comments"] in (0, "0")
    assert result["posted"] == ""
    assert result["channel_username"] == "@UC123"
    assert result["subscribers"] == "0"
    assert result["transcript"] == "Transcript unavailable or disabled by the uploader."


@patch("youtube_api.get_transcript")
@patch("youtube_api.youtube_api_get")
def test_get_video_data_invalid_id(mock_youtube_api_get, mock_get_transcript):
    mock_youtube_api_get.return_value = {"items": []}
    mock_get_transcript.return_value = "unused"

    result = get_video_data("invalid_id")

    assert result is None

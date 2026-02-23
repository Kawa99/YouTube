import os
import random
import re
import time
from urllib.parse import parse_qs, urlparse

import isodate
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from youtube_transcript_api import YouTubeTranscriptApi, _errors as transcript_errors

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = (3.05, 15)
API_MAX_RETRIES = int(os.environ.get("API_MAX_RETRIES", "5"))
API_BACKOFF_BASE_SECONDS = float(os.environ.get("API_BACKOFF_BASE_SECONDS", "0.5"))
TRANSCRIPT_UNAVAILABLE_MESSAGE = "Transcript unavailable or disabled by the uploader."
YOUTUBE_VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
YOUTUBE_CHANNEL_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _transcript_error(name):
    return getattr(transcript_errors, name, type(name, (Exception,), {}))


TranscriptsDisabled = _transcript_error("TranscriptsDisabled")
NoTranscriptFound = _transcript_error("NoTranscriptFound")
NON_RETRIABLE_TRANSCRIPT_EXCEPTIONS = (
    TranscriptsDisabled,
    NoTranscriptFound,
    _transcript_error("VideoUnavailable"),
    _transcript_error("InvalidVideoId"),
    _transcript_error("NotTranslatable"),
    _transcript_error("TranslationLanguageNotAvailable"),
)
RETRIABLE_TRANSCRIPT_EXCEPTIONS = (
    _transcript_error("TooManyRequests"),
    _transcript_error("RequestBlocked"),
    _transcript_error("IpBlocked"),
    _transcript_error("CouldNotRetrieveTranscript"),
    _transcript_error("YouTubeRequestFailed"),
)

# Create a resilient session for outbound HTTP calls.
session = requests.Session()
retries = Retry(
    total=API_MAX_RETRIES,
    connect=API_MAX_RETRIES,
    read=API_MAX_RETRIES,
    status=API_MAX_RETRIES,
    backoff_factor=API_BACKOFF_BASE_SECONDS,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset({"GET"}),
    raise_on_status=False,
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))


def _sleep_with_backoff(attempt, base_delay=API_BACKOFF_BASE_SECONDS, max_delay=8.0):
    delay = min(max_delay, base_delay * (2 ** attempt))
    jitter = random.uniform(0, delay * 0.2 if delay > 0 else 0)
    time.sleep(delay + jitter)


def request_json_with_retry(url, params=None, timeout=REQUEST_TIMEOUT):
    """GET JSON with a retry-enabled session."""
    params = params or {}

    try:
        response = session.get(url, params=params, timeout=timeout)
        if response.status_code >= 400:
            return {}
        return response.json()
    except (requests.RequestException, ValueError):
        return {}


def youtube_api_get(endpoint, params):
    payload = dict(params)
    payload["key"] = YOUTUBE_API_KEY
    return request_json_with_retry(f"{YOUTUBE_API_BASE_URL}/{endpoint}", params=payload)


def _parse_input_url(raw_url):
    if not raw_url:
        return None

    normalized = raw_url.strip()
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    if not parsed.netloc:
        return None
    return parsed


def is_valid_youtube_video_url(video_url):
    parsed = _parse_input_url(video_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_VIDEO_HOSTS)


def is_valid_youtube_channel_url(channel_url):
    parsed = _parse_input_url(channel_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_CHANNEL_HOSTS)


def extract_video_id(video_url):
    """Extract video ID from supported YouTube URL formats."""
    parsed = _parse_input_url(video_url)
    if not parsed:
        return None

    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id = None

    if host in {"youtu.be", "www.youtu.be"}:
        if path_parts:
            video_id = path_parts[0]
    elif host in YOUTUBE_CHANNEL_HOSTS:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts and path_parts[0] in {"embed", "shorts", "live"} and len(path_parts) > 1:
            video_id = path_parts[1]

    if not video_id or not VIDEO_ID_PATTERN.match(video_id):
        return None

    return video_id


def extract_channel_info(channel_url):
    """Extract (identifier_type, identifier) from common YouTube channel URL formats."""
    parsed = _parse_input_url(channel_url)
    if not parsed:
        return None, None

    host = parsed.netloc.lower()
    if host not in YOUTUBE_CHANNEL_HOSTS:
        return None, None

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None, None

    first = path_parts[0]
    if first == "channel" and len(path_parts) > 1:
        return "channel_id", path_parts[1]
    if first == "user" and len(path_parts) > 1:
        return "username", path_parts[1]
    if first == "c" and len(path_parts) > 1:
        return "custom", path_parts[1]
    if first.startswith("@"):
        return "handle", first

    reserved = {"watch", "shorts", "embed", "playlist", "feed", "results", "live"}
    if first not in reserved:
        return "custom", first

    return None, None


def get_channel_id_from_url(channel_url):
    """Resolve a canonical YouTube channel ID (UC...) from various URL formats."""
    identifier_type, identifier = extract_channel_info(channel_url)
    if not identifier:
        return None

    handle_no_at = identifier[1:] if identifier.startswith("@") else identifier

    call_plan = []
    if identifier_type == "channel_id":
        call_plan.append(("channels", {"part": "id", "id": identifier}))
    elif identifier_type == "username":
        call_plan.append(("channels", {"part": "id", "forUsername": identifier}))
    elif identifier_type == "handle":
        call_plan.append(("channels", {"part": "id", "forHandle": identifier}))
        call_plan.append(("channels", {"part": "id", "forHandle": handle_no_at}))
    else:
        call_plan.append(("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}))

    call_plan.extend(
        [
            ("channels", {"part": "id", "id": identifier}),
            ("channels", {"part": "id", "forUsername": identifier}),
            ("channels", {"part": "id", "forHandle": identifier}),
            ("channels", {"part": "id", "forHandle": handle_no_at}),
            ("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}),
        ]
    )

    for endpoint, params in call_plan:
        response = youtube_api_get(endpoint, params)
        items = response.get("items", [])
        if not items:
            continue

        if endpoint == "channels":
            return items[0].get("id")

        item = items[0]
        item_id = item.get("id")
        search_id = item_id.get("channelId") if isinstance(item_id, dict) else None
        search_id = search_id or item.get("snippet", {}).get("channelId")
        if search_id:
            return search_id

    return None


def get_channel_videos_from_search(channel_id, max_results=50):
    """Fallback: fetch channel videos using search endpoint ordered by date."""
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(50, max_results - len(videos)),
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        response = youtube_api_get("search", params)
        items = response.get("items", [])
        if not items:
            break

        for item in items:
            item_id = item.get("id")
            video_id = item_id.get("videoId") if isinstance(item_id, dict) else None
            if video_id:
                videos.append(video_id)
                if len(videos) >= max_results:
                    break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def get_channel_videos(channel_id, max_results=50):
    """Get up to max_results recent video IDs from a channel uploads playlist."""
    videos = []
    next_page_token = None

    channel_response = youtube_api_get("channels", {"part": "contentDetails", "id": channel_id})
    items = channel_response.get("items", [])
    if not items:
        return videos

    uploads_playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        return get_channel_videos_from_search(channel_id, max_results)

    while len(videos) < max_results:
        playlist_params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(50, max_results - len(videos)),
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token

        playlist_response = youtube_api_get("playlistItems", playlist_params)
        items = playlist_response.get("items", [])
        if not items:
            break

        for item in items:
            if len(videos) >= max_results:
                break
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                videos.append(video_id)

        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token:
            break

    if not videos:
        return get_channel_videos_from_search(channel_id, max_results)

    return videos


def parse_duration(duration):
    """Converts YouTube ISO 8601 duration format to HH:MM:SS."""
    try:
        parsed_duration = isodate.parse_duration(duration)
        return str(parsed_duration)
    except Exception:
        return "Unknown"


def _should_retry_transcript_exception(exc):
    if isinstance(exc, NON_RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return False

    if isinstance(exc, RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return True

    message = str(exc).lower()
    retryable_markers = ["429", "rate limit", "timed out", "temporar", "try again"]
    return any(marker in message for marker in retryable_markers)


def get_transcript(video_id):
    """Fetch transcript with retry for transient errors."""
    api = YouTubeTranscriptApi()

    for attempt in range(API_MAX_RETRIES):
        try:
            transcript = api.fetch(video_id)
            return " ".join([line.text for line in transcript])
        except (TranscriptsDisabled, NoTranscriptFound):
            return TRANSCRIPT_UNAVAILABLE_MESSAGE
        except Exception as exc:
            if attempt >= API_MAX_RETRIES - 1 or not _should_retry_transcript_exception(exc):
                return TRANSCRIPT_UNAVAILABLE_MESSAGE
            _sleep_with_backoff(attempt)

    return TRANSCRIPT_UNAVAILABLE_MESSAGE


def get_video_data(video_id):
    """Fetch video details including channel @username and subscribers."""
    response = youtube_api_get(
        "videos",
        {"part": "snippet,statistics,contentDetails", "id": video_id},
    )

    items = response.get("items", [])
    if not items:
        return None

    data = items[0]
    snippet = data.get("snippet", {})
    statistics = data.get("statistics", {})
    content_details = data.get("contentDetails", {})
    channel_id = snippet.get("channelId")

    channel_username = f"@{channel_id}" if channel_id else "@unknown"
    subscribers = "0"

    if channel_id:
        channel_response = youtube_api_get(
            "channels",
            {"part": "snippet,statistics", "id": channel_id},
        )
        channel_items = channel_response.get("items", [])
        if channel_items:
            channel_snippet = channel_items[0].get("snippet", {})
            channel_stats = channel_items[0].get("statistics", {})
            channel_username = channel_snippet.get("customUrl", f"@{channel_id}")
            subscribers = channel_stats.get("subscriberCount", "0")

    published = snippet.get("publishedAt", "")
    posted = published.split("T")[0] if published else ""

    return {
        "youtube_video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "views": statistics.get("viewCount", 0),
        "likes": statistics.get("likeCount", 0),
        "comments": statistics.get("commentCount", 0),
        "posted": posted,
        "channel_username": channel_username,
        "subscribers": subscribers,
        "video_length": parse_duration(content_details.get("duration", "")),
        "transcript": get_transcript(video_id),
    }

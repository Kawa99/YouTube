import os
import re
import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple, Type
from urllib.parse import ParseResult, parse_qs, urlparse

from services.youtube.client import YouTubeClient, create_retry_session
from services.youtube.errors import YouTubeAPIError
from services.youtube.parsers import (
    best_thumbnail_url,
    parse_duration as parse_youtube_duration,
    parse_video_item,
)
from services.youtube.quota import (
    DEFAULT_DAILY_QUOTA_BUDGET,
    estimate_channel_batch_cost,
    estimate_channel_uploads_cost,
    estimate_search_cost,
    estimate_video_batch_cost,
)
from youtube_transcript_api import YouTubeTranscriptApi, _errors as transcript_errors

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = (3.05, 15)
API_MAX_RETRIES = int(os.environ.get("API_MAX_RETRIES", "5"))
API_BACKOFF_BASE_SECONDS = float(os.environ.get("API_BACKOFF_BASE_SECONDS", "0.5"))
TRANSCRIPTS_ENABLED = os.environ.get("TRANSCRIPTS_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TRANSCRIPT_FETCH_MODE = os.environ.get("TRANSCRIPT_FETCH_MODE", "manual").lower()
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


def _transcript_error(name: str) -> Type[Exception]:
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

# Public for legacy tests; the actual request policy lives in services/youtube/client.py.
session = create_retry_session(API_MAX_RETRIES, API_BACKOFF_BASE_SECONDS)
client = YouTubeClient(
    api_key=YOUTUBE_API_KEY or "missing-api-key",
    session=session,
    max_retries=API_MAX_RETRIES,
    backoff_base_seconds=API_BACKOFF_BASE_SECONDS,
    timeout=REQUEST_TIMEOUT,
    daily_quota_budget=DEFAULT_DAILY_QUOTA_BUDGET,
)


def _sleep_with_backoff(
    attempt: int,
    base_delay: float = API_BACKOFF_BASE_SECONDS,
    max_delay: float = 8.0,
) -> None:
    client.backoff_base_seconds = base_delay
    client._sleep_with_backoff(attempt, max_delay=max_delay)


def request_json_with_retry(
    url: str,
    params: Optional[Mapping[str, Any]] = None,
    timeout: Tuple[float, float] = REQUEST_TIMEOUT,
) -> Dict[str, Any]:
    """GET JSON with a retry-enabled session."""
    params = params or {}
    try:
        response = session.get(url, params=params, timeout=timeout)
        if response.status_code >= 400:
            logger.error("YouTube request failed with HTTP %s.", response.status_code)
            return {}
        return response.json()
    except Exception as exc:
        logger.exception("YouTube request failed: %s", exc)
        return {}


def youtube_api_get(endpoint: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        return client.get(endpoint, params)
    except YouTubeAPIError as exc:
        logger.exception("YouTube API %s request failed: %s", endpoint, exc)
        return {}


def _parse_input_url(raw_url: Optional[str]) -> Optional[ParseResult]:
    if not raw_url:
        return None

    normalized = raw_url.strip()
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    if not parsed.netloc:
        return None
    return parsed


def is_valid_youtube_video_url(video_url: Optional[str]) -> bool:
    parsed = _parse_input_url(video_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_VIDEO_HOSTS)


def is_valid_youtube_channel_url(channel_url: Optional[str]) -> bool:
    parsed = _parse_input_url(channel_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_CHANNEL_HOSTS)


def extract_video_id(video_url: Optional[str]) -> Optional[str]:
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
        elif (
            path_parts
            and path_parts[0] in {"embed", "shorts", "live"}
            and len(path_parts) > 1
        ):
            video_id = path_parts[1]

    if not video_id or not VIDEO_ID_PATTERN.match(video_id):
        return None

    return video_id


def extract_channel_info(
    channel_url: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
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


def get_channel_id_from_url(channel_url: Optional[str]) -> Optional[str]:
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
        call_plan.append(
            (
                "search",
                {
                    "part": "snippet",
                    "type": "channel",
                    "q": identifier,
                    "maxResults": 1,
                },
            )
        )

    call_plan.extend(
        [
            ("channels", {"part": "id", "id": identifier}),
            ("channels", {"part": "id", "forUsername": identifier}),
            ("channels", {"part": "id", "forHandle": identifier}),
            ("channels", {"part": "id", "forHandle": handle_no_at}),
            (
                "search",
                {
                    "part": "snippet",
                    "type": "channel",
                    "q": identifier,
                    "maxResults": 1,
                },
            ),
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


def get_channel_videos_from_search(channel_id: str, max_results: int = 50) -> List[str]:
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


def get_channel_videos(channel_id: str, max_results: int = 50) -> List[str]:
    """Get up to max_results recent video IDs from a channel uploads playlist."""
    result = get_channel_videos_with_metadata(channel_id, max_results)
    return result["video_ids"]


def get_channel_videos_with_metadata(
    channel_id: str, max_results: int = 50, mode: str = "uploads_playlist"
) -> Dict[str, Any]:
    """Collect channel video IDs and preserve sampling metadata for run records."""
    videos = []
    next_page_token = None
    page_tokens_used = []
    quota_estimate = estimate_channel_uploads_cost(max_results)

    if mode == "search":
        videos = get_channel_videos_from_search(channel_id, max_results)
        return {
            "video_ids": videos,
            "mode": "search",
            "quota_estimate": estimate_search_cost()
            + estimate_video_batch_cost(len(videos))
            + estimate_channel_batch_cost(len(videos)),
            "sampling_metadata": {
                "channelId": channel_id,
                "order": "date",
                "maxResults": max_results,
                "collectedVia": "search",
            },
        }

    channel_response = youtube_api_get(
        "channels", {"part": "contentDetails", "id": channel_id}
    )
    items = channel_response.get("items", [])
    if not items:
        return {
            "video_ids": videos,
            "mode": mode,
            "quota_estimate": quota_estimate,
            "sampling_metadata": {
                "channelId": channel_id,
                "maxResults": max_results,
                "collectedVia": "uploads_playlist",
            },
        }

    uploads_playlist_id = (
        items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    )
    if not uploads_playlist_id:
        fallback_videos = get_channel_videos_from_search(channel_id, max_results)
        return {
            "video_ids": fallback_videos,
            "mode": "search_fallback",
            "quota_estimate": quota_estimate
            + estimate_video_batch_cost(len(fallback_videos))
            + estimate_channel_batch_cost(len(fallback_videos)),
            "sampling_metadata": {
                "channelId": channel_id,
                "order": "date",
                "maxResults": max_results,
                "collectedVia": "search_fallback",
            },
        }

    while len(videos) < max_results:
        playlist_params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(50, max_results - len(videos)),
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token
            page_tokens_used.append(next_page_token)

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
        fallback_videos = get_channel_videos_from_search(channel_id, max_results)
        return {
            "video_ids": fallback_videos,
            "mode": "search_fallback",
            "quota_estimate": quota_estimate
            + estimate_video_batch_cost(len(fallback_videos))
            + estimate_channel_batch_cost(len(fallback_videos)),
            "sampling_metadata": {
                "channelId": channel_id,
                "order": "date",
                "maxResults": max_results,
                "collectedVia": "search_fallback",
            },
        }

    return {
        "video_ids": videos,
        "mode": "uploads_playlist",
        "quota_estimate": quota_estimate
        + estimate_video_batch_cost(len(videos))
        + estimate_channel_batch_cost(len(videos)),
        "sampling_metadata": {
            "channelId": channel_id,
            "playlistId": uploads_playlist_id,
            "maxResults": max_results,
            "pageTokensUsed": page_tokens_used,
            "collectedVia": "uploads_playlist",
        },
    }


def keyword_search_videos(
    query: str,
    *,
    max_results: int = 50,
    order: str = "relevance",
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    region_code: Optional[str] = None,
    relevance_language: Optional[str] = None,
) -> Dict[str, Any]:
    """Collect video IDs from keyword search with explicit sampling metadata."""
    videos = []
    next_page_token = None
    page_tokens_used = []
    pages = 0

    while len(videos) < max_results:
        params = {
            "part": "id",
            "type": "video",
            "q": query,
            "order": order,
            "maxResults": min(50, max_results - len(videos)),
        }
        if published_after:
            params["publishedAfter"] = published_after
        if published_before:
            params["publishedBefore"] = published_before
        if region_code:
            params["regionCode"] = region_code
        if relevance_language:
            params["relevanceLanguage"] = relevance_language
        if next_page_token:
            params["pageToken"] = next_page_token
            page_tokens_used.append(next_page_token)

        response = youtube_api_get("search", params)
        pages += 1
        for item in response.get("items", []):
            item_id = item.get("id")
            video_id = item_id.get("videoId") if isinstance(item_id, dict) else None
            if video_id:
                videos.append(video_id)
                if len(videos) >= max_results:
                    break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return {
        "video_ids": videos,
        "mode": "keyword_search",
        "quota_estimate": (pages * 100)
        + estimate_video_batch_cost(len(videos))
        + estimate_channel_batch_cost(len(videos)),
        "sampling_metadata": {
            "query": query,
            "order": order,
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "regionCode": region_code,
            "relevanceLanguage": relevance_language,
            "maxResults": max_results,
            "pageTokensUsed": page_tokens_used,
        },
    }


def manual_video_url_collection(video_urls: List[str]) -> Dict[str, Any]:
    """Normalize a manual URL list into a collection payload."""
    video_ids = []
    invalid_urls = []
    for raw_url in video_urls:
        video_id = extract_video_id(raw_url)
        if video_id:
            video_ids.append(video_id)
        else:
            invalid_urls.append(raw_url)

    deduped_ids = list(dict.fromkeys(video_ids))
    return {
        "video_ids": deduped_ids,
        "mode": "manual_video_url_list",
        "quota_estimate": estimate_video_batch_cost(len(deduped_ids)),
        "sampling_metadata": {
            "inputCount": len(video_urls),
            "validVideoCount": len(deduped_ids),
            "invalidUrls": invalid_urls,
        },
    }


def parse_duration(duration: str) -> str:
    """Converts YouTube ISO 8601 duration format to HH:MM:SS."""
    return parse_youtube_duration(duration)


def _best_thumbnail_url(snippet: Mapping[str, Any]) -> str:
    return best_thumbnail_url(snippet)


def should_fetch_transcripts(include_transcripts: Optional[bool] = None) -> bool:
    if include_transcripts is not None:
        return bool(include_transcripts)
    if TRANSCRIPT_FETCH_MODE == "always":
        return True
    if TRANSCRIPT_FETCH_MODE == "never":
        return False
    return TRANSCRIPTS_ENABLED


def _should_retry_transcript_exception(exc: Exception) -> bool:
    if isinstance(exc, NON_RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return False

    if isinstance(exc, RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return True

    message = str(exc).lower()
    retryable_markers = ["429", "rate limit", "timed out", "temporar", "try again"]
    return any(marker in message for marker in retryable_markers)


def get_transcript(video_id: str) -> str:
    """Fetch transcript with retry for transient errors."""
    api = YouTubeTranscriptApi()

    for attempt in range(API_MAX_RETRIES):
        try:
            transcript = api.fetch(video_id)
            return " ".join([line.text for line in transcript])
        except (TranscriptsDisabled, NoTranscriptFound):
            return TRANSCRIPT_UNAVAILABLE_MESSAGE
        except Exception as e:
            if (
                attempt >= API_MAX_RETRIES - 1
                or not _should_retry_transcript_exception(e)
            ):
                logger.exception("An error occurred: %s", str(e))
                return TRANSCRIPT_UNAVAILABLE_MESSAGE
            logger.warning(
                "Retrying transcript fetch for video %s after transient error (%s/%s): %s",
                video_id,
                attempt + 1,
                API_MAX_RETRIES,
                str(e),
            )
            _sleep_with_backoff(attempt)

    return TRANSCRIPT_UNAVAILABLE_MESSAGE


def get_channels_data(channel_ids: List[str]) -> Dict[str, Mapping[str, Any]]:
    """Fetch channel details in batches keyed by canonical channel ID."""
    channel_map = {}
    unique_channel_ids = [
        channel_id for channel_id in dict.fromkeys(channel_ids) if channel_id
    ]

    for batch_start in range(0, len(unique_channel_ids), 50):
        batch = unique_channel_ids[batch_start : batch_start + 50]
        response = youtube_api_get(
            "channels",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
            },
        )
        for index, item in enumerate(response.get("items", [])):
            channel_id = item.get("id") or (
                batch[index] if index < len(batch) else None
            )
            if channel_id:
                item.setdefault("id", channel_id)
                channel_map[channel_id] = item

    return channel_map


def get_videos_data(
    video_ids: List[str], include_transcripts: Optional[bool] = None
) -> Dict[str, Dict[str, Any]]:
    """Fetch video metadata in videos.list batches and map parsed rows by video ID."""
    video_map = {}
    ordered_ids = [video_id for video_id in dict.fromkeys(video_ids) if video_id]
    video_items = []

    for batch_start in range(0, len(ordered_ids), 50):
        batch = ordered_ids[batch_start : batch_start + 50]
        response = youtube_api_get(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
            },
        )
        for index, item in enumerate(response.get("items", [])):
            item.setdefault("id", batch[index] if index < len(batch) else "")
            video_items.append(item)

    channel_ids = [
        item.get("snippet", {}).get("channelId")
        for item in video_items
        if item.get("snippet", {}).get("channelId")
    ]
    channel_map = get_channels_data(channel_ids)
    fetch_transcripts = should_fetch_transcripts(include_transcripts)

    for item in video_items:
        video_id = item.get("id")
        if not video_id:
            continue

        transcript = ""
        transcript_status = "skipped"
        if fetch_transcripts:
            transcript = get_transcript(video_id)
            transcript_status = (
                "unavailable"
                if transcript == TRANSCRIPT_UNAVAILABLE_MESSAGE
                else "available"
            )

        channel_id = item.get("snippet", {}).get("channelId")
        video_map[video_id] = parse_video_item(
            item,
            channel_map.get(channel_id),
            transcript=transcript,
            transcript_status=transcript_status,
        )

    return video_map


def get_video_data(
    video_id: str, include_transcript: Optional[bool] = True
) -> Optional[Dict[str, Any]]:
    """Fetch one video while preserving the historical single-video interface."""
    return get_videos_data([video_id], include_transcripts=include_transcript).get(
        video_id
    )

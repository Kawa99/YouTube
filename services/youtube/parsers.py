import logging
from typing import Any, Dict, Mapping, Optional

import isodate

logger = logging.getLogger(__name__)


def best_thumbnail_url(snippet: Mapping[str, Any]) -> str:
    thumbnails = snippet.get("thumbnails", {}) or {}
    for quality in ("maxres", "standard", "high", "medium", "default"):
        candidate = thumbnails.get(quality, {}).get("url")
        if candidate:
            return str(candidate)
    return ""


def parse_duration(duration: str) -> str:
    try:
        parsed_duration = isodate.parse_duration(duration)
        return str(parsed_duration)
    except Exception as exc:
        logger.exception("Could not parse YouTube duration %s: %s", duration, exc)
        return "Unknown"


def duration_seconds(duration: str) -> Optional[int]:
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except Exception:
        return None


def posted_date(published_at: str) -> str:
    return published_at.split("T")[0] if published_at else ""


def channel_username(channel_item: Optional[Mapping[str, Any]], channel_id: str) -> str:
    if not channel_item:
        return f"@{channel_id}" if channel_id else "@unknown"
    snippet = channel_item.get("snippet", {}) or {}
    return snippet.get("customUrl") or snippet.get("handle") or f"@{channel_id}"


def parse_channel_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    snippet = item.get("snippet", {}) or {}
    statistics = item.get("statistics", {}) or {}
    channel_id = item.get("id", "")

    return {
        "youtube_channel_id": channel_id,
        "channel_username": channel_username(item, channel_id),
        "channel_name": snippet.get("title", ""),
        "handle": snippet.get("customUrl", ""),
        "custom_url": snippet.get("customUrl", ""),
        "canonical_url": (
            f"https://www.youtube.com/channel/{channel_id}" if channel_id else ""
        ),
        "channel_description": snippet.get("description", ""),
        "channel_published_at": snippet.get("publishedAt", ""),
        "channel_view_count": statistics.get("viewCount"),
        "channel_video_count": statistics.get("videoCount"),
        "subscribers": statistics.get("subscriberCount", 0),
        "country": snippet.get("country", ""),
        "channel_default_language": snippet.get("defaultLanguage", ""),
    }


def parse_video_item(
    item: Mapping[str, Any],
    channel_item: Optional[Mapping[str, Any]] = None,
    *,
    transcript: str = "",
    transcript_status: str = "skipped",
) -> Dict[str, Any]:
    snippet = item.get("snippet", {}) or {}
    statistics = item.get("statistics", {}) or {}
    content_details = item.get("contentDetails", {}) or {}
    video_id = item.get("id", "")
    channel_id = snippet.get("channelId", "")
    published_at = snippet.get("publishedAt", "")
    duration = content_details.get("duration", "")
    channel_data = parse_channel_item(channel_item) if channel_item else {}

    return {
        "youtube_video_id": video_id,
        "youtube_channel_id": channel_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "description_full": snippet.get("description", ""),
        "thumbnail_url": best_thumbnail_url(snippet),
        "views": statistics.get("viewCount", 0),
        "likes": statistics.get("likeCount", 0),
        "comments": statistics.get("commentCount", 0),
        "posted": posted_date(published_at),
        "published_at": published_at,
        "channel_username": channel_data.get(
            "channel_username", f"@{channel_id}" if channel_id else "@unknown"
        ),
        "subscribers": channel_data.get("subscribers", 0),
        "video_length": parse_duration(duration),
        "duration_seconds": duration_seconds(duration),
        "category_id": snippet.get("categoryId", ""),
        "default_language": snippet.get("defaultLanguage", ""),
        "caption_available": content_details.get("caption") == "true",
        "transcript": transcript,
        "transcript_text": transcript,
        "transcript_status": transcript_status,
        **channel_data,
    }

import logging
from datetime import UTC, datetime

from models import (
    Channel,
    ChannelHistory,
    ChannelVideo,
    ChannelSnapshot,
    Video,
    VideoHistory,
    VideoMetadataChange,
    VideoMetadataHistory,
    VideoSnapshot,
    db,
)

logger = logging.getLogger(__name__)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_text(value, default=""):
    if value is None:
        return default
    return str(value)


def _optional_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_datetime(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None

    value = str(value).strip()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _duration_to_seconds(value):
    if isinstance(value, int):
        return value
    if not value:
        return None

    parts = str(value).split(":")
    try:
        seconds = 0
        for part in parts:
            seconds = (seconds * 60) + int(part)
        return seconds
    except ValueError:
        return None


def _description_excerpt(description):
    if not description:
        return ""
    return description[:500]


def _collection_run_id(data):
    return _optional_int(data.get("collection_run_id"))


def save_video(data, commit=True):
    """Idempotently upsert video data and append snapshot history rows."""
    youtube_video_id = data.get("youtube_video_id")
    if not youtube_video_id:
        raise ValueError("youtube_video_id is required to save video data.")

    channel_username = data.get("channel_username")
    if not channel_username:
        raise ValueError("channel_username is required to save video data.")

    subscribers = _safe_int(data.get("subscribers"), 0)
    collected_at = datetime.now(UTC).replace(tzinfo=None)
    collection_run_id = _collection_run_id(data)
    youtube_channel_id = data.get("youtube_channel_id")
    latest_channel_name = data.get("channel_name") or data.get("channel_title")
    latest_handle = data.get("handle") or (
        channel_username if str(channel_username).startswith("@") else None
    )

    try:
        channel = Channel.query.filter_by(channel_username=channel_username).first()
        if channel:
            previous_subscribers = _safe_int(channel.subscribers, 0)
            if previous_subscribers != subscribers:
                db.session.add(
                    ChannelHistory(
                        channel_id=channel.id,
                        previous_subscribers=previous_subscribers,
                    )
                )
                channel.subscribers = subscribers
        else:
            channel = Channel(
                channel_username=channel_username,
                subscribers=subscribers,
                subscriber_count=subscribers,
            )
            db.session.add(channel)
            db.session.flush()

        if (
            youtube_channel_id
            and channel.youtube_channel_id
            and channel.youtube_channel_id != youtube_channel_id
        ):
            raise ValueError(
                "youtube_channel_id does not match the existing channel identity."
            )
        if youtube_channel_id and not channel.youtube_channel_id:
            channel.youtube_channel_id = youtube_channel_id
        channel.channel_name = latest_channel_name or channel.channel_name
        channel.handle = latest_handle or channel.handle
        channel.custom_url = data.get("custom_url") or channel.custom_url
        channel.canonical_url = data.get("canonical_url") or channel.canonical_url
        channel.description = data.get("channel_description") or channel.description
        channel.published_at = (
            _safe_datetime(data.get("channel_published_at")) or channel.published_at
        )
        channel.subscriber_count = subscribers
        channel_view_count = _optional_int(data.get("channel_view_count"))
        channel_video_count = _optional_int(data.get("channel_video_count"))
        channel.view_count = (
            channel_view_count if channel_view_count is not None else channel.view_count
        )
        channel.video_count = (
            channel_video_count
            if channel_video_count is not None
            else channel.video_count
        )
        channel.country = data.get("country") or channel.country
        channel.default_language = (
            data.get("channel_default_language") or channel.default_language
        )
        channel.last_collected_at = collected_at

        video = Video.query.filter_by(youtube_video_id=youtube_video_id).first()

        latest_title = _safe_text(data.get("title"), "")
        latest_description = _safe_text(data.get("description"), "")
        latest_description_full = _safe_text(
            data.get("description_full"), latest_description
        )
        latest_description_excerpt = _safe_text(
            data.get("description_excerpt"),
            _description_excerpt(latest_description_full or latest_description),
        )
        latest_posted = _safe_text(data.get("posted"), "")
        latest_video_length = _safe_text(data.get("video_length"), "")
        latest_thumbnail_url = _safe_text(data.get("thumbnail_url"), "")
        latest_thumbnail_quality = _safe_text(data.get("thumbnail_quality"), "")
        latest_thumbnail_cached_path = _safe_text(data.get("thumbnail_cached_path"), "")
        latest_thumbnail_phash = _safe_text(data.get("thumbnail_phash"), "")
        latest_transcript = _safe_text(data.get("transcript"), "")
        latest_transcript_text = _safe_text(
            data.get("transcript_text"), latest_transcript
        )
        duration_seconds = _optional_int(data.get("duration_seconds"))
        if duration_seconds is None:
            duration_seconds = _duration_to_seconds(latest_video_length)

        if video:
            old_title = _safe_text(video.title, "")
            old_thumbnail = _safe_text(video.thumbnail_url, "")
            title_changed = old_title != latest_title
            thumbnail_changed = old_thumbnail != latest_thumbnail_url

            if title_changed or thumbnail_changed:
                db.session.add(
                    VideoMetadataHistory(
                        video_id=video.id,
                        old_title=old_title,
                        new_title=latest_title,
                        old_thumbnail=old_thumbnail,
                        new_thumbnail=latest_thumbnail_url,
                    )
                )
                if title_changed:
                    db.session.add(
                        VideoMetadataChange(
                            video_id=video.id,
                            field_name="title",
                            old_value=old_title,
                            new_value=latest_title,
                            collection_run_id=collection_run_id,
                        )
                    )
                if thumbnail_changed:
                    db.session.add(
                        VideoMetadataChange(
                            video_id=video.id,
                            field_name="thumbnail_url",
                            old_value=old_thumbnail,
                            new_value=latest_thumbnail_url,
                            collection_run_id=collection_run_id,
                        )
                    )

            video.title = latest_title
            video.description = latest_description
            video.description_full = latest_description_full
            video.description_excerpt = latest_description_excerpt
            video.views = _safe_int(data.get("views"), 0)
            video.likes = _safe_int(data.get("likes"), 0)
            video.comments = _safe_int(data.get("comments"), 0)
            video.posted = latest_posted
            video.published_at = (
                _safe_datetime(data.get("published_at")) or video.published_at
            )
            video.video_length = latest_video_length
            video.duration_seconds = duration_seconds
            video.category_id = data.get("category_id") or video.category_id
            video.default_language = (
                data.get("default_language") or video.default_language
            )
            video.caption_available = data.get(
                "caption_available", bool(latest_transcript_text)
            )
            video.thumbnail_url = latest_thumbnail_url
            video.thumbnail_quality = (
                latest_thumbnail_quality or video.thumbnail_quality
            )
            video.thumbnail_cached_path = (
                latest_thumbnail_cached_path or video.thumbnail_cached_path
            )
            video.thumbnail_phash = latest_thumbnail_phash or video.thumbnail_phash
            video.transcript = latest_transcript
            video.transcript_text = latest_transcript_text
            video.transcript_status = data.get("transcript_status") or (
                "available" if latest_transcript_text else "missing"
            )
            video.channel_id = channel.id
            video.youtube_channel_id = channel.youtube_channel_id
            video.last_collected_at = collected_at
            created = False
        else:
            video = Video(
                title=latest_title,
                description=latest_description,
                description_full=latest_description_full,
                description_excerpt=latest_description_excerpt,
                views=_safe_int(data.get("views"), 0),
                likes=_safe_int(data.get("likes"), 0),
                comments=_safe_int(data.get("comments"), 0),
                posted=latest_posted,
                published_at=_safe_datetime(data.get("published_at")),
                video_length=latest_video_length,
                duration_seconds=duration_seconds,
                category_id=data.get("category_id"),
                default_language=data.get("default_language"),
                caption_available=data.get(
                    "caption_available", bool(latest_transcript_text)
                ),
                thumbnail_url=latest_thumbnail_url,
                thumbnail_quality=latest_thumbnail_quality,
                thumbnail_cached_path=latest_thumbnail_cached_path,
                thumbnail_phash=latest_thumbnail_phash,
                transcript=latest_transcript,
                transcript_text=latest_transcript_text,
                transcript_status=data.get("transcript_status")
                or ("available" if latest_transcript_text else "missing"),
                channel_id=channel.id,
                youtube_channel_id=channel.youtube_channel_id,
                youtube_video_id=youtube_video_id,
                last_collected_at=collected_at,
            )
            db.session.add(video)
            db.session.flush()
            created = True

        existing_link = ChannelVideo.query.filter_by(
            video_id=video.id, channel_id=channel.id
        ).first()
        if not existing_link:
            db.session.add(ChannelVideo(video_id=video.id, channel_id=channel.id))

        # Append-only: store a fresh stats snapshot on every scrape/update cycle.
        db.session.add(
            VideoHistory(
                video_id=video.id,
                views=_safe_int(video.views, 0),
                likes=_safe_int(video.likes, 0),
                comments=_safe_int(video.comments, 0),
            )
        )
        db.session.add(
            VideoSnapshot(
                video_id=video.id,
                snapshot_at=collected_at,
                view_count=_safe_int(video.views, 0),
                like_count=_safe_int(video.likes, 0),
                comment_count=_safe_int(video.comments, 0),
                subscriber_count_at_snapshot=subscribers,
                collection_run_id=collection_run_id,
            )
        )
        db.session.add(
            ChannelSnapshot(
                channel_id=channel.id,
                snapshot_at=collected_at,
                subscriber_count=subscribers,
                view_count=channel.view_count,
                video_count=channel.video_count,
                collection_run_id=collection_run_id,
            )
        )

        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return {"video_id": video.id, "created": created}
    except Exception as e:
        db.session.rollback()
        logger.exception("An error occurred: %s", str(e))
        raise

import logging

from models import (
    Channel,
    ChannelHistory,
    ChannelVideo,
    Video,
    VideoHistory,
    VideoMetadataHistory,
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


def save_video(data):
    """Idempotently upsert video data and append snapshot history rows."""
    youtube_video_id = data.get("youtube_video_id")
    if not youtube_video_id:
        raise ValueError("youtube_video_id is required to save video data.")

    channel_username = data.get("channel_username")
    if not channel_username:
        raise ValueError("channel_username is required to save video data.")

    subscribers = _safe_int(data.get("subscribers"), 0)

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
                channel_username=channel_username, subscribers=subscribers
            )
            db.session.add(channel)
            db.session.flush()

        video = Video.query.filter_by(youtube_video_id=youtube_video_id).first()

        latest_title = _safe_text(data.get("title"), "")
        latest_description = _safe_text(data.get("description"), "")
        latest_posted = _safe_text(data.get("posted"), "")
        latest_video_length = _safe_text(data.get("video_length"), "")
        latest_thumbnail_url = _safe_text(data.get("thumbnail_url"), "")
        latest_transcript = _safe_text(data.get("transcript"), "")

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

            video.title = latest_title
            video.description = latest_description
            video.views = _safe_int(data.get("views"), 0)
            video.likes = _safe_int(data.get("likes"), 0)
            video.comments = _safe_int(data.get("comments"), 0)
            video.posted = latest_posted
            video.video_length = latest_video_length
            video.thumbnail_url = latest_thumbnail_url
            video.transcript = latest_transcript
            video.channel_id = channel.id
            created = False
        else:
            video = Video(
                title=latest_title,
                description=latest_description,
                views=_safe_int(data.get("views"), 0),
                likes=_safe_int(data.get("likes"), 0),
                comments=_safe_int(data.get("comments"), 0),
                posted=latest_posted,
                video_length=latest_video_length,
                thumbnail_url=latest_thumbnail_url,
                transcript=latest_transcript,
                channel_id=channel.id,
                youtube_video_id=youtube_video_id,
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

        db.session.commit()
        return {"video_id": video.id, "created": created}
    except Exception as e:
        db.session.rollback()
        logger.exception("An error occurred: %s", str(e))
        raise

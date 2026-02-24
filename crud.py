import logging

from models import Channel, ChannelHistory, ChannelVideo, Video, db

logger = logging.getLogger(__name__)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def save_video(data):
    """Idempotently insert/update video data and manage channel subscriber history."""
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

        if video:
            video.title = data.get("title", "")
            video.description = data.get("description", "")
            video.views = _safe_int(data.get("views"), 0)
            video.likes = _safe_int(data.get("likes"), 0)
            video.comments = _safe_int(data.get("comments"), 0)
            video.posted = data.get("posted", "")
            video.video_length = data.get("video_length", "")
            video.transcript = data.get("transcript", "")
            video.channel_id = channel.id
            created = False
        else:
            video = Video(
                title=data.get("title", ""),
                description=data.get("description", ""),
                views=_safe_int(data.get("views"), 0),
                likes=_safe_int(data.get("likes"), 0),
                comments=_safe_int(data.get("comments"), 0),
                posted=data.get("posted", ""),
                video_length=data.get("video_length", ""),
                transcript=data.get("transcript", ""),
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

        db.session.commit()
        return {"video_id": video.id, "created": created}
    except Exception as e:
        db.session.rollback()
        logger.exception("An error occurred: %s", str(e))
        raise

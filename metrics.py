import os
from collections import Counter
from datetime import UTC, datetime
from statistics import median

from sqlalchemy import func

from models import (
    Channel,
    ChannelDerivedSummary,
    ChannelSnapshot,
    Video,
    VideoDerivedMetric,
    VideoLabel,
    VideoSnapshot,
    db,
)

DERIVED_METRICS_ALGORITHM_VERSION = os.environ.get(
    "DERIVED_METRICS_ALGORITHM_VERSION", "derived-metrics-v1"
)
BREAKOUT_THRESHOLD = float(os.environ.get("DERIVED_BREAKOUT_THRESHOLD", "5"))
OUTLIER_THRESHOLD = float(os.environ.get("DERIVED_OUTLIER_THRESHOLD", "2"))
UNDERPERFORMER_THRESHOLD = float(
    os.environ.get("DERIVED_UNDERPERFORMER_THRESHOLD", "0.5")
)
RECENT_VIDEO_LIMIT = int(os.environ.get("DERIVED_RECENT_VIDEO_LIMIT", "20"))


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def compute_derived_metrics():
    computed_at = utc_now()
    VideoDerivedMetric.query.filter_by(
        algorithm_version=DERIVED_METRICS_ALGORITHM_VERSION
    ).delete(synchronize_session=False)
    ChannelDerivedSummary.query.filter_by(
        algorithm_version=DERIVED_METRICS_ALGORITHM_VERSION
    ).delete(synchronize_session=False)
    db.session.flush()
    db.session.expire_all()

    video_count = 0

    for video in Video.query.order_by(Video.id.asc()).all():
        snapshot = latest_video_snapshot(video.id)
        if not snapshot:
            continue

        metric = compute_video_metric(video, snapshot, computed_at=computed_at)
        db.session.add(metric)
        video_count += 1

    channel_count = 0
    for channel in Channel.query.order_by(Channel.id.asc()).all():
        summary = compute_channel_summary(channel, computed_at=computed_at)
        if summary:
            db.session.add(summary)
            channel_count += 1

    db.session.commit()
    return {"videos_computed": video_count, "channels_computed": channel_count}


def compute_video_metric(video, snapshot, *, computed_at=None):
    computed_at = computed_at or utc_now()
    age_days = compute_age_days(video, snapshot.snapshot_at)
    view_count = safe_number(snapshot.view_count)
    subscriber_count = safe_number(snapshot.subscriber_count_at_snapshot)
    recent_median_views = channel_recent_median_views(video, exclude_video_id=video.id)
    relative_performance = safe_divide(view_count, recent_median_views)
    like_rate = percentage_rate(snapshot.like_count, view_count)
    comment_rate = percentage_rate(snapshot.comment_count, view_count)
    engagement_rate = percentage_rate(
        safe_number(snapshot.like_count) + safe_number(snapshot.comment_count),
        view_count,
    )
    performance_tier = classify_performance(relative_performance)

    return VideoDerivedMetric(
        video_id=video.id,
        snapshot_at=snapshot.snapshot_at,
        age_days=age_days,
        views_per_day=safe_divide(view_count, max(age_days, 1.0)),
        views_per_subscriber=safe_divide(view_count, subscriber_count),
        channel_recent_median_views=recent_median_views,
        relative_performance=relative_performance,
        duration_bucket=duration_bucket(video.duration_seconds),
        performance_tier=performance_tier,
        outlier_flag=performance_tier in {"breakout", "outlier"},
        like_rate=like_rate,
        comment_rate=comment_rate,
        engagement_rate=engagement_rate,
        computed_at=computed_at,
        algorithm_version=DERIVED_METRICS_ALGORITHM_VERSION,
    )


def compute_channel_summary(channel, *, computed_at=None):
    computed_at = computed_at or utc_now()
    videos = (
        Video.query.filter_by(channel_id=channel.id)
        .order_by(Video.published_at.desc().nullslast(), Video.id.desc())
        .limit(RECENT_VIDEO_LIMIT)
        .all()
    )
    if not videos:
        return None

    snapshots = [latest_video_snapshot(video.id) for video in videos]
    snapshots = [snapshot for snapshot in snapshots if snapshot]
    if not snapshots:
        return None

    labels = [video.labels[0] for video in videos if video.labels]
    view_counts = [safe_number(snapshot.view_count) for snapshot in snapshots]
    median_recent_views = median(view_counts) if view_counts else None
    subscriber_count = latest_channel_subscriber_count(channel)
    durations = [video.duration_seconds for video in videos if video.duration_seconds]
    published_dates = [video.published_at for video in videos if video.published_at]
    latest_snapshot_at = max(snapshot.snapshot_at for snapshot in snapshots)

    return ChannelDerivedSummary(
        channel_id=channel.id,
        snapshot_at=latest_snapshot_at,
        median_recent_views=median_recent_views,
        median_views_per_subscriber=safe_divide(median_recent_views, subscriber_count),
        upload_cadence_days=upload_cadence_days(published_dates),
        average_duration_seconds=(
            sum(durations) / len(durations) if durations else None
        ),
        top_outlier_topics=top_outlier_topics(channel.id),
        format_distribution=dict(
            Counter(label.format for label in labels if label.format)
        ),
        packaging_pattern_distribution=dict(
            Counter(
                label.packaging_pattern for label in labels if label.packaging_pattern
            )
        ),
        visible_monetization_signals=[
            label.monetization_signals for label in labels if label.monetization_signals
        ],
        computed_at=computed_at,
        algorithm_version=DERIVED_METRICS_ALGORITHM_VERSION,
    )


def latest_video_snapshot(video_id):
    return (
        VideoSnapshot.query.filter_by(video_id=video_id)
        .order_by(VideoSnapshot.snapshot_at.desc(), VideoSnapshot.id.desc())
        .first()
    )


def latest_channel_subscriber_count(channel):
    snapshot = (
        ChannelSnapshot.query.filter_by(channel_id=channel.id)
        .order_by(ChannelSnapshot.snapshot_at.desc(), ChannelSnapshot.id.desc())
        .first()
    )
    if snapshot:
        return safe_number(snapshot.subscriber_count)
    return safe_number(channel.subscriber_count or channel.subscribers)


def channel_recent_median_views(video, exclude_video_id=None):
    if not video.channel_id:
        return None

    query = Video.query.filter_by(channel_id=video.channel_id).order_by(
        Video.published_at.desc().nullslast(), Video.id.desc()
    )
    if exclude_video_id:
        query = query.filter(Video.id != exclude_video_id)

    view_counts = []
    for candidate in query.limit(RECENT_VIDEO_LIMIT).all():
        snapshot = latest_video_snapshot(candidate.id)
        if snapshot:
            view_counts.append(safe_number(snapshot.view_count))

    if not view_counts:
        own_snapshot = latest_video_snapshot(video.id)
        return safe_number(own_snapshot.view_count) if own_snapshot else None
    return median(view_counts)


def top_outlier_topics(channel_id):
    rows = (
        db.session.query(Video.title, VideoLabel.topic_type, VideoLabel.niche)
        .join(VideoDerivedMetric, VideoDerivedMetric.video_id == Video.id)
        .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .filter(Video.channel_id == channel_id)
        .filter(VideoDerivedMetric.outlier_flag.is_(True))
        .order_by(VideoDerivedMetric.relative_performance.desc().nullslast())
        .limit(5)
        .all()
    )
    return [
        {
            "title": title,
            "topic_type": topic_type,
            "niche": niche,
        }
        for title, topic_type, niche in rows
    ]


def upload_cadence_days(published_dates):
    dates = sorted(published_dates)
    if len(dates) < 2:
        return None
    gaps = [
        (dates[index] - dates[index - 1]).total_seconds() / 86400
        for index in range(1, len(dates))
    ]
    return median(gaps)


def compute_age_days(video, snapshot_at):
    baseline = video.published_at or video.created_at or snapshot_at
    return max((snapshot_at - baseline).total_seconds() / 86400, 0.0)


def duration_bucket(duration_seconds):
    if duration_seconds is None:
        return "unknown"
    if duration_seconds < 240:
        return "<4m"
    if duration_seconds < 480:
        return "4-8m"
    if duration_seconds < 900:
        return "8-15m"
    if duration_seconds < 1800:
        return "15-30m"
    return "30m+"


def classify_performance(relative_performance):
    if relative_performance is None:
        return "unknown"
    if relative_performance >= BREAKOUT_THRESHOLD:
        return "breakout"
    if relative_performance >= OUTLIER_THRESHOLD:
        return "outlier"
    if relative_performance < UNDERPERFORMER_THRESHOLD:
        return "underperformer"
    return "normal"


def percentage_rate(numerator, denominator):
    return round(safe_divide(numerator, denominator, default=0.0) * 100, 2)


def safe_divide(numerator, denominator, default=None):
    numerator = safe_number(numerator)
    denominator = safe_number(denominator)
    if denominator == 0:
        return default
    return numerator / denominator


def safe_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def market_analysis_summary(limit=25):
    top_outliers = (
        db.session.query(VideoDerivedMetric, Video, Channel, VideoLabel)
        .join(Video, Video.id == VideoDerivedMetric.video_id)
        .outerjoin(Channel, Channel.id == Video.channel_id)
        .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .order_by(VideoDerivedMetric.relative_performance.desc().nullslast())
        .limit(limit)
        .all()
    )
    strong_channels = (
        db.session.query(ChannelDerivedSummary, Channel)
        .join(Channel, Channel.id == ChannelDerivedSummary.channel_id)
        .order_by(
            ChannelDerivedSummary.median_views_per_subscriber.desc().nullslast(),
            ChannelDerivedSummary.median_recent_views.desc().nullslast(),
        )
        .limit(limit)
        .all()
    )
    repeated_topic_rows = (
        db.session.query(
            VideoLabel.niche,
            VideoLabel.topic_type,
            func.avg(VideoDerivedMetric.relative_performance),
            func.count(VideoDerivedMetric.id),
        )
        .join(VideoDerivedMetric, VideoDerivedMetric.video_id == VideoLabel.video_id)
        .filter(VideoDerivedMetric.outlier_flag.is_(True))
        .filter(VideoLabel.niche.isnot(None))
        .filter(VideoLabel.topic_type.isnot(None))
        .group_by(VideoLabel.niche, VideoLabel.topic_type)
        .order_by(
            func.count(VideoDerivedMetric.id).desc(),
            func.avg(VideoDerivedMetric.relative_performance).desc(),
        )
        .limit(limit)
        .all()
    )
    thesis_rows = (
        db.session.query(
            VideoLabel.niche,
            VideoLabel.format,
            VideoLabel.packaging_pattern,
            VideoLabel.topic_type,
            func.avg(VideoDerivedMetric.relative_performance),
            func.avg(VideoDerivedMetric.views_per_subscriber),
            func.count(VideoDerivedMetric.id),
        )
        .join(VideoDerivedMetric, VideoDerivedMetric.video_id == VideoLabel.video_id)
        .filter(VideoDerivedMetric.outlier_flag.is_(True))
        .filter(VideoLabel.niche.isnot(None))
        .filter(VideoLabel.format.isnot(None))
        .group_by(
            VideoLabel.niche,
            VideoLabel.format,
            VideoLabel.packaging_pattern,
            VideoLabel.topic_type,
        )
        .order_by(
            func.count(VideoDerivedMetric.id).desc(),
            func.avg(VideoDerivedMetric.relative_performance).desc(),
            func.avg(VideoDerivedMetric.views_per_subscriber).desc(),
        )
        .limit(limit)
        .all()
    )
    format_rows = (
        db.session.query(
            VideoLabel.format,
            func.avg(VideoDerivedMetric.relative_performance),
            func.count(VideoDerivedMetric.id),
        )
        .join(VideoDerivedMetric, VideoDerivedMetric.video_id == VideoLabel.video_id)
        .filter(VideoLabel.format.isnot(None))
        .group_by(VideoLabel.format)
        .order_by(func.avg(VideoDerivedMetric.relative_performance).desc())
        .all()
    )
    packaging_rows = (
        db.session.query(
            VideoLabel.packaging_pattern,
            func.avg(VideoDerivedMetric.relative_performance),
            func.count(VideoDerivedMetric.id),
        )
        .join(VideoDerivedMetric, VideoDerivedMetric.video_id == VideoLabel.video_id)
        .filter(VideoLabel.packaging_pattern.isnot(None))
        .group_by(VideoLabel.packaging_pattern)
        .order_by(func.avg(VideoDerivedMetric.relative_performance).desc())
        .all()
    )

    return {
        "top_outliers": top_outliers,
        "strong_channels": strong_channels,
        "repeated_topic_rows": repeated_topic_rows,
        "thesis_rows": thesis_rows,
        "format_rows": format_rows,
        "packaging_rows": packaging_rows,
        "algorithm_version": DERIVED_METRICS_ALGORITHM_VERSION,
        "thresholds": {
            "breakout": BREAKOUT_THRESHOLD,
            "outlier": OUTLIER_THRESHOLD,
            "underperformer": UNDERPERFORMER_THRESHOLD,
        },
    }

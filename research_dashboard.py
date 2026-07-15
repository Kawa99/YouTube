from datetime import UTC, datetime

from models import (
    Channel,
    CollectionRun,
    ContentThesis,
    Video,
    VideoDerivedMetric,
    VideoLabel,
    db,
)


def research_dashboard_summary():
    labeled_videos = VideoLabel.query.count()
    total_videos = Video.query.count()
    unlabeled_videos = (
        Video.query.outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .filter(VideoLabel.id.is_(None))
        .count()
    )
    recent_runs = (
        CollectionRun.query.order_by(CollectionRun.started_at.desc()).limit(8).all()
    )
    failed_runs = (
        CollectionRun.query.filter(CollectionRun.status.in_(("failed", "partial")))
        .order_by(CollectionRun.started_at.desc())
        .limit(8)
        .all()
    )
    quota_total = (
        db.session.query(
            db.func.coalesce(db.func.sum(CollectionRun.quota_estimate), 0)
        ).scalar()
        or 0
    )
    top_outliers = (
        db.session.query(VideoDerivedMetric, Video, Channel, VideoLabel)
        .join(Video, Video.id == VideoDerivedMetric.video_id)
        .outerjoin(Channel, Channel.id == Video.channel_id)
        .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .filter(VideoDerivedMetric.outlier_flag.is_(True))
        .order_by(VideoDerivedMetric.relative_performance.desc())
        .limit(8)
        .all()
    )
    candidate_theses = (
        ContentThesis.query.filter(ContentThesis.status.in_(("research", "pilot")))
        .order_by(ContentThesis.updated_at.desc())
        .limit(8)
        .all()
    )

    return {
        "generated_at": datetime.now(UTC).replace(tzinfo=None),
        "counts": {
            "channels": Channel.query.count(),
            "videos": total_videos,
            "labeled_videos": labeled_videos,
            "unlabeled_videos": unlabeled_videos,
            "label_coverage": _percentage(labeled_videos, total_videos),
            "collection_runs": CollectionRun.query.count(),
            "failed_runs": CollectionRun.query.filter(
                CollectionRun.status.in_(("failed", "partial"))
            ).count(),
            "candidate_theses": ContentThesis.query.filter(
                ContentThesis.status.in_(("research", "pilot"))
            ).count(),
            "quota_total": int(quota_total),
        },
        "recent_runs": recent_runs,
        "failed_runs": failed_runs,
        "top_outliers": top_outliers,
        "candidate_theses": candidate_theses,
    }


def _percentage(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 1)

from datetime import UTC, datetime

from sqlalchemy import func

from models import (
    Channel,
    PackagingExperiment,
    Video,
    VideoDerivedMetric,
    VideoLabel,
    VideoMetadataChange,
    VideoSnapshot,
    db,
)


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def packaging_lab_summary(limit=48, niche=None):
    comparison_query = (
        db.session.query(Video, Channel, VideoLabel, VideoDerivedMetric)
        .outerjoin(Channel, Channel.id == Video.channel_id)
        .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .outerjoin(VideoDerivedMetric, VideoDerivedMetric.video_id == Video.id)
    )
    if niche:
        comparison_query = comparison_query.filter(VideoLabel.niche == niche)

    comparison_rows = (
        comparison_query.order_by(
            VideoDerivedMetric.relative_performance.desc().nullslast(),
            Video.views.desc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    pattern_query = (
        db.session.query(
            VideoLabel.niche,
            VideoLabel.title_pattern,
            VideoLabel.thumbnail_pattern,
            func.avg(VideoDerivedMetric.relative_performance),
            func.count(Video.id),
        )
        .join(Video, Video.id == VideoLabel.video_id)
        .outerjoin(VideoDerivedMetric, VideoDerivedMetric.video_id == Video.id)
        .filter(VideoLabel.niche.isnot(None))
        .filter(VideoLabel.title_pattern.isnot(None))
        .filter(VideoLabel.thumbnail_pattern.isnot(None))
        .group_by(
            VideoLabel.niche,
            VideoLabel.title_pattern,
            VideoLabel.thumbnail_pattern,
        )
    )
    if niche:
        pattern_query = pattern_query.filter(VideoLabel.niche == niche)

    pattern_rows = (
        pattern_query.order_by(
            func.avg(VideoDerivedMetric.relative_performance).desc().nullslast(),
            func.count(Video.id).desc(),
        )
        .limit(25)
        .all()
    )

    return {
        "comparison_rows": comparison_rows,
        "pattern_rows": pattern_rows,
        "metadata_change_rows": metadata_change_rows(limit=25, niche=niche),
        "experiments": PackagingExperiment.query.order_by(
            PackagingExperiment.updated_at.desc(), PackagingExperiment.id.desc()
        )
        .limit(25)
        .all(),
        "selected_niche": niche or "",
    }


def metadata_change_rows(limit=25, niche=None):
    query = (
        db.session.query(VideoMetadataChange, Video, Channel, VideoLabel)
        .join(Video, Video.id == VideoMetadataChange.video_id)
        .outerjoin(Channel, Channel.id == Video.channel_id)
        .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .filter(VideoMetadataChange.field_name.in_(("title", "thumbnail_url")))
    )
    if niche:
        query = query.filter(VideoLabel.niche == niche)

    rows = []
    for change, video, channel, label in (
        query.order_by(VideoMetadataChange.changed_at.desc()).limit(limit).all()
    ):
        before_snapshot = (
            VideoSnapshot.query.filter(VideoSnapshot.video_id == video.id)
            .filter(VideoSnapshot.snapshot_at <= change.changed_at)
            .order_by(VideoSnapshot.snapshot_at.desc(), VideoSnapshot.id.desc())
            .first()
        )
        after_snapshot = (
            VideoSnapshot.query.filter(VideoSnapshot.video_id == video.id)
            .filter(VideoSnapshot.snapshot_at > change.changed_at)
            .order_by(VideoSnapshot.snapshot_at.asc(), VideoSnapshot.id.asc())
            .first()
        )
        rows.append(
            {
                "change": change,
                "video": video,
                "channel": channel,
                "label": label,
                "before_views": before_snapshot.view_count if before_snapshot else None,
                "after_views": after_snapshot.view_count if after_snapshot else None,
                "view_delta": (
                    after_snapshot.view_count - before_snapshot.view_count
                    if before_snapshot and after_snapshot
                    else None
                ),
            }
        )
    return rows


def save_packaging_experiment(payload):
    working_title = (payload.get("working_title") or "").strip()
    if not working_title:
        raise ValueError("Working title is required.")

    experiment = PackagingExperiment(
        working_title=working_title,
        niche=_blank_to_none(payload.get("niche")),
        format=_blank_to_none(payload.get("format")),
        title_candidates=_lines(payload.get("title_candidates")),
        thumbnail_concepts=_lines(payload.get("thumbnail_concepts")),
        experiment_log_url=_blank_to_none(payload.get("experiment_log_url")),
        final_title=_blank_to_none(payload.get("final_title")),
        final_thumbnail_concept=_blank_to_none(payload.get("final_thumbnail_concept")),
        final_choice_reason=_blank_to_none(payload.get("final_choice_reason")),
        status=_blank_to_none(payload.get("status")) or "draft",
    )
    db.session.add(experiment)
    db.session.commit()
    return experiment


def _lines(value):
    if not value:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None

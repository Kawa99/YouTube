from datetime import UTC, datetime

from label_vocabularies import (
    CONTROLLED_VIDEO_LABEL_FIELDS,
    LABEL_VOCABULARIES,
    VIDEO_LABEL_FIELDS,
    VIDEO_LABEL_SCORE_FIELDS,
)
from models import Video, VideoLabel, VideoLabelAudit, db


class LabelValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def label_snapshot(label):
    if not label:
        return {}
    return {
        "niche": label.niche,
        "format": label.format,
        "faceless_status": label.faceless_status,
        "ai_use_visible": label.ai_use_visible,
        "visual_style": label.visual_style,
        "packaging_pattern": label.packaging_pattern,
        "title_pattern": label.title_pattern,
        "thumbnail_pattern": label.thumbnail_pattern,
        "viewer_promise": label.viewer_promise,
        "curiosity_type": label.curiosity_type,
        "clarity_score": label.clarity_score,
        "specificity_score": label.specificity_score,
        "honesty_score": label.honesty_score,
        "visual_readability_score": label.visual_readability_score,
        "differentiation_score": label.differentiation_score,
        "topic_type": label.topic_type,
        "production_complexity": label.production_complexity,
        "policy_risk": label.policy_risk,
        "monetization_signals": label.monetization_signals,
        "review_status": label.review_status,
        "label_confidence": label.label_confidence,
        "notes": label.notes,
    }


def normalize_video_label_payload(payload, *, partial=False):
    normalized = {}
    for field in VIDEO_LABEL_FIELDS:
        if field not in payload:
            continue
        value = payload.get(field)
        if value is None:
            value = ""
        if isinstance(value, str):
            value = value.strip()

        if field == "label_confidence":
            normalized[field] = _normalize_confidence(value)
        elif field in VIDEO_LABEL_SCORE_FIELDS:
            normalized[field] = _normalize_score(field, value)
        elif field in CONTROLLED_VIDEO_LABEL_FIELDS:
            normalized[field] = _normalize_controlled_value(field, value, partial)
        else:
            normalized[field] = value or None

    if not partial:
        normalized.setdefault("review_status", "reviewed")

    return normalized


def save_video_label(video_id, payload, *, reviewer, action="reviewed", partial=False):
    video = db.session.get(Video, video_id)
    if not video:
        raise LabelValidationError("Video not found.")

    normalized = normalize_video_label_payload(payload, partial=partial)
    if action in {"skipped", "needs_second_review"}:
        normalized["review_status"] = action
    elif action == "reviewed":
        normalized.setdefault("review_status", "reviewed")

    label = VideoLabel.query.filter_by(video_id=video.id).first()
    previous_values = label_snapshot(label)
    if not label:
        label = VideoLabel(video_id=video.id)
        db.session.add(label)
        db.session.flush()

    for field, value in normalized.items():
        setattr(label, field, value)

    label.reviewer = reviewer or "unknown"
    label.reviewed_at = utc_now()

    new_values = label_snapshot(label)
    db.session.add(
        VideoLabelAudit(
            video_label_id=label.id,
            video_id=video.id,
            action=action,
            reviewer=label.reviewer,
            previous_values=previous_values,
            new_values=new_values,
            label_confidence=label.label_confidence,
        )
    )
    db.session.commit()
    return label


def bulk_apply_video_label(video_ids, field, value, *, reviewer):
    if field not in VIDEO_LABEL_FIELDS:
        raise LabelValidationError("Unsupported label field.")

    normalized_payload = normalize_video_label_payload({field: value}, partial=True)
    updated = 0
    for video_id in video_ids:
        if db.session.get(Video, video_id):
            save_video_label(
                video_id,
                normalized_payload,
                reviewer=reviewer,
                action="bulk_apply",
                partial=True,
            )
            updated += 1
    return updated


def next_unlabeled_video_id(current_video_id=None):
    query = (
        Video.query.outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
        .filter((VideoLabel.id.is_(None)) | (VideoLabel.review_status == "pending"))
        .order_by(Video.id.asc())
    )
    if current_video_id:
        later_video = query.filter(Video.id > current_video_id).first()
        if later_video:
            return later_video.id
    video = query.first()
    return video.id if video else None


def _normalize_controlled_value(field, value, partial):
    if value == "" and partial:
        return None
    allowed_values = LABEL_VOCABULARIES[field]
    if value not in allowed_values:
        raise LabelValidationError(
            f"{field} must be one of: {', '.join(allowed_values)}"
        )
    return value


def _normalize_confidence(value):
    if value in ("", None):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise LabelValidationError("label_confidence must be a number.") from exc
    if confidence < 0 or confidence > 1:
        raise LabelValidationError("label_confidence must be between 0 and 1.")
    return confidence


def _normalize_score(field, value):
    if value in ("", None):
        return None
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise LabelValidationError(f"{field} must be an integer.") from exc
    if score < 1 or score > 5:
        raise LabelValidationError(f"{field} must be between 1 and 5.")
    return score

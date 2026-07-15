import os
from datetime import UTC, date, datetime

from models import (
    Channel,
    Experiment,
    ExperimentCheckpoint,
    OwnedAnalyticsCredential,
    OwnedVideoAnalytics,
    RetentionDiagnostic,
    Video,
    db,
)

OWNED_ANALYTICS_SCOPES = (
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
)
CHECKPOINTS = ("24h", "7d", "30d")
EXPERIMENT_DECISIONS = ("pending", "continue", "pivot", "stop", "scale")
RETENTION_PATTERNS = (
    "early_cliff",
    "slow_bleed",
    "mid_video_drop",
    "spike_replay",
    "high_ctr_low_retention",
    "low_ctr_high_retention",
    "low_impressions_good_response",
    "good_search_weak_browse",
    "unknown",
)


class OwnedAnalyticsValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def owned_dashboard(selected_video_id=None):
    videos = Video.query.order_by(Video.id.desc()).limit(100).all()
    selected_video = (
        db.session.get(Video, selected_video_id) if selected_video_id else None
    )
    if selected_video is None and videos:
        selected_video = videos[0]

    return {
        "videos": videos,
        "channels": Channel.query.order_by(Channel.channel_username.asc()).all(),
        "selected_video": selected_video,
        "credentials": OwnedAnalyticsCredential.query.order_by(
            OwnedAnalyticsCredential.created_at.desc()
        ).all(),
        "analytics_rows": (
            OwnedVideoAnalytics.query.filter_by(video_id=selected_video.id)
            .order_by(OwnedVideoAnalytics.date.desc(), OwnedVideoAnalytics.id.desc())
            .limit(60)
            .all()
            if selected_video
            else []
        ),
        "retention_rows": (
            RetentionDiagnostic.query.filter_by(video_id=selected_video.id)
            .order_by(RetentionDiagnostic.report_date.desc())
            .limit(20)
            .all()
            if selected_video
            else []
        ),
        "experiments": Experiment.query.order_by(Experiment.created_at.desc())
        .limit(50)
        .all(),
        "scopes": OWNED_ANALYTICS_SCOPES,
        "oauth_configured": oauth_configured(),
        "checkpoints": CHECKPOINTS,
        "experiment_decisions": EXPERIMENT_DECISIONS,
        "retention_patterns": RETENTION_PATTERNS,
    }


def oauth_configured():
    return bool(
        os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        and os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    )


def save_credential(payload):
    channel_id = _optional_int(payload.get("channel_id"))
    if channel_id is not None and not db.session.get(Channel, channel_id):
        raise OwnedAnalyticsValidationError("Channel not found.")

    credential = OwnedAnalyticsCredential(
        channel_id=channel_id,
        google_account_email=_blank_to_none(payload.get("google_account_email")),
        scopes=list(OWNED_ANALYTICS_SCOPES),
        token_secret_ref=_blank_to_none(payload.get("token_secret_ref")),
        status="configured",
        notes=_blank_to_none(payload.get("notes")),
    )
    if not credential.token_secret_ref:
        raise OwnedAnalyticsValidationError(
            "Store tokens in a secret manager and provide token_secret_ref."
        )
    db.session.add(credential)
    db.session.commit()
    return credential


def revoke_credential(credential_id):
    credential = db.session.get(OwnedAnalyticsCredential, credential_id)
    if not credential:
        raise OwnedAnalyticsValidationError("Credential not found.")
    credential.status = "revoked"
    credential.revoked_at = utc_now()
    db.session.commit()
    return credential


def save_owned_analytics(payload):
    video = _video(payload.get("video_id"))
    row = OwnedVideoAnalytics(
        video_id=video.id,
        date=_date(payload.get("date"), "date"),
        views=_optional_int(payload.get("views")),
        impressions=_optional_int(payload.get("impressions")),
        impression_ctr=_optional_float(payload.get("impression_ctr")),
        average_view_duration_seconds=_optional_float(
            payload.get("average_view_duration_seconds")
        ),
        average_view_percentage=_optional_float(payload.get("average_view_percentage")),
        watch_time_minutes=_optional_float(payload.get("watch_time_minutes")),
        subscribers_gained=_optional_int(payload.get("subscribers_gained")),
        estimated_revenue=_optional_float(payload.get("estimated_revenue")),
        traffic_source_type=_blank_to_none(payload.get("traffic_source_type")),
        source=_blank_to_none(payload.get("source")) or "manual",
    )
    db.session.add(row)
    db.session.commit()
    return row


def save_retention_diagnostic(payload):
    video = _video(payload.get("video_id"))
    row = RetentionDiagnostic(
        video_id=video.id,
        report_date=_date(payload.get("report_date"), "report_date"),
        ctr=_optional_float(payload.get("ctr")),
        average_view_duration_seconds=_optional_float(
            payload.get("average_view_duration_seconds")
        ),
        average_view_percentage=_optional_float(payload.get("average_view_percentage")),
        impressions=_optional_int(payload.get("impressions")),
        dominant_traffic_source=_blank_to_none(payload.get("dominant_traffic_source")),
        retention_pattern=_choice(
            payload.get("retention_pattern") or "unknown",
            RETENTION_PATTERNS,
            "retention_pattern",
        ),
        likely_cause=_blank_to_none(payload.get("likely_cause")),
        evidence=_blank_to_none(payload.get("evidence")),
        next_change=_blank_to_none(payload.get("next_change")),
        notes=_blank_to_none(payload.get("notes")),
    )
    db.session.add(row)
    db.session.commit()
    return row


def create_experiment(payload):
    video_id = _optional_int(payload.get("video_id"))
    if video_id is not None and not db.session.get(Video, video_id):
        raise OwnedAnalyticsValidationError("Video not found.")

    experiment = Experiment(
        video_id=video_id,
        hypothesis=_required(payload, "hypothesis"),
        variable_tested=_required(payload, "variable_tested"),
        title=_blank_to_none(payload.get("title")),
        thumbnail_variant=_blank_to_none(payload.get("thumbnail_variant")),
        publish_date=_optional_date(payload.get("publish_date")),
        success_metric=_blank_to_none(payload.get("success_metric")),
        production_hours=_optional_float(payload.get("production_hours")),
        production_cost=_optional_float(payload.get("production_cost")),
        decision=_choice(
            payload.get("decision") or "pending",
            EXPERIMENT_DECISIONS,
            "decision",
        ),
        notes=_blank_to_none(payload.get("notes")),
    )
    db.session.add(experiment)
    db.session.commit()
    return experiment


def save_experiment_checkpoint(experiment_id, payload):
    experiment = db.session.get(Experiment, experiment_id)
    if not experiment:
        raise OwnedAnalyticsValidationError("Experiment not found.")
    checkpoint = ExperimentCheckpoint(
        experiment_id=experiment.id,
        checkpoint=_choice(payload.get("checkpoint"), CHECKPOINTS, "checkpoint"),
        views=_optional_int(payload.get("views")),
        impressions=_optional_int(payload.get("impressions")),
        impression_ctr=_optional_float(payload.get("impression_ctr")),
        average_view_duration_seconds=_optional_float(
            payload.get("average_view_duration_seconds")
        ),
        average_view_percentage=_optional_float(payload.get("average_view_percentage")),
        watch_time_minutes=_optional_float(payload.get("watch_time_minutes")),
        subscribers_gained=_optional_int(payload.get("subscribers_gained")),
        main_traffic_source=_blank_to_none(payload.get("main_traffic_source")),
        notes=_blank_to_none(payload.get("notes")),
    )
    db.session.add(checkpoint)
    db.session.commit()
    return checkpoint


def _video(video_id):
    video = db.session.get(Video, _required_int(video_id, "video_id"))
    if not video:
        raise OwnedAnalyticsValidationError("Video not found.")
    return video


def _required(payload, field):
    value = _blank_to_none(payload.get(field))
    if not value:
        raise OwnedAnalyticsValidationError(f"{field} is required.")
    return value


def _required_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise OwnedAnalyticsValidationError(f"{field} must be an integer.") from exc


def _optional_int(value):
    if value in (None, ""):
        return None
    return _required_int(value, "integer field")


def _optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise OwnedAnalyticsValidationError("Metric values must be numbers.") from exc


def _optional_date(value):
    if value in (None, ""):
        return None
    return _date(value, "date")


def _date(value, field):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise OwnedAnalyticsValidationError(f"{field} must be YYYY-MM-DD.") from exc


def _choice(value, allowed, field):
    value = _blank_to_none(value)
    if value not in allowed:
        raise OwnedAnalyticsValidationError(
            f"{field} must be one of: {', '.join(allowed)}"
        )
    return value


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None

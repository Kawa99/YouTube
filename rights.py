from datetime import UTC, datetime

from models import Asset, Video, VideoAsset, VideoDisclosure, VideoRightsChecklist, db

ASSET_TYPES = (
    "stock_video",
    "stock_image",
    "archival_video",
    "public_domain_image",
    "music",
    "sound_effect",
    "font",
    "ai_generated_image",
    "ai_generated_video",
    "tts_voice",
    "voice_clone",
    "original_graphic",
    "screenshot",
    "map_diagram",
)
RIGHTS_STATES = ("yes", "no", "unclear")
RIGHTS_DECISIONS = ("use", "replace", "seek_permission", "remove")
SYNTHETIC_STATUSES = ("none", "ai_generated", "altered", "synthetic_voice", "unknown")
HIGH_RISK_TYPES = {
    "archival_video",
    "music",
    "voice_clone",
    "screenshot",
}


class RightsValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def rights_dashboard(selected_video_id=None):
    videos = Video.query.order_by(Video.id.desc()).limit(100).all()
    selected_video = (
        db.session.get(Video, selected_video_id) if selected_video_id else None
    )
    if selected_video is None and videos:
        selected_video = videos[0]

    return {
        "videos": videos,
        "selected_video": selected_video,
        "assets": Asset.query.order_by(Asset.updated_at.desc(), Asset.id.desc())
        .limit(100)
        .all(),
        "video_assets": _video_assets(selected_video.id) if selected_video else [],
        "checklists": (
            VideoRightsChecklist.query.filter_by(video_id=selected_video.id)
            .order_by(VideoRightsChecklist.reviewed_at.desc())
            .all()
            if selected_video
            else []
        ),
        "disclosures": (
            VideoDisclosure.query.filter_by(video_id=selected_video.id)
            .order_by(VideoDisclosure.created_at.desc())
            .all()
            if selected_video
            else []
        ),
        "high_risk_assets": Asset.query.filter_by(high_risk_flag=True)
        .order_by(Asset.updated_at.desc())
        .limit(25)
        .all(),
        "asset_types": ASSET_TYPES,
        "rights_states": RIGHTS_STATES,
        "rights_decisions": RIGHTS_DECISIONS,
        "synthetic_statuses": SYNTHETIC_STATUSES,
    }


def create_asset(payload):
    asset_id = _required(payload, "asset_id").upper()
    if Asset.query.filter_by(asset_id=asset_id).first():
        raise RightsValidationError("Asset ID already exists.")
    asset_type = _choice(payload.get("asset_type"), ASSET_TYPES, "asset_type")
    high_risk_flag = (
        _bool(payload.get("high_risk_flag")) or asset_type in HIGH_RISK_TYPES
    )
    asset = Asset(
        asset_id=asset_id,
        asset_type=asset_type,
        source_url_path=_required(payload, "source_url_path"),
        creator_licensor=_blank_to_none(payload.get("creator_licensor")),
        license_terms=_blank_to_none(payload.get("license_terms")),
        monetized_youtube_allowed=_choice(
            payload.get("monetized_youtube_allowed") or "unclear",
            RIGHTS_STATES,
            "monetized_youtube_allowed",
        ),
        attribution_required=_bool(payload.get("attribution_required")),
        proof_saved=_bool(payload.get("proof_saved")),
        high_risk_flag=high_risk_flag,
        high_risk_reason=_blank_to_none(payload.get("high_risk_reason")),
        notes=_blank_to_none(payload.get("notes")),
    )
    db.session.add(asset)
    db.session.commit()
    return asset


def link_asset_to_video(payload):
    video = db.session.get(Video, _required_int(payload.get("video_id"), "video_id"))
    if not video:
        raise RightsValidationError("Video not found.")
    asset = db.session.get(Asset, _required_int(payload.get("asset_id"), "asset_id"))
    if not asset:
        raise RightsValidationError("Asset not found.")

    link = VideoAsset(
        video_id=video.id,
        asset_id=asset.id,
        intended_use=_blank_to_none(payload.get("intended_use")),
        attribution_text=_blank_to_none(payload.get("attribution_text")),
        rights_decision=_choice(
            payload.get("rights_decision") or "use",
            RIGHTS_DECISIONS,
            "rights_decision",
        ),
    )
    db.session.add(link)
    db.session.commit()
    return link


def save_rights_checklist(video_id, payload):
    video = db.session.get(Video, video_id)
    if not video:
        raise RightsValidationError("Video not found.")
    checklist = VideoRightsChecklist(
        video_id=video.id,
        every_asset_has_row=_bool(payload.get("every_asset_has_row")),
        unclear_assets_blocked=_bool(payload.get("unclear_assets_blocked")),
        attribution_captured=_bool(payload.get("attribution_captured")),
        synthetic_altered_status=_choice(
            payload.get("synthetic_altered_status") or "none",
            SYNTHETIC_STATUSES,
            "synthetic_altered_status",
        ),
        no_terms_prohibit_monetization=_bool(
            payload.get("no_terms_prohibit_monetization")
        ),
        ready_for_upload=_bool(payload.get("ready_for_upload")),
        reviewer=_blank_to_none(payload.get("reviewer")),
        notes=_blank_to_none(payload.get("notes")),
    )
    if checklist.ready_for_upload:
        _validate_ready_for_upload(video, checklist)
    db.session.add(checklist)
    db.session.commit()
    return checklist


def save_video_disclosure(video_id, payload):
    video = db.session.get(Video, video_id)
    if not video:
        raise RightsValidationError("Video not found.")
    disclosure = VideoDisclosure(
        video_id=video.id,
        sponsor_disclosure=_blank_to_none(payload.get("sponsor_disclosure")),
        affiliate_disclosure=_blank_to_none(payload.get("affiliate_disclosure")),
        altered_synthetic_disclosure=_blank_to_none(
            payload.get("altered_synthetic_disclosure")
        ),
        music_license_attribution=_blank_to_none(
            payload.get("music_license_attribution")
        ),
        disclosure_notes=_blank_to_none(payload.get("disclosure_notes")),
    )
    db.session.add(disclosure)
    db.session.commit()
    return disclosure


def _validate_ready_for_upload(video, checklist):
    linked_assets = _video_assets(video.id)
    if not linked_assets:
        raise RightsValidationError("Ready videos must have at least one asset row.")
    if not checklist.every_asset_has_row:
        raise RightsValidationError("Every asset must have a ledger row.")
    if not checklist.unclear_assets_blocked:
        raise RightsValidationError("Unclear assets must be blocked before upload.")
    if not checklist.attribution_captured:
        raise RightsValidationError("Attribution must be captured before upload.")
    if not checklist.no_terms_prohibit_monetization:
        raise RightsValidationError("Asset terms must allow monetized YouTube use.")

    blocked_assets = [
        link.asset.asset_id
        for link in linked_assets
        if link.rights_decision != "use"
        or link.asset.monetized_youtube_allowed != "yes"
        or not link.asset.proof_saved
    ]
    if blocked_assets:
        raise RightsValidationError(
            "Blocked or unproven assets prevent upload: " + ", ".join(blocked_assets)
        )


def _video_assets(video_id):
    return (
        VideoAsset.query.filter_by(video_id=video_id)
        .join(Asset, Asset.id == VideoAsset.asset_id)
        .order_by(Asset.high_risk_flag.desc(), VideoAsset.id.desc())
        .all()
    )


def _required(payload, field):
    value = _blank_to_none(payload.get(field))
    if not value:
        raise RightsValidationError(f"{field} is required.")
    return value


def _required_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RightsValidationError(f"{field} must be an integer.") from exc


def _choice(value, allowed, field):
    value = _blank_to_none(value)
    if value not in allowed:
        raise RightsValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return value


def _bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None

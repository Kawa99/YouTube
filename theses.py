from datetime import UTC, datetime

from models import (
    ContentThesis,
    RedTeamReview,
    ThesisEvidence,
    ThesisScore,
    ThesisTopic,
    db,
)

THESIS_STATUSES = ("idea", "research", "pilot", "reject", "launch")
TOPIC_STATUSES = ("backlog", "shortlisted", "scripted", "tested", "rejected")
EVIDENCE_TYPES = (
    "outlier_video",
    "competitor_channel",
    "comment_theme",
    "search_trend",
    "sponsor_density",
    "source_availability",
    "forum_question",
    "manual_note",
)
RED_TEAM_DECISIONS = ("proceed_to_pilot", "research_more", "revise_thesis", "reject")
DECISIONS_UNDER_REVIEW = ("launch", "pilot", "scale", "pivot")
NICHE_SCORE_FACTORS = (
    ("audience_demand", 5),
    ("rpm_potential", 5),
    ("policy_safety", 5),
    ("differentiation", 4),
    ("production_feasibility", 4),
    ("research_source_availability", 4),
    ("evergreen_value", 4),
    ("competition_intensity", 3),
    ("sponsorship_affiliate_fit", 3),
    ("thumbnail_title_viability", 3),
    ("operator_fit", 3),
    ("cost_control", 2),
)
MAX_NICHE_SCORE = sum(weight * 5 for _, weight in NICHE_SCORE_FACTORS)


class ThesisValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def thesis_dashboard(selected_id=None):
    theses = ContentThesis.query.order_by(
        ContentThesis.updated_at.desc(), ContentThesis.id.desc()
    ).all()
    selected = None
    if selected_id:
        selected = db.session.get(ContentThesis, selected_id)
    if selected is None and theses:
        selected = theses[0]

    return {
        "theses": theses,
        "selected": selected,
        "score_summary": score_summary(selected) if selected else None,
        "statuses": THESIS_STATUSES,
        "topic_statuses": TOPIC_STATUSES,
        "evidence_types": EVIDENCE_TYPES,
        "score_factors": NICHE_SCORE_FACTORS,
        "red_team_decisions": RED_TEAM_DECISIONS,
        "decisions_under_review": DECISIONS_UNDER_REVIEW,
    }


def create_content_thesis(payload):
    thesis_id = _required(payload, "thesis_id").upper()
    title = _required(payload, "title")
    status = _choice(payload.get("status") or "idea", THESIS_STATUSES, "status")
    if ContentThesis.query.filter_by(thesis_id=thesis_id).first():
        raise ThesisValidationError("Thesis ID already exists.")

    thesis = ContentThesis(
        thesis_id=thesis_id,
        title=title,
        target_viewer=_blank_to_none(payload.get("target_viewer")),
        viewer_promise=_blank_to_none(payload.get("viewer_promise")),
        format=_blank_to_none(payload.get("format")),
        topic_universe=_blank_to_none(payload.get("topic_universe")),
        production_edge=_blank_to_none(payload.get("production_edge")),
        packaging_edge=_blank_to_none(payload.get("packaging_edge")),
        monetization_path=_blank_to_none(payload.get("monetization_path")),
        policy_risk_argument=_blank_to_none(payload.get("policy_risk_argument")),
        status=status,
        notes=_blank_to_none(payload.get("notes")),
    )
    db.session.add(thesis)
    db.session.commit()
    return thesis


def update_thesis_status(thesis_id, status):
    thesis = _get_thesis(thesis_id)
    thesis.status = _choice(status, THESIS_STATUSES, "status")
    thesis.updated_at = utc_now()
    db.session.commit()
    return thesis


def add_thesis_evidence(thesis_id, payload):
    thesis = _get_thesis(thesis_id)
    evidence = ThesisEvidence(
        thesis_id=thesis.id,
        evidence_type=_choice(
            payload.get("evidence_type"), EVIDENCE_TYPES, "evidence_type"
        ),
        channel_id=_optional_int(payload.get("channel_id")),
        video_id=_optional_int(payload.get("video_id")),
        source_url=_blank_to_none(payload.get("source_url")),
        note=_blank_to_none(payload.get("note")),
        confidence=_optional_confidence(payload.get("confidence")),
    )
    db.session.add(evidence)
    _touch(thesis)
    db.session.commit()
    return evidence


def add_thesis_topic(thesis_id, payload):
    thesis = _get_thesis(thesis_id)
    topic = ThesisTopic(
        thesis_id=thesis.id,
        topic=_required(payload, "topic"),
        title_angle=_blank_to_none(payload.get("title_angle")),
        demand_evidence=_blank_to_none(payload.get("demand_evidence")),
        source_availability=_blank_to_none(payload.get("source_availability")),
        production_complexity=_blank_to_none(payload.get("production_complexity")),
        packaging_potential=_blank_to_none(payload.get("packaging_potential")),
        status=_choice(payload.get("status") or "backlog", TOPIC_STATUSES, "status"),
    )
    db.session.add(topic)
    _touch(thesis)
    db.session.commit()
    return topic


def add_thesis_score(thesis_id, payload):
    thesis = _get_thesis(thesis_id)
    factor = _choice(
        payload.get("factor"), [factor for factor, _ in NICHE_SCORE_FACTORS], "factor"
    )
    weight = dict(NICHE_SCORE_FACTORS)[factor]
    score = _score(payload.get("score"))
    score_row = ThesisScore(
        thesis_id=thesis.id,
        factor=factor,
        weight=weight,
        score=score,
        weighted_score=score * weight,
        evidence=_blank_to_none(payload.get("evidence")),
        confidence=_optional_confidence(payload.get("confidence")),
    )
    db.session.add(score_row)
    _touch(thesis)
    db.session.commit()
    return score_row


def add_red_team_review(thesis_id, payload):
    thesis = _get_thesis(thesis_id)
    review = RedTeamReview(
        thesis_id=thesis.id,
        reviewer=_blank_to_none(payload.get("reviewer")),
        decision_under_review=_choice(
            payload.get("decision_under_review"),
            DECISIONS_UNDER_REVIEW,
            "decision_under_review",
        ),
        core_objections=_red_team_objections(payload),
        competitor_challenges=_lines(payload.get("competitor_challenges")),
        failure_premortem=_blank_to_none(payload.get("failure_premortem")),
        early_warning_signs=_blank_to_none(payload.get("early_warning_signs")),
        preventive_actions=_blank_to_none(payload.get("preventive_actions")),
        kill_criteria=_blank_to_none(payload.get("kill_criteria")),
        decision=_choice(payload.get("decision"), RED_TEAM_DECISIONS, "decision"),
        decision_rationale=_blank_to_none(payload.get("decision_rationale")),
    )
    db.session.add(review)
    _touch(thesis)
    db.session.commit()
    return review


def score_summary(thesis):
    if not thesis:
        return {"weighted_score": 0, "score_percent": 0.0, "band": "unscored"}
    latest_scores = {}
    for score in sorted(thesis.scores, key=lambda item: item.created_at or utc_now()):
        latest_scores[score.factor] = score

    weighted_score = sum(score.weighted_score for score in latest_scores.values())
    score_percent = round((weighted_score / MAX_NICHE_SCORE) * 100, 1)
    if score_percent >= 80:
        band = "strong_candidate"
    elif score_percent >= 65:
        band = "plausible_candidate"
    elif score_percent >= 50:
        band = "weak_or_uncertain"
    elif score_percent > 0:
        band = "poor_candidate"
    else:
        band = "unscored"
    return {
        "weighted_score": weighted_score,
        "score_percent": score_percent,
        "band": band,
        "max_score": MAX_NICHE_SCORE,
        "latest_scores": latest_scores,
    }


def _get_thesis(thesis_id):
    thesis = db.session.get(ContentThesis, thesis_id)
    if not thesis:
        raise ThesisValidationError("Thesis not found.")
    return thesis


def _touch(thesis):
    thesis.updated_at = utc_now()


def _required(payload, field):
    value = _blank_to_none(payload.get(field))
    if not value:
        raise ThesisValidationError(f"{field} is required.")
    return value


def _choice(value, allowed, field):
    value = _blank_to_none(value)
    if value not in allowed:
        raise ThesisValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return value


def _score(value):
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise ThesisValidationError("score must be an integer.") from exc
    if score < 1 or score > 5:
        raise ThesisValidationError("score must be between 1 and 5.")
    return score


def _optional_confidence(value):
    if value in (None, ""):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ThesisValidationError("confidence must be a number.") from exc
    if confidence < 0 or confidence > 1:
        raise ThesisValidationError("confidence must be between 0 and 1.")
    return confidence


def _optional_int(value):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ThesisValidationError("IDs must be integers.") from exc
    return parsed


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _lines(value):
    if not value:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _red_team_objections(payload):
    objections = {}
    for key in (
        "better_channels",
        "easy_to_copy",
        "production_burden",
        "policy_risk",
        "weak_monetization",
        "saturation",
        "shallow_backlog",
        "weak_packaging",
        "unclear_audience",
        "operator_interest",
    ):
        objections[key] = {
            "answer": _blank_to_none(payload.get(f"{key}_answer")),
            "evidence": _blank_to_none(payload.get(f"{key}_evidence")),
            "severity": _blank_to_none(payload.get(f"{key}_severity")),
        }
    return objections

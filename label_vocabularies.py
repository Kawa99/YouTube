LABEL_VOCABULARIES = {
    "niche": [
        "education",
        "finance",
        "health",
        "history",
        "science",
        "technology",
        "business",
        "legal",
        "travel",
        "gaming",
        "lifestyle",
        "news",
        "other",
    ],
    "format": [
        "explainer",
        "documentary",
        "listicle",
        "case_study",
        "news_analysis",
        "tutorial",
        "comparison",
        "story",
        "compilation",
        "commentary",
        "other",
    ],
    "faceless_status": ["faceless", "mixed", "host_led", "unknown"],
    "ai_use_visible": ["none_visible", "possible", "obvious", "unknown"],
    "visual_style": [
        "stock_footage",
        "screen_recording",
        "animation",
        "slideshow",
        "ai_imagery",
        "b_roll",
        "talking_head",
        "mixed",
        "unknown",
    ],
    "packaging_pattern": [
        "curiosity_gap",
        "numbered_list",
        "before_after",
        "contrarian",
        "warning",
        "beginner_guide",
        "case_study",
        "ranking",
        "how_to",
        "other",
    ],
    "topic_type": [
        "evergreen",
        "trend",
        "seasonal",
        "news_reactive",
        "search_intent",
        "controversy",
        "other",
    ],
    "production_complexity": ["low", "medium", "high", "unknown"],
    "policy_risk": ["low", "medium", "high", "unknown"],
    "review_status": ["pending", "reviewed", "skipped", "needs_second_review"],
}

VIDEO_LABEL_FIELDS = (
    "niche",
    "format",
    "faceless_status",
    "ai_use_visible",
    "visual_style",
    "packaging_pattern",
    "topic_type",
    "production_complexity",
    "policy_risk",
    "monetization_signals",
    "notes",
    "review_status",
    "label_confidence",
)

CONTROLLED_VIDEO_LABEL_FIELDS = tuple(
    field for field in VIDEO_LABEL_FIELDS if field in LABEL_VOCABULARIES
)


def vocabulary_options(field):
    return LABEL_VOCABULARIES.get(field, [])

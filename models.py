from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


class Channel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.Integer, primary_key=True)
    channel_username = db.Column(db.String, unique=True, nullable=False)
    subscribers = db.Column(db.Integer, nullable=False, default=0)
    youtube_channel_id = db.Column(db.String, unique=True, nullable=True, index=True)
    channel_name = db.Column(db.String)
    handle = db.Column(db.String, index=True)
    custom_url = db.Column(db.String)
    canonical_url = db.Column(db.String)
    description = db.Column(db.Text)
    published_at = db.Column(db.DateTime)
    subscriber_count = db.Column(db.Integer)
    view_count = db.Column(db.Integer)
    video_count = db.Column(db.Integer)
    country = db.Column(db.String)
    default_language = db.Column(db.String)
    is_tracked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    last_collected_at = db.Column(db.DateTime)

    videos = db.relationship(
        "Video",
        back_populates="channel",
        lazy=True,
        foreign_keys="Video.channel_id",
    )
    history_records = db.relationship(
        "ChannelHistory", back_populates="channel", lazy=True
    )
    linked_videos = db.relationship("ChannelVideo", back_populates="channel", lazy=True)
    snapshots = db.relationship(
        "ChannelSnapshot",
        back_populates="channel",
        lazy=True,
        cascade="all, delete-orphan",
    )
    labels = db.relationship(
        "ChannelLabel",
        back_populates="channel",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    youtube_video_id = db.Column(db.String, unique=True)
    youtube_channel_id = db.Column(
        db.String,
        db.ForeignKey("channels.youtube_channel_id"),
        nullable=True,
        index=True,
    )
    title = db.Column(db.String)
    description = db.Column(db.Text)
    description_excerpt = db.Column(db.Text)
    description_full = db.Column(db.Text)
    views = db.Column(db.Integer)
    likes = db.Column(db.Integer)
    comments = db.Column(db.Integer)
    posted = db.Column(db.String)
    published_at = db.Column(db.DateTime)
    video_length = db.Column(db.String)
    duration_seconds = db.Column(db.Integer)
    category_id = db.Column(db.String)
    default_language = db.Column(db.String)
    caption_available = db.Column(db.Boolean)
    thumbnail_url = db.Column(db.String)
    thumbnail_quality = db.Column(db.String)
    thumbnail_cached_path = db.Column(db.String)
    thumbnail_phash = db.Column(db.String)
    transcript = db.Column(db.Text)
    transcript_status = db.Column(db.String)
    transcript_text = db.Column(db.Text)
    saved_at = db.Column(db.Text, server_default=db.text("CURRENT_TIMESTAMP"))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    last_collected_at = db.Column(db.DateTime)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"))

    channel = db.relationship(
        "Channel", back_populates="videos", foreign_keys=[channel_id]
    )
    linked_channels = db.relationship("ChannelVideo", back_populates="video", lazy=True)
    history = db.relationship(
        "VideoHistory",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )
    snapshots = db.relationship(
        "VideoSnapshot",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )
    metadata_changes = db.relationship(
        "VideoMetadataChange",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )
    labels = db.relationship(
        "VideoLabel",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )
    derived_metrics = db.relationship(
        "VideoDerivedMetric",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )
    metadata_history = db.relationship(
        "VideoMetadataHistory",
        back_populates="video",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def _safe_percentage_rate(self, numerator):
        """Return a 2-decimal percentage, suppressing invalid math states."""
        try:
            return round((numerator / self.views) * 100, 2)
        except (ZeroDivisionError, TypeError):
            return 0.0

    @property
    def like_rate(self):
        """Likes as a percentage of views."""
        return self._safe_percentage_rate(self.likes)

    @property
    def comment_rate(self):
        """Comments as a percentage of views."""
        return self._safe_percentage_rate(self.comments)

    @property
    def engagement_rate(self):
        """Combined likes + comments as a percentage of views."""
        try:
            engagement_total = (self.likes or 0) + (self.comments or 0)
        except TypeError:
            engagement_total = 0
        return self._safe_percentage_rate(engagement_total)


class ChannelHistory(db.Model):
    __tablename__ = "channel_history"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), nullable=False)
    previous_subscribers = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.Text, server_default=db.text("CURRENT_TIMESTAMP"))

    channel = db.relationship("Channel", back_populates="history_records")


class VideoHistory(db.Model):
    __tablename__ = "video_history"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    views = db.Column(db.Integer, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    comments = db.Column(db.Integer, nullable=False, default=0)
    timestamp = db.Column(db.DateTime, nullable=False, default=utc_now)

    video = db.relationship("Video", back_populates="history")


class VideoMetadataHistory(db.Model):
    __tablename__ = "video_metadata_history"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    old_title = db.Column(db.String, nullable=False, default="")
    new_title = db.Column(db.String, nullable=False, default="")
    old_thumbnail = db.Column(db.String, nullable=False, default="")
    new_thumbnail = db.Column(db.String, nullable=False, default="")
    changed_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    video = db.relationship("Video", back_populates="metadata_history")


class ChannelVideo(db.Model):
    __tablename__ = "channel_videos"

    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), primary_key=True)

    video = db.relationship("Video", back_populates="linked_channels")
    channel = db.relationship("Channel", back_populates="linked_videos")


class CollectionRun(db.Model):
    __tablename__ = "collection_runs"

    id = db.Column(db.Integer, primary_key=True)
    run_type = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False, default="completed")
    input_type = db.Column(db.String)
    input_value = db.Column(db.String)
    requested_limit = db.Column(db.Integer)
    started_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime)
    quota_estimate = db.Column(db.Integer)
    items_found = db.Column(db.Integer, nullable=False, default=0)
    items_saved = db.Column(db.Integer, nullable=False, default=0)
    items_failed = db.Column(db.Integer, nullable=False, default=0)
    error_summary = db.Column(db.Text)
    created_by = db.Column(db.String)

    raw_payloads = db.relationship("ApiRawPayload", back_populates="collection_run")
    video_snapshots = db.relationship("VideoSnapshot", back_populates="collection_run")
    channel_snapshots = db.relationship(
        "ChannelSnapshot", back_populates="collection_run"
    )
    metadata_changes = db.relationship(
        "VideoMetadataChange", back_populates="collection_run"
    )


class ApiRawPayload(db.Model):
    __tablename__ = "api_raw_payloads"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String, nullable=False)
    endpoint = db.Column(db.String, nullable=False)
    external_id = db.Column(db.String, index=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    collection_run_id = db.Column(db.Integer, db.ForeignKey("collection_runs.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    collection_run = db.relationship("CollectionRun", back_populates="raw_payloads")


class VideoSnapshot(db.Model):
    __tablename__ = "video_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    snapshot_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    comment_count = db.Column(db.Integer, nullable=False, default=0)
    subscriber_count_at_snapshot = db.Column(db.Integer)
    collection_run_id = db.Column(db.Integer, db.ForeignKey("collection_runs.id"))

    video = db.relationship("Video", back_populates="snapshots")
    collection_run = db.relationship("CollectionRun", back_populates="video_snapshots")


class ChannelSnapshot(db.Model):
    __tablename__ = "channel_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), nullable=False)
    snapshot_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    subscriber_count = db.Column(db.Integer, nullable=False, default=0)
    view_count = db.Column(db.Integer)
    video_count = db.Column(db.Integer)
    collection_run_id = db.Column(db.Integer, db.ForeignKey("collection_runs.id"))

    channel = db.relationship("Channel", back_populates="snapshots")
    collection_run = db.relationship(
        "CollectionRun", back_populates="channel_snapshots"
    )


class VideoMetadataChange(db.Model):
    __tablename__ = "video_metadata_changes"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    field_name = db.Column(db.String, nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    collection_run_id = db.Column(db.Integer, db.ForeignKey("collection_runs.id"))

    video = db.relationship("Video", back_populates="metadata_changes")
    collection_run = db.relationship("CollectionRun", back_populates="metadata_changes")


class VideoLabel(db.Model):
    __tablename__ = "video_labels"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    niche = db.Column(db.String)
    format = db.Column(db.String)
    faceless_status = db.Column(db.String)
    ai_use_visible = db.Column(db.String)
    visual_style = db.Column(db.String)
    packaging_pattern = db.Column(db.String)
    title_pattern = db.Column(db.String)
    thumbnail_pattern = db.Column(db.String)
    viewer_promise = db.Column(db.Text)
    curiosity_type = db.Column(db.String)
    clarity_score = db.Column(db.Integer)
    specificity_score = db.Column(db.Integer)
    honesty_score = db.Column(db.Integer)
    visual_readability_score = db.Column(db.Integer)
    differentiation_score = db.Column(db.Integer)
    topic_type = db.Column(db.String)
    production_complexity = db.Column(db.String)
    policy_risk = db.Column(db.String)
    monetization_signals = db.Column(db.Text)
    reviewer = db.Column(db.String)
    review_status = db.Column(db.String, nullable=False, default="pending")
    reviewed_at = db.Column(db.DateTime)
    label_confidence = db.Column(db.Float)
    notes = db.Column(db.Text)

    video = db.relationship("Video", back_populates="labels")
    audits = db.relationship(
        "VideoLabelAudit",
        back_populates="video_label",
        lazy=True,
        cascade="all, delete-orphan",
    )


class VideoLabelAudit(db.Model):
    __tablename__ = "video_label_audits"

    id = db.Column(db.Integer, primary_key=True)
    video_label_id = db.Column(db.Integer, db.ForeignKey("video_labels.id"))
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    action = db.Column(db.String, nullable=False)
    reviewer = db.Column(db.String)
    previous_values = db.Column(db.JSON, nullable=False, default=dict)
    new_values = db.Column(db.JSON, nullable=False, default=dict)
    label_confidence = db.Column(db.Float)
    changed_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    video_label = db.relationship("VideoLabel", back_populates="audits")
    video = db.relationship("Video")


class ChannelLabel(db.Model):
    __tablename__ = "channel_labels"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), nullable=False)
    primary_niche = db.Column(db.String)
    primary_format = db.Column(db.String)
    faceless_status = db.Column(db.String)
    sponsor_fit = db.Column(db.String)
    policy_risk = db.Column(db.String)
    production_complexity = db.Column(db.String)
    notes = db.Column(db.Text)
    reviewer = db.Column(db.String)
    reviewed_at = db.Column(db.DateTime)

    channel = db.relationship("Channel", back_populates="labels")


class VideoDerivedMetric(db.Model):
    __tablename__ = "video_derived_metrics"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    snapshot_at = db.Column(db.DateTime, nullable=False)
    age_days = db.Column(db.Float)
    views_per_day = db.Column(db.Float)
    views_per_subscriber = db.Column(db.Float)
    channel_recent_median_views = db.Column(db.Float)
    relative_performance = db.Column(db.Float)
    duration_bucket = db.Column(db.String)
    performance_tier = db.Column(db.String)
    outlier_flag = db.Column(db.Boolean, nullable=False, default=False)
    like_rate = db.Column(db.Float)
    comment_rate = db.Column(db.Float)
    engagement_rate = db.Column(db.Float)
    computed_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    algorithm_version = db.Column(db.String, nullable=False)

    video = db.relationship("Video", back_populates="derived_metrics")


class ChannelDerivedSummary(db.Model):
    __tablename__ = "channel_derived_summaries"

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"), nullable=False)
    snapshot_at = db.Column(db.DateTime, nullable=False)
    median_recent_views = db.Column(db.Float)
    median_views_per_subscriber = db.Column(db.Float)
    upload_cadence_days = db.Column(db.Float)
    average_duration_seconds = db.Column(db.Float)
    top_outlier_topics = db.Column(db.JSON, nullable=False, default=list)
    format_distribution = db.Column(db.JSON, nullable=False, default=dict)
    packaging_pattern_distribution = db.Column(db.JSON, nullable=False, default=dict)
    visible_monetization_signals = db.Column(db.JSON, nullable=False, default=list)
    computed_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    algorithm_version = db.Column(db.String, nullable=False)

    channel = db.relationship("Channel")


class PackagingExperiment(db.Model):
    __tablename__ = "packaging_experiments"

    id = db.Column(db.Integer, primary_key=True)
    working_title = db.Column(db.String, nullable=False)
    niche = db.Column(db.String)
    format = db.Column(db.String)
    title_candidates = db.Column(db.JSON, nullable=False, default=list)
    thumbnail_concepts = db.Column(db.JSON, nullable=False, default=list)
    experiment_log_url = db.Column(db.String)
    final_title = db.Column(db.String)
    final_thumbnail_concept = db.Column(db.Text)
    final_choice_reason = db.Column(db.Text)
    status = db.Column(db.String, nullable=False, default="draft")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class ContentThesis(db.Model):
    __tablename__ = "content_theses"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(db.String, nullable=False, unique=True, index=True)
    title = db.Column(db.String, nullable=False)
    target_viewer = db.Column(db.Text)
    viewer_promise = db.Column(db.Text)
    format = db.Column(db.String)
    topic_universe = db.Column(db.Text)
    production_edge = db.Column(db.Text)
    packaging_edge = db.Column(db.Text)
    monetization_path = db.Column(db.Text)
    policy_risk_argument = db.Column(db.Text)
    status = db.Column(db.String, nullable=False, default="idea")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    evidence = db.relationship(
        "ThesisEvidence",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    topics = db.relationship(
        "ThesisTopic",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    scores = db.relationship(
        "ThesisScore",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    red_team_reviews = db.relationship(
        "RedTeamReview",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    monetization_maps = db.relationship(
        "ThesisMonetizationMap",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    sponsor_evidence = db.relationship(
        "SponsorEvidence",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )
    affiliate_evidence = db.relationship(
        "AffiliateProductEvidence",
        back_populates="thesis",
        lazy=True,
        cascade="all, delete-orphan",
    )


class ThesisEvidence(db.Model):
    __tablename__ = "thesis_evidence"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    evidence_type = db.Column(db.String, nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"))
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"))
    source_url = db.Column(db.String)
    note = db.Column(db.Text)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="evidence")
    channel = db.relationship("Channel")
    video = db.relationship("Video")


class ThesisTopic(db.Model):
    __tablename__ = "thesis_topics"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    topic = db.Column(db.String, nullable=False)
    title_angle = db.Column(db.String)
    demand_evidence = db.Column(db.Text)
    source_availability = db.Column(db.String)
    production_complexity = db.Column(db.String)
    packaging_potential = db.Column(db.String)
    status = db.Column(db.String, nullable=False, default="backlog")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="topics")


class ThesisScore(db.Model):
    __tablename__ = "thesis_scores"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    factor = db.Column(db.String, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    weighted_score = db.Column(db.Integer, nullable=False)
    evidence = db.Column(db.Text)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="scores")


class RedTeamReview(db.Model):
    __tablename__ = "red_team_reviews"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    reviewer = db.Column(db.String)
    decision_under_review = db.Column(db.String, nullable=False)
    core_objections = db.Column(db.JSON, nullable=False, default=dict)
    competitor_challenges = db.Column(db.JSON, nullable=False, default=list)
    failure_premortem = db.Column(db.Text)
    early_warning_signs = db.Column(db.Text)
    preventive_actions = db.Column(db.Text)
    kill_criteria = db.Column(db.Text)
    decision = db.Column(db.String, nullable=False)
    decision_rationale = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="red_team_reviews")


class ThesisMonetizationMap(db.Model):
    __tablename__ = "thesis_monetization_maps"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    revenue_paths = db.Column(db.JSON, nullable=False, default=list)
    primary_revenue_path = db.Column(db.String)
    secondary_revenue_path = db.Column(db.String)
    conservative_ad_rpm = db.Column(db.Float)
    base_ad_rpm = db.Column(db.Float)
    upside_ad_rpm = db.Column(db.Float)
    sponsor_rpm_equivalent = db.Column(db.Float)
    affiliate_rpm_equivalent = db.Column(db.Float)
    membership_rpm_equivalent = db.Column(db.Float)
    product_rpm_equivalent = db.Column(db.Float)
    break_even_view_count = db.Column(db.Integer)
    meaningful_income_view_count = db.Column(db.Integer)
    assumptions = db.Column(db.Text)
    main_monetization_risk = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    thesis = db.relationship("ContentThesis", back_populates="monetization_maps")


class SponsorEvidence(db.Model):
    __tablename__ = "sponsor_evidence"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    sponsor_category = db.Column(db.String, nullable=False)
    observed_sponsor = db.Column(db.String)
    competitor_channel_id = db.Column(db.Integer, db.ForeignKey("channels.id"))
    video_url = db.Column(db.String)
    date_observed = db.Column(db.DateTime)
    niche_fit = db.Column(db.String)
    brand_safety_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="sponsor_evidence")
    competitor_channel = db.relationship("Channel")


class AffiliateProductEvidence(db.Model):
    __tablename__ = "affiliate_product_evidence"

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(
        db.Integer, db.ForeignKey("content_theses.id"), nullable=False
    )
    product_category = db.Column(db.String, nullable=False)
    program_source = db.Column(db.String)
    estimated_fit = db.Column(db.String)
    audience_intent = db.Column(db.String)
    compliance_disclosure_concerns = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    thesis = db.relationship("ContentThesis", back_populates="affiliate_evidence")


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String, nullable=False, unique=True, index=True)
    asset_type = db.Column(db.String, nullable=False)
    source_url_path = db.Column(db.String, nullable=False)
    creator_licensor = db.Column(db.String)
    license_terms = db.Column(db.Text)
    monetized_youtube_allowed = db.Column(db.String, nullable=False, default="unclear")
    attribution_required = db.Column(db.Boolean, nullable=False, default=False)
    proof_saved = db.Column(db.Boolean, nullable=False, default=False)
    high_risk_flag = db.Column(db.Boolean, nullable=False, default=False)
    high_risk_reason = db.Column(db.String)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    video_links = db.relationship(
        "VideoAsset",
        back_populates="asset",
        lazy=True,
        cascade="all, delete-orphan",
    )


class VideoAsset(db.Model):
    __tablename__ = "video_assets"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    intended_use = db.Column(db.Text)
    attribution_text = db.Column(db.Text)
    rights_decision = db.Column(db.String, nullable=False, default="use")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    video = db.relationship("Video")
    asset = db.relationship("Asset", back_populates="video_links")


class VideoRightsChecklist(db.Model):
    __tablename__ = "video_rights_checklists"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    every_asset_has_row = db.Column(db.Boolean, nullable=False, default=False)
    unclear_assets_blocked = db.Column(db.Boolean, nullable=False, default=False)
    attribution_captured = db.Column(db.Boolean, nullable=False, default=False)
    synthetic_altered_status = db.Column(db.String, nullable=False, default="none")
    no_terms_prohibit_monetization = db.Column(
        db.Boolean, nullable=False, default=False
    )
    ready_for_upload = db.Column(db.Boolean, nullable=False, default=False)
    reviewer = db.Column(db.String)
    reviewed_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    notes = db.Column(db.Text)

    video = db.relationship("Video")


class VideoDisclosure(db.Model):
    __tablename__ = "video_disclosures"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    sponsor_disclosure = db.Column(db.Text)
    affiliate_disclosure = db.Column(db.Text)
    altered_synthetic_disclosure = db.Column(db.Text)
    music_license_attribution = db.Column(db.Text)
    disclosure_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    video = db.relationship("Video")

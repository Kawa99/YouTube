import csv
import io
import json
import tempfile
import zipfile
from datetime import date, datetime

from openpyxl import Workbook
from sqlalchemy import text

from models import db

CORE_EXPORT_TABLES = (
    "channels",
    "videos",
    "channel_snapshots",
    "video_snapshots",
    "video_metadata_changes",
    "video_labels",
    "video_label_audits",
    "channel_labels",
    "collection_runs",
    "video_derived_metrics",
    "channel_derived_summaries",
    "packaging_experiments",
    "content_theses",
    "thesis_evidence",
    "thesis_topics",
    "thesis_scores",
    "red_team_reviews",
    "thesis_monetization_maps",
    "sponsor_evidence",
    "affiliate_product_evidence",
    "assets",
    "video_assets",
    "video_rights_checklists",
    "video_disclosures",
    "owned_analytics_credentials",
    "owned_video_analytics",
    "retention_diagnostics",
    "experiments",
    "experiment_checkpoints",
    # Compatibility tables kept for the current UI and old exports.
    "channel_videos",
    "channel_history",
    "video_history",
    "video_metadata_history",
)
EXPORT_TABLES = CORE_EXPORT_TABLES
TABLE_SELECT_QUERIES = {
    "channels": "SELECT * FROM channels",
    "videos": "SELECT * FROM videos",
    "channel_snapshots": "SELECT * FROM channel_snapshots",
    "video_snapshots": "SELECT * FROM video_snapshots",
    "video_metadata_changes": "SELECT * FROM video_metadata_changes",
    "video_labels": "SELECT * FROM video_labels",
    "video_label_audits": "SELECT * FROM video_label_audits",
    "channel_labels": "SELECT * FROM channel_labels",
    "collection_runs": "SELECT * FROM collection_runs",
    "video_derived_metrics": "SELECT * FROM video_derived_metrics",
    "channel_derived_summaries": "SELECT * FROM channel_derived_summaries",
    "packaging_experiments": "SELECT * FROM packaging_experiments",
    "content_theses": "SELECT * FROM content_theses",
    "thesis_evidence": "SELECT * FROM thesis_evidence",
    "thesis_topics": "SELECT * FROM thesis_topics",
    "thesis_scores": "SELECT * FROM thesis_scores",
    "red_team_reviews": "SELECT * FROM red_team_reviews",
    "thesis_monetization_maps": "SELECT * FROM thesis_monetization_maps",
    "sponsor_evidence": "SELECT * FROM sponsor_evidence",
    "affiliate_product_evidence": "SELECT * FROM affiliate_product_evidence",
    "assets": "SELECT * FROM assets",
    "video_assets": "SELECT * FROM video_assets",
    "video_rights_checklists": "SELECT * FROM video_rights_checklists",
    "video_disclosures": "SELECT * FROM video_disclosures",
    "owned_analytics_credentials": "SELECT * FROM owned_analytics_credentials",
    "owned_video_analytics": "SELECT * FROM owned_video_analytics",
    "retention_diagnostics": "SELECT * FROM retention_diagnostics",
    "experiments": "SELECT * FROM experiments",
    "experiment_checkpoints": "SELECT * FROM experiment_checkpoints",
    "channel_videos": "SELECT * FROM channel_videos",
    "channel_history": "SELECT * FROM channel_history",
    "video_history": "SELECT * FROM video_history",
    "video_metadata_history": "SELECT * FROM video_metadata_history",
}
DB_FETCH_CHUNK_SIZE = 1000
RESEARCH_ZIP_FILES = (
    "channels.csv",
    "videos.csv",
    "manual_labels.csv",
    "snapshots.csv",
    "derived_metrics.csv",
    "content_theses.csv",
    "thesis_evidence.csv",
    "thesis_topics.csv",
    "thesis_scores.csv",
    "red_team_reviews.csv",
    "thesis_monetization_maps.csv",
    "sponsor_evidence.csv",
    "affiliate_product_evidence.csv",
    "assets.csv",
    "video_assets.csv",
    "video_rights_checklists.csv",
    "video_disclosures.csv",
    "owned_analytics_credentials.csv",
    "owned_video_analytics.csv",
    "retention_diagnostics.csv",
    "experiments.csv",
    "experiment_checkpoints.csv",
    "collection_runs.csv",
    "data_dictionary.md",
)
RESEARCH_HEADERS = {
    "channels": [
        "channel_id",
        "youtube_channel_id",
        "channel_username",
        "channel_name",
        "handle",
        "canonical_url",
        "subscriber_count",
        "view_count",
        "video_count",
        "country",
        "default_language",
        "published_at",
        "last_collected_at",
        "primary_niche",
        "primary_format",
        "faceless_status",
        "sponsor_fit",
        "policy_risk",
        "production_complexity",
        "reviewer",
        "reviewed_at",
        "notes",
    ],
    "videos": [
        "video_id",
        "youtube_video_id",
        "youtube_channel_id",
        "channel_username",
        "channel_name",
        "title",
        "description_excerpt",
        "published_at",
        "duration_seconds",
        "category_id",
        "default_language",
        "caption_available",
        "thumbnail_url",
        "thumbnail_quality",
        "thumbnail_cached_path",
        "thumbnail_phash",
        "transcript_status",
        "views",
        "likes",
        "comments",
        "last_collected_at",
        "niche",
        "format",
        "faceless_status",
        "visual_style",
        "packaging_pattern",
        "title_pattern",
        "thumbnail_pattern",
        "viewer_promise",
        "curiosity_type",
        "clarity_score",
        "specificity_score",
        "honesty_score",
        "visual_readability_score",
        "differentiation_score",
        "topic_type",
        "production_complexity",
        "policy_risk",
        "review_status",
        "label_confidence",
    ],
    "manual_labels": [
        "entity_type",
        "entity_id",
        "youtube_id",
        "display_name",
        "channel_username",
        "niche",
        "format",
        "faceless_status",
        "ai_use_visible",
        "visual_style",
        "packaging_pattern",
        "title_pattern",
        "thumbnail_pattern",
        "viewer_promise",
        "curiosity_type",
        "clarity_score",
        "specificity_score",
        "honesty_score",
        "visual_readability_score",
        "differentiation_score",
        "topic_type",
        "production_complexity",
        "policy_risk",
        "monetization_signals",
        "sponsor_fit",
        "reviewer",
        "review_status",
        "reviewed_at",
        "label_confidence",
        "notes",
    ],
    "snapshots": [
        "entity_type",
        "snapshot_id",
        "entity_id",
        "youtube_id",
        "display_name",
        "channel_username",
        "snapshot_at",
        "view_count",
        "like_count",
        "comment_count",
        "subscriber_count",
        "video_count",
        "collection_run_id",
    ],
    "derived_metrics": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "channel_username",
        "youtube_channel_id",
        "snapshot_at",
        "age_days",
        "views_per_day",
        "views_per_subscriber",
        "channel_recent_median_views",
        "relative_performance",
        "duration_bucket",
        "performance_tier",
        "outlier_flag",
        "like_rate",
        "comment_rate",
        "engagement_rate",
        "computed_at",
        "algorithm_version",
    ],
    "collection_runs": [
        "id",
        "run_type",
        "status",
        "input_type",
        "input_value",
        "requested_limit",
        "started_at",
        "completed_at",
        "quota_estimate",
        "items_found",
        "items_saved",
        "items_failed",
        "error_summary",
        "created_by",
    ],
    "content_theses": [
        "id",
        "thesis_id",
        "title",
        "target_viewer",
        "viewer_promise",
        "format",
        "topic_universe",
        "production_edge",
        "packaging_edge",
        "monetization_path",
        "policy_risk_argument",
        "status",
        "notes",
        "created_at",
        "updated_at",
    ],
    "thesis_evidence": [
        "id",
        "thesis_id",
        "thesis_code",
        "evidence_type",
        "channel_id",
        "channel_username",
        "video_id",
        "youtube_video_id",
        "source_url",
        "note",
        "confidence",
        "created_at",
    ],
    "thesis_topics": [
        "id",
        "thesis_id",
        "thesis_code",
        "topic",
        "title_angle",
        "demand_evidence",
        "source_availability",
        "production_complexity",
        "packaging_potential",
        "status",
        "created_at",
    ],
    "thesis_scores": [
        "id",
        "thesis_id",
        "thesis_code",
        "factor",
        "weight",
        "score",
        "weighted_score",
        "evidence",
        "confidence",
        "created_at",
    ],
    "red_team_reviews": [
        "id",
        "thesis_id",
        "thesis_code",
        "reviewer",
        "decision_under_review",
        "core_objections",
        "competitor_challenges",
        "failure_premortem",
        "early_warning_signs",
        "preventive_actions",
        "kill_criteria",
        "decision",
        "decision_rationale",
        "reviewed_at",
    ],
    "thesis_monetization_maps": [
        "id",
        "thesis_id",
        "thesis_code",
        "revenue_paths",
        "primary_revenue_path",
        "secondary_revenue_path",
        "conservative_ad_rpm",
        "base_ad_rpm",
        "upside_ad_rpm",
        "sponsor_rpm_equivalent",
        "affiliate_rpm_equivalent",
        "membership_rpm_equivalent",
        "product_rpm_equivalent",
        "break_even_view_count",
        "meaningful_income_view_count",
        "assumptions",
        "main_monetization_risk",
        "created_at",
        "updated_at",
    ],
    "sponsor_evidence": [
        "id",
        "thesis_id",
        "thesis_code",
        "sponsor_category",
        "observed_sponsor",
        "competitor_channel_id",
        "competitor_channel_username",
        "video_url",
        "date_observed",
        "niche_fit",
        "brand_safety_notes",
        "created_at",
    ],
    "affiliate_product_evidence": [
        "id",
        "thesis_id",
        "thesis_code",
        "product_category",
        "program_source",
        "estimated_fit",
        "audience_intent",
        "compliance_disclosure_concerns",
        "created_at",
    ],
    "assets": [
        "id",
        "asset_id",
        "asset_type",
        "source_url_path",
        "creator_licensor",
        "license_terms",
        "monetized_youtube_allowed",
        "attribution_required",
        "proof_saved",
        "high_risk_flag",
        "high_risk_reason",
        "notes",
        "created_at",
        "updated_at",
    ],
    "video_assets": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "asset_row_id",
        "asset_id",
        "asset_type",
        "intended_use",
        "attribution_text",
        "rights_decision",
        "created_at",
    ],
    "video_rights_checklists": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "every_asset_has_row",
        "unclear_assets_blocked",
        "attribution_captured",
        "synthetic_altered_status",
        "no_terms_prohibit_monetization",
        "ready_for_upload",
        "reviewer",
        "reviewed_at",
        "notes",
    ],
    "video_disclosures": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "sponsor_disclosure",
        "affiliate_disclosure",
        "altered_synthetic_disclosure",
        "music_license_attribution",
        "disclosure_notes",
        "created_at",
    ],
    "owned_analytics_credentials": [
        "id",
        "channel_id",
        "youtube_channel_id",
        "channel_username",
        "google_account_email",
        "scopes",
        "token_secret_ref",
        "status",
        "created_at",
        "revoked_at",
        "notes",
    ],
    "owned_video_analytics": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "date",
        "views",
        "impressions",
        "impression_ctr",
        "average_view_duration_seconds",
        "average_view_percentage",
        "watch_time_minutes",
        "subscribers_gained",
        "estimated_revenue",
        "traffic_source_type",
        "source",
        "created_at",
    ],
    "retention_diagnostics": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "report_date",
        "ctr",
        "average_view_duration_seconds",
        "average_view_percentage",
        "impressions",
        "dominant_traffic_source",
        "retention_pattern",
        "likely_cause",
        "evidence",
        "next_change",
        "notes",
        "created_at",
    ],
    "experiments": [
        "id",
        "video_id",
        "youtube_video_id",
        "title",
        "hypothesis",
        "variable_tested",
        "experiment_title",
        "thumbnail_variant",
        "publish_date",
        "success_metric",
        "production_hours",
        "production_cost",
        "decision",
        "notes",
        "created_at",
    ],
    "experiment_checkpoints": [
        "id",
        "experiment_id",
        "video_id",
        "youtube_video_id",
        "checkpoint",
        "views",
        "impressions",
        "impression_ctr",
        "average_view_duration_seconds",
        "average_view_percentage",
        "watch_time_minutes",
        "subscribers_gained",
        "main_traffic_source",
        "notes",
        "recorded_at",
    ],
}


DATA_DICTIONARY_ROWS = [
    (
        "channels.csv",
        "youtube_channel_id",
        "string",
        "Stable YouTube channel ID.",
        "channels",
        "normalized",
        "",
    ),
    (
        "channels.csv",
        "primary_niche",
        "string",
        "Human-reviewed channel niche.",
        "channel_labels",
        "manual",
        "Project-specific niche taxonomy.",
    ),
    (
        "videos.csv",
        "youtube_video_id",
        "string",
        "Stable YouTube video ID.",
        "videos",
        "normalized",
        "",
    ),
    (
        "videos.csv",
        "duration_seconds",
        "integer",
        "Analysis-friendly video duration.",
        "videos",
        "normalized",
        "",
    ),
    (
        "manual_labels.csv",
        "faceless_status",
        "string",
        "Whether the video or channel appears faceless.",
        "video_labels/channel_labels",
        "manual",
        "faceless|mixed|host-led|unknown",
    ),
    (
        "manual_labels.csv",
        "policy_risk",
        "string",
        "Human-reviewed policy or monetization risk.",
        "video_labels/channel_labels",
        "manual",
        "low|medium|high|unknown",
    ),
    (
        "snapshots.csv",
        "snapshot_at",
        "datetime",
        "Timestamp when public metrics were collected.",
        "video_snapshots/channel_snapshots",
        "raw",
        "",
    ),
    (
        "derived_metrics.csv",
        "relative_performance",
        "float",
        "Video performance versus channel baseline.",
        "video_derived_metrics",
        "derived",
        "",
    ),
    (
        "derived_metrics.csv",
        "outlier_flag",
        "boolean",
        "Whether the video is marked as a performance outlier.",
        "video_derived_metrics",
        "derived",
        "true|false",
    ),
    (
        "collection_runs.csv",
        "quota_estimate",
        "integer",
        "Estimated YouTube API quota cost for the run.",
        "collection_runs",
        "raw",
        "",
    ),
    (
        "owned_analytics_credentials.csv",
        "token_secret_ref",
        "string",
        "Reference to an external secret-manager token; raw OAuth tokens are never exported.",
        "owned_analytics_credentials",
        "auth_metadata",
        "",
    ),
    (
        "owned_video_analytics.csv",
        "impression_ctr",
        "float",
        "Owned-channel YouTube Studio CTR only; never competitor private data.",
        "owned_video_analytics",
        "owned_private",
        "",
    ),
    (
        "retention_diagnostics.csv",
        "retention_pattern",
        "string",
        "Human-coded retention pattern from the owned-channel diagnostics protocol.",
        "retention_diagnostics",
        "owned_private",
        "early_cliff|slow_bleed|mid_video_drop|spike_replay|high_ctr_low_retention|low_ctr_high_retention|low_impressions_good_response|good_search_weak_browse|unknown",
    ),
    (
        "experiment_checkpoints.csv",
        "checkpoint",
        "string",
        "Pilot review window for owned experiments.",
        "experiment_checkpoints",
        "owned_private",
        "24h|7d|30d",
    ),
]


def execute_table_query(table_name):
    query = TABLE_SELECT_QUERIES.get(table_name)
    if query is None:
        raise ValueError(f"Unsupported table name: {table_name}")
    return db.session.execute(text(query))


def iter_table_csv(table_name):
    result = execute_table_query(table_name)
    columns = list(result.keys())

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(columns)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    try:
        while True:
            rows = result.fetchmany(DB_FETCH_CHUNK_SIZE)
            if not rows:
                break

            writer.writerows(
                tuple(_serialize_value(value) for value in row) for row in rows
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
    finally:
        result.close()


def stream_all_tables_csv():
    for table_name in EXPORT_TABLES:
        yield f"=== {table_name.upper()} ===\n"
        yield from iter_table_csv(table_name)
        yield "\n"


def build_xlsx_export_file():
    workbook = Workbook(write_only=True)

    try:
        for table_name in EXPORT_TABLES:
            sheet = workbook.create_sheet(title=table_name[:31])
            result = execute_table_query(table_name)
            columns = list(result.keys())
            sheet.append(columns)

            try:
                while True:
                    rows = result.fetchmany(DB_FETCH_CHUNK_SIZE)
                    if not rows:
                        break
                    for row in rows:
                        sheet.append(tuple(_serialize_value(value) for value in row))
            finally:
                result.close()

        temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        workbook.save(temp_file_path)
        return temp_file_path
    finally:
        workbook.close()


def normalize_export_filters(args):
    return {
        "niche": _blank_to_none(args.get("niche")),
        "format": _blank_to_none(args.get("format")),
        "channel": _blank_to_none(args.get("channel")),
        "date_from": _blank_to_none(args.get("date_from")),
        "date_to": _blank_to_none(args.get("date_to")),
        "collection_run_id": _optional_int(args.get("collection_run")),
        "labeled": _optional_bool(args.get("labeled")),
        "outlier_flag": _optional_bool(args.get("outlier_flag")),
    }


def build_research_zip_file(filters=None):
    filters = filters or {}
    temp_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temp_file_path = temp_file.name
    temp_file.close()

    with zipfile.ZipFile(
        temp_file_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for filename in RESEARCH_ZIP_FILES:
            if filename == "data_dictionary.md":
                archive.writestr(filename, generate_data_dictionary_markdown())
                continue

            dataset = filename.removesuffix(".csv")
            rows = list(iter_research_rows(dataset, filters))
            archive.writestr(filename, _rows_to_csv(rows, RESEARCH_HEADERS[dataset]))

    return temp_file_path


def stream_research_jsonl(filters=None):
    filters = filters or {}
    for dataset in (
        "channels",
        "videos",
        "manual_labels",
        "snapshots",
        "derived_metrics",
        "content_theses",
        "thesis_evidence",
        "thesis_topics",
        "thesis_scores",
        "red_team_reviews",
        "thesis_monetization_maps",
        "sponsor_evidence",
        "affiliate_product_evidence",
        "assets",
        "video_assets",
        "video_rights_checklists",
        "video_disclosures",
        "owned_analytics_credentials",
        "owned_video_analytics",
        "retention_diagnostics",
        "experiments",
        "experiment_checkpoints",
        "collection_runs",
    ):
        for row in iter_research_rows(dataset, filters):
            yield json.dumps(
                {"dataset": dataset, **row}, default=_serialize_value
            ) + "\n"


def iter_research_rows(dataset, filters=None):
    filters = filters or {}
    query, params = _research_query(dataset, filters)
    result = db.session.execute(text(query), params)
    try:
        for row in result.mappings():
            yield {key: _serialize_value(value) for key, value in dict(row).items()}
    finally:
        result.close()


def generate_data_dictionary_markdown():
    buffer = io.StringIO()
    buffer.write("# Research Export Data Dictionary\n\n")
    buffer.write(
        "| file | field | type | description | source table | layer | allowed labels |\n"
    )
    buffer.write("|---|---|---|---|---|---|---|\n")
    for row in _data_dictionary_rows():
        buffer.write("| " + " | ".join(_markdown_cell(value) for value in row) + " |\n")
    return buffer.getvalue()


def _data_dictionary_rows():
    overrides = {
        (file_name, field): (
            field_type,
            description,
            source_table,
            layer,
            allowed_labels,
        )
        for (
            file_name,
            field,
            field_type,
            description,
            source_table,
            layer,
            allowed_labels,
        ) in DATA_DICTIONARY_ROWS
    }

    rows = []
    for dataset, headers in RESEARCH_HEADERS.items():
        file_name = f"{dataset}.csv"
        for field in headers:
            override = overrides.get((file_name, field))
            if override:
                field_type, description, source_table, layer, allowed_labels = override
            else:
                field_type = _infer_dictionary_type(field)
                description = field.replace("_", " ").capitalize() + "."
                source_table = _infer_source_table(dataset, field)
                layer = _infer_layer(dataset)
                allowed_labels = _allowed_labels(field)
            rows.append(
                (
                    file_name,
                    field,
                    field_type,
                    description,
                    source_table,
                    layer,
                    allowed_labels,
                )
            )
    return rows


def _compose_query(base_query, clauses, order_by):
    return base_query + _where(clauses) + order_by


def _research_query(dataset, filters):
    params = {}
    if dataset == "channels":
        clauses = _channel_filter_clauses(filters, params)
        base_query = """
            SELECT
                c.id AS channel_id,
                c.youtube_channel_id,
                c.channel_username,
                c.channel_name,
                c.handle,
                c.canonical_url,
                c.subscriber_count,
                c.view_count,
                c.video_count,
                c.country,
                c.default_language,
                c.published_at,
                c.last_collected_at,
                cl.primary_niche,
                cl.primary_format,
                cl.faceless_status,
                cl.sponsor_fit,
                cl.policy_risk,
                cl.production_complexity,
                cl.reviewer,
                cl.reviewed_at,
                cl.notes
            FROM channels c
            LEFT JOIN channel_labels cl ON cl.channel_id = c.id
            """
        return _compose_query(base_query, clauses, " ORDER BY c.id"), params

    if dataset == "videos":
        clauses = _video_filter_clauses(filters, params)
        base_query = """
            SELECT
                v.id AS video_id,
                v.youtube_video_id,
                v.youtube_channel_id,
                c.channel_username,
                c.channel_name,
                v.title,
                v.description_excerpt,
                v.published_at,
                v.duration_seconds,
                v.category_id,
                v.default_language,
                v.caption_available,
                v.thumbnail_url,
                v.thumbnail_quality,
                v.thumbnail_cached_path,
                v.thumbnail_phash,
                v.transcript_status,
                v.views,
                v.likes,
                v.comments,
                v.last_collected_at,
                vl.niche,
                vl.format,
                vl.faceless_status,
                vl.visual_style,
                vl.packaging_pattern,
                vl.title_pattern,
                vl.thumbnail_pattern,
                vl.viewer_promise,
                vl.curiosity_type,
                vl.clarity_score,
                vl.specificity_score,
                vl.honesty_score,
                vl.visual_readability_score,
                vl.differentiation_score,
                vl.topic_type,
                vl.production_complexity,
                vl.policy_risk,
                vl.review_status,
                vl.label_confidence
            FROM videos v
            LEFT JOIN channels c ON c.id = v.channel_id
            LEFT JOIN video_labels vl ON vl.video_id = v.id
            """
        return _compose_query(base_query, clauses, " ORDER BY v.id"), params

    if dataset == "manual_labels":
        clauses = _manual_label_filter_clauses(filters, params)
        base_query = """
            SELECT * FROM (
                SELECT
                    'video' AS entity_type,
                    v.id AS entity_id,
                    v.youtube_video_id AS youtube_id,
                    v.title AS display_name,
                    c.channel_username,
                    vl.niche AS niche,
                    vl.format AS format,
                    vl.faceless_status,
                    vl.ai_use_visible,
                    vl.visual_style,
                    vl.packaging_pattern,
                    vl.title_pattern,
                    vl.thumbnail_pattern,
                    vl.viewer_promise,
                    vl.curiosity_type,
                    vl.clarity_score,
                    vl.specificity_score,
                    vl.honesty_score,
                    vl.visual_readability_score,
                    vl.differentiation_score,
                    vl.topic_type,
                    vl.production_complexity,
                    vl.policy_risk,
                    vl.monetization_signals,
                    NULL AS sponsor_fit,
                    vl.reviewer,
                    vl.review_status,
                    vl.reviewed_at,
                    vl.label_confidence,
                    vl.notes
                FROM video_labels vl
                JOIN videos v ON v.id = vl.video_id
                LEFT JOIN channels c ON c.id = v.channel_id
                UNION ALL
                SELECT
                    'channel' AS entity_type,
                    c.id AS entity_id,
                    c.youtube_channel_id AS youtube_id,
                    c.channel_name AS display_name,
                    c.channel_username,
                    cl.primary_niche AS niche,
                    cl.primary_format AS format,
                    cl.faceless_status,
                    NULL AS ai_use_visible,
                    NULL AS visual_style,
                    NULL AS packaging_pattern,
                    NULL AS title_pattern,
                    NULL AS thumbnail_pattern,
                    NULL AS viewer_promise,
                    NULL AS curiosity_type,
                    NULL AS clarity_score,
                    NULL AS specificity_score,
                    NULL AS honesty_score,
                    NULL AS visual_readability_score,
                    NULL AS differentiation_score,
                    NULL AS topic_type,
                    cl.production_complexity,
                    cl.policy_risk,
                    NULL AS monetization_signals,
                    cl.sponsor_fit,
                    cl.reviewer,
                    NULL AS review_status,
                    cl.reviewed_at,
                    NULL AS label_confidence,
                    cl.notes
                FROM channel_labels cl
                JOIN channels c ON c.id = cl.channel_id
            ) labels
            """
        return (
            _compose_query(base_query, clauses, " ORDER BY entity_type, entity_id"),
            params,
        )

    if dataset == "snapshots":
        clauses = _snapshot_filter_clauses(filters, params)
        base_query = """
            SELECT * FROM (
                SELECT
                    'video' AS entity_type,
                    vs.id AS snapshot_id,
                    v.id AS entity_id,
                    v.youtube_video_id AS youtube_id,
                    v.title AS display_name,
                    c.channel_username,
                    vs.snapshot_at,
                    vs.view_count,
                    vs.like_count,
                    vs.comment_count,
                    vs.subscriber_count_at_snapshot AS subscriber_count,
                    NULL AS video_count,
                    vs.collection_run_id
                FROM video_snapshots vs
                JOIN videos v ON v.id = vs.video_id
                LEFT JOIN channels c ON c.id = v.channel_id
                UNION ALL
                SELECT
                    'channel' AS entity_type,
                    cs.id AS snapshot_id,
                    c.id AS entity_id,
                    c.youtube_channel_id AS youtube_id,
                    c.channel_name AS display_name,
                    c.channel_username,
                    cs.snapshot_at,
                    cs.view_count,
                    NULL AS like_count,
                    NULL AS comment_count,
                    cs.subscriber_count,
                    cs.video_count,
                    cs.collection_run_id
                FROM channel_snapshots cs
                JOIN channels c ON c.id = cs.channel_id
            ) snapshots
            """
        return (
            _compose_query(
                base_query, clauses, " ORDER BY snapshot_at, entity_type, snapshot_id"
            ),
            params,
        )

    if dataset == "derived_metrics":
        clauses = _derived_filter_clauses(filters, params)
        base_query = """
            SELECT
                vdm.id,
                vdm.video_id,
                v.youtube_video_id,
                v.title,
                c.channel_username,
                c.youtube_channel_id,
                vdm.snapshot_at,
                vdm.age_days,
                vdm.views_per_day,
                vdm.views_per_subscriber,
                vdm.channel_recent_median_views,
                vdm.relative_performance,
                vdm.duration_bucket,
                vdm.performance_tier,
                vdm.outlier_flag,
                vdm.like_rate,
                vdm.comment_rate,
                vdm.engagement_rate,
                vdm.computed_at,
                vdm.algorithm_version
            FROM video_derived_metrics vdm
            JOIN videos v ON v.id = vdm.video_id
            LEFT JOIN channels c ON c.id = v.channel_id
            LEFT JOIN video_labels vl ON vl.video_id = v.id
            """
        return (
            _compose_query(base_query, clauses, " ORDER BY vdm.snapshot_at, vdm.id"),
            params,
        )

    if dataset == "collection_runs":
        clauses = _collection_run_filter_clauses(filters, params)
        base_query = """
            SELECT
                id,
                run_type,
                status,
                input_type,
                input_value,
                requested_limit,
                started_at,
                completed_at,
                quota_estimate,
                items_found,
                items_saved,
                items_failed,
                error_summary,
                created_by
            FROM collection_runs
            """
        return _compose_query(base_query, clauses, " ORDER BY started_at, id"), params

    if dataset == "content_theses":
        base_query = """
            SELECT
                id,
                thesis_id,
                title,
                target_viewer,
                viewer_promise,
                format,
                topic_universe,
                production_edge,
                packaging_edge,
                monetization_path,
                policy_risk_argument,
                status,
                notes,
                created_at,
                updated_at
            FROM content_theses
            """
        return _compose_query(base_query, [], " ORDER BY thesis_id"), params

    if dataset == "thesis_evidence":
        base_query = """
            SELECT
                te.id,
                te.thesis_id,
                ct.thesis_id AS thesis_code,
                te.evidence_type,
                te.channel_id,
                c.channel_username,
                te.video_id,
                v.youtube_video_id,
                te.source_url,
                te.note,
                te.confidence,
                te.created_at
            FROM thesis_evidence te
            JOIN content_theses ct ON ct.id = te.thesis_id
            LEFT JOIN channels c ON c.id = te.channel_id
            LEFT JOIN videos v ON v.id = te.video_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, te.id"), params

    if dataset == "thesis_topics":
        base_query = """
            SELECT
                tt.id,
                tt.thesis_id,
                ct.thesis_id AS thesis_code,
                tt.topic,
                tt.title_angle,
                tt.demand_evidence,
                tt.source_availability,
                tt.production_complexity,
                tt.packaging_potential,
                tt.status,
                tt.created_at
            FROM thesis_topics tt
            JOIN content_theses ct ON ct.id = tt.thesis_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, tt.id"), params

    if dataset == "thesis_scores":
        base_query = """
            SELECT
                ts.id,
                ts.thesis_id,
                ct.thesis_id AS thesis_code,
                ts.factor,
                ts.weight,
                ts.score,
                ts.weighted_score,
                ts.evidence,
                ts.confidence,
                ts.created_at
            FROM thesis_scores ts
            JOIN content_theses ct ON ct.id = ts.thesis_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, ts.id"), params

    if dataset == "red_team_reviews":
        base_query = """
            SELECT
                rtr.id,
                rtr.thesis_id,
                ct.thesis_id AS thesis_code,
                rtr.reviewer,
                rtr.decision_under_review,
                rtr.core_objections,
                rtr.competitor_challenges,
                rtr.failure_premortem,
                rtr.early_warning_signs,
                rtr.preventive_actions,
                rtr.kill_criteria,
                rtr.decision,
                rtr.decision_rationale,
                rtr.reviewed_at
            FROM red_team_reviews rtr
            JOIN content_theses ct ON ct.id = rtr.thesis_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, rtr.id"), params

    if dataset == "thesis_monetization_maps":
        base_query = """
            SELECT
                tmm.id,
                tmm.thesis_id,
                ct.thesis_id AS thesis_code,
                tmm.revenue_paths,
                tmm.primary_revenue_path,
                tmm.secondary_revenue_path,
                tmm.conservative_ad_rpm,
                tmm.base_ad_rpm,
                tmm.upside_ad_rpm,
                tmm.sponsor_rpm_equivalent,
                tmm.affiliate_rpm_equivalent,
                tmm.membership_rpm_equivalent,
                tmm.product_rpm_equivalent,
                tmm.break_even_view_count,
                tmm.meaningful_income_view_count,
                tmm.assumptions,
                tmm.main_monetization_risk,
                tmm.created_at,
                tmm.updated_at
            FROM thesis_monetization_maps tmm
            JOIN content_theses ct ON ct.id = tmm.thesis_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, tmm.id"), params

    if dataset == "sponsor_evidence":
        base_query = """
            SELECT
                se.id,
                se.thesis_id,
                ct.thesis_id AS thesis_code,
                se.sponsor_category,
                se.observed_sponsor,
                se.competitor_channel_id,
                c.channel_username AS competitor_channel_username,
                se.video_url,
                se.date_observed,
                se.niche_fit,
                se.brand_safety_notes,
                se.created_at
            FROM sponsor_evidence se
            JOIN content_theses ct ON ct.id = se.thesis_id
            LEFT JOIN channels c ON c.id = se.competitor_channel_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, se.id"), params

    if dataset == "affiliate_product_evidence":
        base_query = """
            SELECT
                ape.id,
                ape.thesis_id,
                ct.thesis_id AS thesis_code,
                ape.product_category,
                ape.program_source,
                ape.estimated_fit,
                ape.audience_intent,
                ape.compliance_disclosure_concerns,
                ape.created_at
            FROM affiliate_product_evidence ape
            JOIN content_theses ct ON ct.id = ape.thesis_id
            """
        return _compose_query(base_query, [], " ORDER BY ct.thesis_id, ape.id"), params

    if dataset == "assets":
        base_query = """
            SELECT
                id,
                asset_id,
                asset_type,
                source_url_path,
                creator_licensor,
                license_terms,
                monetized_youtube_allowed,
                attribution_required,
                proof_saved,
                high_risk_flag,
                high_risk_reason,
                notes,
                created_at,
                updated_at
            FROM assets
            """
        return _compose_query(base_query, [], " ORDER BY asset_id"), params

    if dataset == "video_assets":
        base_query = """
            SELECT
                va.id,
                va.video_id,
                v.youtube_video_id,
                v.title,
                va.asset_id AS asset_row_id,
                a.asset_id,
                a.asset_type,
                va.intended_use,
                va.attribution_text,
                va.rights_decision,
                va.created_at
            FROM video_assets va
            JOIN videos v ON v.id = va.video_id
            JOIN assets a ON a.id = va.asset_id
            """
        return _compose_query(base_query, [], " ORDER BY v.id, va.id"), params

    if dataset == "video_rights_checklists":
        base_query = """
            SELECT
                vrc.id,
                vrc.video_id,
                v.youtube_video_id,
                v.title,
                vrc.every_asset_has_row,
                vrc.unclear_assets_blocked,
                vrc.attribution_captured,
                vrc.synthetic_altered_status,
                vrc.no_terms_prohibit_monetization,
                vrc.ready_for_upload,
                vrc.reviewer,
                vrc.reviewed_at,
                vrc.notes
            FROM video_rights_checklists vrc
            JOIN videos v ON v.id = vrc.video_id
            """
        return _compose_query(base_query, [], " ORDER BY v.id, vrc.id"), params

    if dataset == "video_disclosures":
        base_query = """
            SELECT
                vd.id,
                vd.video_id,
                v.youtube_video_id,
                v.title,
                vd.sponsor_disclosure,
                vd.affiliate_disclosure,
                vd.altered_synthetic_disclosure,
                vd.music_license_attribution,
                vd.disclosure_notes,
                vd.created_at
            FROM video_disclosures vd
            JOIN videos v ON v.id = vd.video_id
            """
        return _compose_query(base_query, [], " ORDER BY v.id, vd.id"), params

    if dataset == "owned_analytics_credentials":
        base_query = """
            SELECT
                oac.id,
                oac.channel_id,
                c.youtube_channel_id,
                c.channel_username,
                oac.google_account_email,
                oac.scopes,
                oac.token_secret_ref,
                oac.status,
                oac.created_at,
                oac.revoked_at,
                oac.notes
            FROM owned_analytics_credentials oac
            LEFT JOIN channels c ON c.id = oac.channel_id
            """
        return (
            _compose_query(base_query, [], " ORDER BY oac.created_at, oac.id"),
            params,
        )

    if dataset == "owned_video_analytics":
        base_query = """
            SELECT
                ova.id,
                ova.video_id,
                v.youtube_video_id,
                v.title,
                ova.date,
                ova.views,
                ova.impressions,
                ova.impression_ctr,
                ova.average_view_duration_seconds,
                ova.average_view_percentage,
                ova.watch_time_minutes,
                ova.subscribers_gained,
                ova.estimated_revenue,
                ova.traffic_source_type,
                ova.source,
                ova.created_at
            FROM owned_video_analytics ova
            JOIN videos v ON v.id = ova.video_id
            """
        return _compose_query(base_query, [], " ORDER BY ova.date, ova.id"), params

    if dataset == "retention_diagnostics":
        base_query = """
            SELECT
                rd.id,
                rd.video_id,
                v.youtube_video_id,
                v.title,
                rd.report_date,
                rd.ctr,
                rd.average_view_duration_seconds,
                rd.average_view_percentage,
                rd.impressions,
                rd.dominant_traffic_source,
                rd.retention_pattern,
                rd.likely_cause,
                rd.evidence,
                rd.next_change,
                rd.notes,
                rd.created_at
            FROM retention_diagnostics rd
            JOIN videos v ON v.id = rd.video_id
            """
        return _compose_query(base_query, [], " ORDER BY rd.report_date, rd.id"), params

    if dataset == "experiments":
        base_query = """
            SELECT
                e.id,
                e.video_id,
                v.youtube_video_id,
                v.title,
                e.hypothesis,
                e.variable_tested,
                e.title AS experiment_title,
                e.thumbnail_variant,
                e.publish_date,
                e.success_metric,
                e.production_hours,
                e.production_cost,
                e.decision,
                e.notes,
                e.created_at
            FROM experiments e
            LEFT JOIN videos v ON v.id = e.video_id
            """
        return _compose_query(base_query, [], " ORDER BY e.created_at, e.id"), params

    if dataset == "experiment_checkpoints":
        base_query = """
            SELECT
                ec.id,
                ec.experiment_id,
                e.video_id,
                v.youtube_video_id,
                ec.checkpoint,
                ec.views,
                ec.impressions,
                ec.impression_ctr,
                ec.average_view_duration_seconds,
                ec.average_view_percentage,
                ec.watch_time_minutes,
                ec.subscribers_gained,
                ec.main_traffic_source,
                ec.notes,
                ec.recorded_at
            FROM experiment_checkpoints ec
            JOIN experiments e ON e.id = ec.experiment_id
            LEFT JOIN videos v ON v.id = e.video_id
            """
        return _compose_query(base_query, [], " ORDER BY ec.recorded_at, ec.id"), params

    raise ValueError(f"Unsupported research dataset: {dataset}")


def _video_filter_clauses(filters, params):
    clauses = []
    _add_label_filters(clauses, params, filters, "vl.niche", "vl.format")
    _add_channel_filter(clauses, params, filters, "c")
    _add_date_filter(clauses, params, filters, "COALESCE(v.published_at, v.created_at)")
    if filters.get("collection_run_id") is not None:
        params["collection_run_id"] = filters["collection_run_id"]
        clauses.append(
            "EXISTS (SELECT 1 FROM video_snapshots vfs "
            "WHERE vfs.video_id = v.id AND vfs.collection_run_id = :collection_run_id)"
        )
    if filters.get("labeled") is True:
        clauses.append("vl.id IS NOT NULL")
    elif filters.get("labeled") is False:
        clauses.append("vl.id IS NULL")
    if filters.get("outlier_flag") is not None:
        params["outlier_flag"] = filters["outlier_flag"]
        clauses.append(
            "EXISTS (SELECT 1 FROM video_derived_metrics vdmf "
            "WHERE vdmf.video_id = v.id AND vdmf.outlier_flag = :outlier_flag)"
        )
    return clauses


def _channel_filter_clauses(filters, params):
    clauses = []
    _add_label_filters(
        clauses, params, filters, "cl.primary_niche", "cl.primary_format"
    )
    _add_channel_filter(clauses, params, filters, "c")
    _add_date_filter(clauses, params, filters, "COALESCE(c.published_at, c.created_at)")
    if filters.get("collection_run_id") is not None:
        params["collection_run_id"] = filters["collection_run_id"]
        clauses.append(
            "EXISTS (SELECT 1 FROM channel_snapshots cfs "
            "WHERE cfs.channel_id = c.id AND cfs.collection_run_id = :collection_run_id)"
        )
    if filters.get("labeled") is True:
        clauses.append("cl.id IS NOT NULL")
    elif filters.get("labeled") is False:
        clauses.append("cl.id IS NULL")
    if filters.get("outlier_flag") is not None:
        params["outlier_flag"] = filters["outlier_flag"]
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM videos vf "
            "JOIN video_derived_metrics vdmf ON vdmf.video_id = vf.id "
            "WHERE vf.channel_id = c.id AND vdmf.outlier_flag = :outlier_flag)"
        )
    return clauses


def _manual_label_filter_clauses(filters, params):
    clauses = []
    if filters.get("niche"):
        params["niche"] = filters["niche"]
        clauses.append("labels.niche = :niche")
    if filters.get("format"):
        params["format"] = filters["format"]
        clauses.append("labels.format = :format")
    if filters.get("channel"):
        params["channel"] = filters["channel"]
        clauses.append("labels.channel_username = :channel")
    _add_date_filter(clauses, params, filters, "labels.reviewed_at")
    return clauses


def _snapshot_filter_clauses(filters, params):
    clauses = []
    if filters.get("channel"):
        params["channel"] = filters["channel"]
        clauses.append("snapshots.channel_username = :channel")
    _add_date_filter(clauses, params, filters, "snapshots.snapshot_at")
    if filters.get("collection_run_id") is not None:
        params["collection_run_id"] = filters["collection_run_id"]
        clauses.append("snapshots.collection_run_id = :collection_run_id")
    return clauses


def _derived_filter_clauses(filters, params):
    clauses = []
    _add_label_filters(clauses, params, filters, "vl.niche", "vl.format")
    _add_channel_filter(clauses, params, filters, "c")
    _add_date_filter(clauses, params, filters, "vdm.snapshot_at")
    if filters.get("outlier_flag") is not None:
        params["outlier_flag"] = filters["outlier_flag"]
        clauses.append("vdm.outlier_flag = :outlier_flag")
    if filters.get("labeled") is True:
        clauses.append("vl.id IS NOT NULL")
    elif filters.get("labeled") is False:
        clauses.append("vl.id IS NULL")
    return clauses


def _collection_run_filter_clauses(filters, params):
    clauses = []
    if filters.get("collection_run_id") is not None:
        params["collection_run_id"] = filters["collection_run_id"]
        clauses.append("id = :collection_run_id")
    if filters.get("channel"):
        params["channel"] = filters["channel"]
        clauses.append("input_value = :channel")
    _add_date_filter(clauses, params, filters, "started_at")
    return clauses


def _add_label_filters(clauses, params, filters, niche_column, format_column):
    if filters.get("niche"):
        params["niche"] = filters["niche"]
        clauses.append(f"{niche_column} = :niche")
    if filters.get("format"):
        params["format"] = filters["format"]
        clauses.append(f"{format_column} = :format")


def _add_channel_filter(clauses, params, filters, channel_alias):
    if not filters.get("channel"):
        return
    params["channel"] = filters["channel"]
    clauses.append(
        f"({channel_alias}.channel_username = :channel "
        f"OR {channel_alias}.youtube_channel_id = :channel "
        f"OR CAST({channel_alias}.id AS TEXT) = :channel)"
    )


def _add_date_filter(clauses, params, filters, expression):
    if filters.get("date_from"):
        params["date_from"] = filters["date_from"]
        clauses.append(f"{expression} >= :date_from")
    if filters.get("date_to"):
        params["date_to"] = filters["date_to"]
        clauses.append(f"{expression} <= :date_to")


def _where(clauses):
    return " WHERE " + " AND ".join(clauses) if clauses else ""


def _rows_to_csv(rows, headers):
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    columns = list(rows[0].keys()) if rows else headers
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return buffer.getvalue()


def _serialize_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _blank_to_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value):
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "labeled"}:
        return True
    if normalized in {"0", "false", "no", "off", "unlabeled"}:
        return False
    return None


def _markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def _infer_dictionary_type(field):
    if field in {"youtube_video_id", "youtube_channel_id", "youtube_id"}:
        return "string"
    if field.endswith("_id") or field in {
        "id",
        "views",
        "likes",
        "comments",
        "subscriber_count",
        "view_count",
        "video_count",
        "like_count",
        "comment_count",
        "duration_seconds",
        "requested_limit",
        "quota_estimate",
        "items_found",
        "items_saved",
        "items_failed",
        "clarity_score",
        "specificity_score",
        "honesty_score",
        "visual_readability_score",
        "differentiation_score",
        "weight",
        "score",
        "weighted_score",
        "break_even_view_count",
        "meaningful_income_view_count",
        "impressions",
        "subscribers_gained",
    }:
        return "integer"
    if field.endswith("_at") or field in {"published_at", "snapshot_at", "date"}:
        return "datetime"
    if field in {
        "label_confidence",
        "age_days",
        "views_per_day",
        "views_per_subscriber",
        "channel_recent_median_views",
        "relative_performance",
        "like_rate",
        "comment_rate",
        "engagement_rate",
        "conservative_ad_rpm",
        "base_ad_rpm",
        "upside_ad_rpm",
        "sponsor_rpm_equivalent",
        "affiliate_rpm_equivalent",
        "membership_rpm_equivalent",
        "product_rpm_equivalent",
        "impression_ctr",
        "ctr",
        "average_view_duration_seconds",
        "average_view_percentage",
        "watch_time_minutes",
        "estimated_revenue",
        "production_hours",
        "production_cost",
    }:
        return "float"
    if field in {
        "caption_available",
        "outlier_flag",
        "attribution_required",
        "proof_saved",
        "high_risk_flag",
        "every_asset_has_row",
        "unclear_assets_blocked",
        "attribution_captured",
        "no_terms_prohibit_monetization",
        "ready_for_upload",
    }:
        return "boolean"
    return "string"


def _infer_source_table(dataset, field):
    if dataset == "manual_labels":
        return "video_labels/channel_labels"
    if dataset == "snapshots":
        return "video_snapshots/channel_snapshots"
    if dataset == "derived_metrics":
        return "video_derived_metrics"
    if dataset == "collection_runs":
        return "collection_runs"
    if dataset in {
        "content_theses",
        "thesis_evidence",
        "thesis_topics",
        "thesis_scores",
        "red_team_reviews",
        "thesis_monetization_maps",
        "sponsor_evidence",
        "affiliate_product_evidence",
        "assets",
        "video_assets",
        "video_rights_checklists",
        "video_disclosures",
        "owned_analytics_credentials",
        "owned_video_analytics",
        "retention_diagnostics",
        "experiments",
        "experiment_checkpoints",
    }:
        return dataset
    if dataset == "channels" and field in {
        "primary_niche",
        "primary_format",
        "faceless_status",
        "sponsor_fit",
        "policy_risk",
        "production_complexity",
        "reviewer",
        "reviewed_at",
        "notes",
    }:
        return "channel_labels"
    if dataset == "videos" and field in {
        "niche",
        "format",
        "faceless_status",
        "visual_style",
        "packaging_pattern",
        "title_pattern",
        "thumbnail_pattern",
        "viewer_promise",
        "curiosity_type",
        "clarity_score",
        "specificity_score",
        "honesty_score",
        "visual_readability_score",
        "differentiation_score",
        "topic_type",
        "production_complexity",
        "policy_risk",
        "review_status",
        "label_confidence",
    }:
        return "video_labels"
    return dataset


def _infer_layer(dataset):
    return {
        "manual_labels": "manual",
        "snapshots": "raw",
        "derived_metrics": "derived",
        "collection_runs": "raw",
        "owned_analytics_credentials": "auth_metadata",
        "owned_video_analytics": "owned_private",
        "retention_diagnostics": "owned_private",
        "experiments": "owned_private",
        "experiment_checkpoints": "owned_private",
    }.get(dataset, "normalized")


def _allowed_labels(field):
    return {
        "faceless_status": "faceless|mixed|host-led|unknown",
        "policy_risk": "low|medium|high|unknown",
        "review_status": "pending|reviewed|needs_review",
        "outlier_flag": "true|false",
        "caption_available": "true|false",
        "attribution_required": "true|false",
        "proof_saved": "true|false",
        "high_risk_flag": "true|false",
        "every_asset_has_row": "true|false",
        "unclear_assets_blocked": "true|false",
        "attribution_captured": "true|false",
        "no_terms_prohibit_monetization": "true|false",
        "ready_for_upload": "true|false",
        "performance_tier": "breakout|outlier|normal|underperformer|unknown",
        "status": "idea|research|pilot|reject|launch",
        "evidence_type": "outlier_video|competitor_channel|comment_theme|search_trend|sponsor_density|source_availability|forum_question|manual_note",
        "decision": "pending|continue|pivot|stop|scale|proceed_to_pilot|research_more|revise_thesis|reject",
        "checkpoint": "24h|7d|30d",
        "retention_pattern": "early_cliff|slow_bleed|mid_video_drop|spike_replay|high_ctr_low_retention|low_ctr_high_retention|low_impressions_good_response|good_search_weak_browse|unknown",
        "primary_revenue_path": "watch_page_ads|sponsors|affiliates|memberships|patreon|newsletter|digital_products|consulting_services|licensing",
        "secondary_revenue_path": "watch_page_ads|sponsors|affiliates|memberships|patreon|newsletter|digital_products|consulting_services|licensing",
        "title_pattern": "mystery|reversal|consequence|transformation|hidden_system|timeline|comparison|specific_question|list_with_angle|strong_claim|other",
        "thumbnail_pattern": "single_object_high_contrast|before_after_contrast|map_timeline_diagram|recognizable_artifact_or_brand|human_face_substitute|text_free_curiosity|short_text_label|red_circle_arrow|split_screen_conflict|scale_contrast|other",
        "curiosity_type": "none|mystery|stakes|contradiction|transformation|comparison|hidden_system|specific_question|other",
    }.get(field, "")

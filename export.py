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
    }:
        return "integer"
    if field.endswith("_at") or field in {"published_at", "snapshot_at"}:
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
    }:
        return "float"
    if field in {"caption_available", "outlier_flag"}:
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
    }.get(dataset, "normalized")


def _allowed_labels(field):
    return {
        "faceless_status": "faceless|mixed|host-led|unknown",
        "policy_risk": "low|medium|high|unknown",
        "review_status": "pending|reviewed|needs_review",
        "outlier_flag": "true|false",
        "caption_available": "true|false",
        "performance_tier": "breakout|outlier|normal|underperformer|unknown",
    }.get(field, "")

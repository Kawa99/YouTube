import os
import logging

from crud import save_video
from export import (
    build_research_zip_file,
    build_xlsx_export_file,
    normalize_export_filters,
    stream_all_tables_csv,
    stream_research_jsonl,
)
from flask import (
    Response,
    after_this_request,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    stream_with_context,
    url_for,
)
from label_vocabularies import LABEL_VOCABULARIES
from labeling import (
    LabelValidationError,
    bulk_apply_video_label,
    next_unlabeled_video_id,
    save_video_label,
)
from metrics import compute_derived_metrics, market_analysis_summary
from packaging_lab import packaging_lab_summary, save_packaging_experiment
from models import Channel, ChannelHistory, Video, VideoHistory, VideoLabel, db
from pydantic import ValidationError
from schemas import VideoCreateSchema
from sqlalchemy import case, func
from tasks import RedisError, enqueue_channel_job, get_channel_job
from youtube_api import (
    YOUTUBE_API_KEY,
    extract_video_id,
    get_channel_id_from_url,
    get_video_data,
    is_valid_youtube_channel_url,
    is_valid_youtube_video_url,
)

logger = logging.getLogger(__name__)

MAX_API_PAGE_SIZE = 200


def _parse_positive_int(value, default, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    if parsed < 1:
        parsed = default

    if maximum is not None:
        parsed = min(parsed, maximum)

    return parsed


def _normalize_sort_direction(value):
    return "asc" if str(value).lower() == "asc" else "desc"


def _build_order_clause(
    column_map, sort_column, sort_direction, default_column, default_direction="desc"
):
    if sort_column in column_map:
        target_column = column_map[sort_column]
        direction = sort_direction
    else:
        target_column = default_column
        direction = default_direction

    return target_column.asc() if direction == "asc" else target_column.desc()


def _pagination_metadata(page_obj):
    return {
        "total_items": page_obj.total,
        "total_pages": page_obj.pages,
        "current_page": page_obj.page,
        "per_page": page_obj.per_page,
        "has_next": page_obj.has_next,
        "has_prev": page_obj.has_prev,
        "next_page": page_obj.next_num if page_obj.has_next else None,
        "prev_page": page_obj.prev_num if page_obj.has_prev else None,
    }


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_percentage_rate(numerator, denominator):
    try:
        denominator_value = _safe_float(denominator)
        if denominator_value == 0:
            return 0.0
        return round((_safe_float(numerator) / denominator_value) * 100, 2)
    except (ZeroDivisionError, TypeError, ValueError):
        return 0.0


def register_routes(app, limiter):
    """Register application routes."""

    @app.route("/", methods=["GET", "POST"])
    @limiter.limit("60 per minute")
    def index():
        video_data = None

        if request.method == "POST":
            if not YOUTUBE_API_KEY:
                flash(
                    "YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.",
                    "danger",
                )
                return render_template("index.html", data=None)

            video_url = request.form.get("video_url", "").strip()
            if not is_valid_youtube_video_url(video_url):
                flash(
                    "URL must be a valid youtube.com or youtu.be video link.", "warning"
                )
                return render_template("index.html", data=None)

            video_id = extract_video_id(video_url)
            if not video_id:
                flash(
                    "Invalid YouTube URL. Please paste a valid video link.", "warning"
                )
                return render_template("index.html", data=None)

            video_data = get_video_data(video_id)
            if not video_data:
                flash(
                    "Could not fetch video data. Check your API key/quota and try again.",
                    "warning",
                )
            else:
                likes = _safe_float(video_data.get("likes"))
                comments = _safe_float(video_data.get("comments"))
                views = video_data.get("views")
                video_data["like_rate"] = _safe_percentage_rate(likes, views)
                video_data["comment_rate"] = _safe_percentage_rate(comments, views)
                video_data["engagement_rate"] = _safe_percentage_rate(
                    likes + comments, views
                )

        return render_template("index.html", data=video_data)

    @app.route("/channel", methods=["GET", "POST"])
    @limiter.limit("30 per minute")
    def channel_scraper():
        if request.method == "POST":
            if not YOUTUBE_API_KEY:
                flash(
                    "YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.",
                    "danger",
                )
                return render_template("channel.html", job_id=None, job=None)

            channel_url = request.form.get("channel_url", "").strip()
            if not is_valid_youtube_channel_url(channel_url):
                flash("Channel URL must use youtube.com.", "warning")
                return render_template("channel.html", job_id=None, job=None)

            max_videos_raw = request.form.get("max_videos", "50")

            try:
                max_videos = int(max_videos_raw)
            except (TypeError, ValueError):
                flash("Maximum videos must be a valid integer.", "warning")
                return render_template("channel.html", job_id=None, job=None)

            max_videos = max(1, min(max_videos, 1000))
            channel_id = get_channel_id_from_url(channel_url)

            if not channel_id:
                flash(
                    "Could not extract channel ID from URL. Please check the URL format.",
                    "danger",
                )
                return render_template("channel.html", job_id=None, job=None)

            try:
                job_id = enqueue_channel_job(channel_id, max_videos)
            except RedisError:
                flash(
                    "Background queue is unavailable. Ensure Redis and the RQ worker are running.",
                    "danger",
                )
                return render_template("channel.html", job_id=None, job=None)

            flash("Channel scrape job queued. Progress is shown below.", "info")
            return redirect(url_for("channel_scraper", job_id=job_id))

        job_id = request.args.get("job_id")
        job = get_channel_job(job_id) if job_id else None

        if job_id and not job:
            flash("The requested job was not found.", "warning")
            job_id = None

        return render_template("channel.html", job_id=job_id, job=job)

    @app.route("/process_channel/<channel_id>/<int:max_videos>")
    def process_channel(channel_id, max_videos):
        """Backward-compatible route: now enqueues background job instead of blocking."""
        if not YOUTUBE_API_KEY:
            flash(
                "YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.",
                "danger",
            )
            return redirect(url_for("channel_scraper"))

        max_videos = max(1, min(max_videos, 1000))
        try:
            job_id = enqueue_channel_job(channel_id, max_videos)
        except RedisError:
            flash(
                "Background queue is unavailable. Ensure Redis and the RQ worker are running.",
                "danger",
            )
            return redirect(url_for("channel_scraper"))

        flash("Channel scrape job queued. Progress is shown below.", "info")
        return redirect(url_for("channel_scraper", job_id=job_id))

    @app.route("/status/<job_id>")
    @app.route("/api/channel-jobs/<job_id>")
    def get_channel_job_status(job_id):
        job = get_channel_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job)

    @app.route("/save", methods=["POST"])
    def save():
        try:
            validated_data = VideoCreateSchema.model_validate(request.form.to_dict())
        except ValidationError as error:
            return (
                jsonify(
                    {"error": "Invalid request payload.", "details": error.errors()}
                ),
                400,
            )

        try:
            result = save_video(validated_data.model_dump())
            if result.get("created"):
                flash("Video data saved successfully!", "success")
            else:
                flash("Video already exists. Stored record was refreshed.", "info")
        except Exception as e:
            logger.exception("An error occurred: %s", str(e))
            flash(f"Error saving video: {str(e)}", "danger")

        return redirect(url_for("index"))

    @app.route("/data")
    def data_viewer():
        return render_template("data_viewer.html")

    @app.route("/analysis", methods=["GET"])
    def market_analysis():
        return render_template(
            "market_analysis.html", analysis=market_analysis_summary()
        )

    @app.route("/analysis/compute", methods=["POST"])
    def compute_derived_metrics_route():
        summary = compute_derived_metrics()
        flash(
            "Derived metrics computed for "
            f"{summary['videos_computed']} videos and "
            f"{summary['channels_computed']} channels.",
            "success",
        )
        return redirect(url_for("market_analysis"))

    @app.route("/packaging", methods=["GET"])
    def packaging_lab():
        niche = request.args.get("niche", "").strip() or None
        return render_template(
            "packaging_lab.html",
            lab=packaging_lab_summary(niche=niche),
            vocabularies=LABEL_VOCABULARIES,
        )

    @app.route("/packaging/experiments", methods=["POST"])
    def create_packaging_experiment_route():
        try:
            experiment = save_packaging_experiment(request.form)
        except ValueError as error:
            flash(str(error), "warning")
            return redirect(url_for("packaging_lab"))

        flash(f"Packaging experiment #{experiment.id} saved.", "success")
        return redirect(url_for("packaging_lab"))

    @app.route("/labeling", methods=["GET"])
    def labeling_queue():
        selected_video_id = request.args.get("video_id", type=int)
        if selected_video_id is None and request.args.get("mode") == "unlabeled":
            selected_video_id = next_unlabeled_video_id()

        video = None
        if selected_video_id is not None:
            video = Video.query.get_or_404(selected_video_id)
        else:
            video = (
                Video.query.outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
                .order_by(
                    (VideoLabel.review_status == "reviewed").asc(),
                    Video.id.asc(),
                )
                .first()
            )

        queue = (
            db.session.query(Video, VideoLabel)
            .outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
            .order_by(Video.id.asc())
            .limit(100)
            .all()
        )
        counts = {
            "total": Video.query.count(),
            "reviewed": VideoLabel.query.filter_by(review_status="reviewed").count(),
            "pending": (
                Video.query.outerjoin(VideoLabel, VideoLabel.video_id == Video.id)
                .filter(
                    (VideoLabel.id.is_(None)) | (VideoLabel.review_status == "pending")
                )
                .count()
            ),
            "needs_second_review": VideoLabel.query.filter_by(
                review_status="needs_second_review"
            ).count(),
            "skipped": VideoLabel.query.filter_by(review_status="skipped").count(),
        }

        return render_template(
            "labeling.html",
            video=video,
            label=video.labels[0] if video and video.labels else None,
            queue=queue,
            counts=counts,
            vocabularies=LABEL_VOCABULARIES,
            next_unlabeled_id=next_unlabeled_video_id(video.id if video else None),
        )

    @app.route("/labeling/<int:video_id>", methods=["POST"])
    def save_video_label_route(video_id):
        action = request.form.get("action", "reviewed")
        reviewer = request.form.get("reviewer", "").strip()

        try:
            save_video_label(video_id, request.form, reviewer=reviewer, action=action)
            flash("Video label saved.", "success")
        except LabelValidationError as error:
            flash(str(error), "warning")
            return redirect(url_for("labeling_queue", video_id=video_id))

        if request.form.get("continue_next") == "1":
            next_video_id = next_unlabeled_video_id(video_id)
            if next_video_id:
                return redirect(url_for("labeling_queue", video_id=next_video_id))

        return redirect(url_for("labeling_queue", video_id=video_id))

    @app.route("/labeling/bulk", methods=["POST"])
    def bulk_label_route():
        video_ids = request.form.getlist("video_ids")
        field = request.form.get("field", "")
        value = request.form.get("value", "")
        reviewer = request.form.get("reviewer", "").strip()

        try:
            parsed_video_ids = [int(video_id) for video_id in video_ids]
            updated = bulk_apply_video_label(
                parsed_video_ids, field, value, reviewer=reviewer
            )
        except (TypeError, ValueError, LabelValidationError) as error:
            flash(str(error), "warning")
            return redirect(url_for("labeling_queue"))

        flash(f"Bulk label applied to {updated} videos.", "success")
        return redirect(url_for("labeling_queue"))

    @app.route("/api/video/<int:video_id>/history")
    def video_history_api(video_id):
        Video.query.get_or_404(video_id)
        history_rows = (
            VideoHistory.query.filter_by(video_id=video_id)
            .order_by(VideoHistory.timestamp.asc())
            .all()
        )

        timestamps = []
        views = []
        likes = []
        comments = []
        for row in history_rows:
            if row.timestamp is None:
                continue
            timestamps.append(f"{row.timestamp.isoformat()}Z")
            views.append(int(row.views or 0))
            likes.append(int(row.likes or 0))
            comments.append(int(row.comments or 0))

        return jsonify(
            {
                "timestamps": timestamps,
                "views": views,
                "likes": likes,
                "comments": comments,
            }
        )

    @app.route("/video/<int:video_id>")
    def video_detail(video_id):
        video = Video.query.get_or_404(video_id)
        return render_template("video_detail.html", video=video)

    @app.route("/video/<int:video_id>/refresh", methods=["POST"])
    @limiter.limit("15 per minute")
    def refresh_video_detail(video_id):
        video = Video.query.get_or_404(video_id)

        if not YOUTUBE_API_KEY:
            flash(
                "YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.",
                "danger",
            )
            return redirect(url_for("video_detail", video_id=video.id))

        youtube_video_id = (video.youtube_video_id or "").strip()
        if not youtube_video_id:
            flash(
                "Cannot refresh this record because its YouTube video ID is missing.",
                "warning",
            )
            return redirect(url_for("video_detail", video_id=video.id))

        latest_video_data = get_video_data(youtube_video_id)
        if not latest_video_data:
            flash(
                "Could not refresh video data. Check API quota/connectivity and try again.",
                "warning",
            )
            return redirect(url_for("video_detail", video_id=video.id))

        latest_video_data.setdefault("youtube_video_id", youtube_video_id)

        try:
            save_video(latest_video_data)
            flash("Video details refreshed. A new history point was added.", "success")
        except Exception as e:
            logger.exception("An error occurred: %s", str(e))
            flash(f"Error refreshing video data: {str(e)}", "danger")

        return redirect(url_for("video_detail", video_id=video.id))

    @app.route("/channel/<int:channel_id>")
    def channel_detail(channel_id):
        channel = Channel.query.get_or_404(channel_id)
        videos = (
            Video.query.filter_by(channel_id=channel.id)
            .order_by(Video.saved_at.desc())
            .all()
        )
        history = (
            ChannelHistory.query.filter_by(channel_id=channel.id)
            .order_by(ChannelHistory.recorded_at.desc())
            .all()
        )
        return render_template(
            "channel_detail.html",
            channel=channel,
            videos=videos,
            history=history,
        )

    @app.route("/api/channel/<int:channel_id>/toggle-tracking", methods=["POST"])
    @limiter.limit("60 per minute")
    def toggle_channel_tracking(channel_id):
        channel = Channel.query.get_or_404(channel_id)
        channel.is_tracked = not bool(channel.is_tracked)
        db.session.commit()
        return jsonify({"is_tracked": bool(channel.is_tracked)})

    @app.route("/api/data")
    def get_data_api():
        page = _parse_positive_int(request.args.get("page", 1), default=1)
        limit = _parse_positive_int(
            request.args.get("limit", 25), default=25, maximum=MAX_API_PAGE_SIZE
        )
        sort_column = request.args.get("sort_column", "saved_at")
        sort_direction = _normalize_sort_direction(
            request.args.get("sort_direction", "desc")
        )

        engagement_rate_order = case(
            (Video.views.is_(None), 0.0),
            (Video.views == 0, 0.0),
            else_=(
                (func.coalesce(Video.likes, 0) + func.coalesce(Video.comments, 0))
                * 100.0
                / Video.views
            ),
        )
        like_rate_order = case(
            (Video.views.is_(None), 0.0),
            (Video.views == 0, 0.0),
            else_=(func.coalesce(Video.likes, 0) * 100.0 / Video.views),
        )
        comment_rate_order = case(
            (Video.views.is_(None), 0.0),
            (Video.views == 0, 0.0),
            else_=(func.coalesce(Video.comments, 0) * 100.0 / Video.views),
        )
        videos_sort_columns = {
            "id": Video.id,
            "youtube_video_id": Video.youtube_video_id,
            "title": Video.title,
            "channel_username": Channel.channel_username,
            "views": Video.views,
            "likes": Video.likes,
            "comments": Video.comments,
            "like_rate": like_rate_order,
            "comment_rate": comment_rate_order,
            "engagement_rate": engagement_rate_order,
            "posted": Video.posted,
            "video_length": Video.video_length,
            "saved_at": Video.saved_at,
            "subscribers": Channel.subscribers,
        }
        videos_order = _build_order_clause(
            videos_sort_columns,
            sort_column,
            sort_direction,
            default_column=Video.saved_at,
            default_direction="desc",
        )
        videos_page = (
            db.session.query(Video, Channel.channel_username, Channel.subscribers)
            .join(Channel, Video.channel_id == Channel.id)
            .order_by(videos_order)
            .paginate(page=page, per_page=limit, error_out=False)
        )
        videos = [
            {
                "id": video.id,
                "youtube_video_id": video.youtube_video_id,
                "title": video.title,
                "channel_username": channel_username,
                "views": video.views,
                "likes": video.likes,
                "comments": video.comments,
                "like_rate": video.like_rate,
                "comment_rate": video.comment_rate,
                "engagement_rate": video.engagement_rate,
                "posted": video.posted,
                "video_length": video.video_length,
                "saved_at": video.saved_at,
                "subscribers": subscribers,
            }
            for video, channel_username, subscribers in videos_page.items
        ]

        channels_sort_columns = {
            "id": Channel.id,
            "channel_username": Channel.channel_username,
            "subscribers": Channel.subscribers,
        }
        channels_order = _build_order_clause(
            channels_sort_columns,
            sort_column,
            sort_direction,
            default_column=Channel.subscribers,
            default_direction="desc",
        )
        channels_page = Channel.query.order_by(channels_order).paginate(
            page=page, per_page=limit, error_out=False
        )
        channels = [
            {
                "id": channel.id,
                "channel_username": channel.channel_username,
                "subscribers": channel.subscribers,
            }
            for channel in channels_page.items
        ]

        history_sort_columns = {
            "id": ChannelHistory.id,
            "channel_username": Channel.channel_username,
            "previous_subscribers": ChannelHistory.previous_subscribers,
            "recorded_at": ChannelHistory.recorded_at,
        }
        history_order = _build_order_clause(
            history_sort_columns,
            sort_column,
            sort_direction,
            default_column=ChannelHistory.recorded_at,
            default_direction="desc",
        )
        history_page = (
            db.session.query(ChannelHistory, Channel.channel_username)
            .join(Channel, ChannelHistory.channel_id == Channel.id)
            .order_by(history_order)
            .paginate(page=page, per_page=limit, error_out=False)
        )
        history = [
            {
                "id": record.id,
                "channel_username": channel_username,
                "previous_subscribers": record.previous_subscribers,
                "recorded_at": record.recorded_at,
            }
            for record, channel_username in history_page.items
        ]

        return jsonify(
            {
                "query": {
                    "page": page,
                    "limit": limit,
                    "sort_column": sort_column,
                    "sort_direction": sort_direction,
                },
                "videos": {
                    "items": videos,
                    "pagination": _pagination_metadata(videos_page),
                },
                "channels": {
                    "items": channels,
                    "pagination": _pagination_metadata(channels_page),
                },
                "history": {
                    "items": history,
                    "pagination": _pagination_metadata(history_page),
                },
                "counts": {
                    "total_videos": videos_page.total,
                    "total_channels": channels_page.total,
                    "total_history_records": history_page.total,
                },
            }
        )

    @app.route("/export", methods=["GET"])
    def export_data_route():
        export_format = request.args.get("format", "csv").lower()

        if export_format == "csv":
            return Response(
                stream_with_context(stream_all_tables_csv()),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=exported_data.csv"
                },
            )

        if export_format == "xlsx":
            file_path = build_xlsx_export_file()

            @after_this_request
            def cleanup(response):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                return response

            return send_file(
                file_path,
                as_attachment=True,
                download_name="exported_data.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        return "Invalid format! Please choose 'csv' or 'xlsx'.", 400

    @app.route("/export/research.zip", methods=["GET"])
    def research_zip_export_route():
        file_path = build_research_zip_file(normalize_export_filters(request.args))

        @after_this_request
        def cleanup(response):
            try:
                os.remove(file_path)
            except OSError:
                pass
            return response

        return send_file(
            file_path,
            as_attachment=True,
            download_name="youtube-research-export.zip",
            mimetype="application/zip",
        )

    @app.route("/export/research.jsonl", methods=["GET"])
    def research_jsonl_export_route():
        return Response(
            stream_with_context(
                stream_research_jsonl(normalize_export_filters(request.args))
            ),
            mimetype="application/x-ndjson",
            headers={
                "Content-Disposition": "attachment; filename=youtube-research-export.jsonl"
            },
        )

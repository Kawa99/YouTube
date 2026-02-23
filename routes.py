import os

from crud import save_video
from export import build_xlsx_export_file, stream_all_tables_csv
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
from models import Channel, ChannelHistory, Video, db
from tasks import RedisError, enqueue_channel_job, get_channel_job
from youtube_api import (
    YOUTUBE_API_KEY,
    extract_video_id,
    get_channel_id_from_url,
    get_video_data,
    is_valid_youtube_channel_url,
    is_valid_youtube_video_url,
)

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


def _build_order_clause(column_map, sort_column, sort_direction, default_column, default_direction="desc"):
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


def register_routes(app, limiter):
    """Register application routes."""

    @app.route("/", methods=["GET", "POST"])
    @limiter.limit("60 per minute")
    def index():
        video_data = None

        if request.method == "POST":
            if not YOUTUBE_API_KEY:
                flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
                return render_template("index.html", data=None)

            video_url = request.form.get("video_url", "").strip()
            if not is_valid_youtube_video_url(video_url):
                flash("URL must be a valid youtube.com or youtu.be video link.", "warning")
                return render_template("index.html", data=None)

            video_id = extract_video_id(video_url)
            if not video_id:
                flash("Invalid YouTube URL. Please paste a valid video link.", "warning")
                return render_template("index.html", data=None)

            video_data = get_video_data(video_id)
            if not video_data:
                flash("Could not fetch video data. Check your API key/quota and try again.", "warning")

        return render_template("index.html", data=video_data)

    @app.route("/channel", methods=["GET", "POST"])
    @limiter.limit("30 per minute")
    def channel_scraper():
        if request.method == "POST":
            if not YOUTUBE_API_KEY:
                flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
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
                flash("Could not extract channel ID from URL. Please check the URL format.", "danger")
                return render_template("channel.html", job_id=None, job=None)

            try:
                job_id = enqueue_channel_job(channel_id, max_videos)
            except RedisError:
                flash("Background queue is unavailable. Ensure Redis and the RQ worker are running.", "danger")
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
            flash("YouTube API key is not configured. Set the YOUTUBE_API_KEY environment variable.", "danger")
            return redirect(url_for("channel_scraper"))

        max_videos = max(1, min(max_videos, 1000))
        try:
            job_id = enqueue_channel_job(channel_id, max_videos)
        except RedisError:
            flash("Background queue is unavailable. Ensure Redis and the RQ worker are running.", "danger")
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
            video_data = request.form.to_dict()
            result = save_video(video_data)
            if result.get("created"):
                flash("Video data saved successfully!", "success")
            else:
                flash("Video already exists. Stored record was refreshed.", "info")
        except Exception as e:
            flash(f"Error saving video: {str(e)}", "danger")

        return redirect(url_for("index"))

    @app.route("/data")
    def data_viewer():
        return render_template("data_viewer.html")

    @app.route("/api/data")
    def get_data_api():
        page = _parse_positive_int(request.args.get("page", 1), default=1)
        limit = _parse_positive_int(request.args.get("limit", 25), default=25, maximum=MAX_API_PAGE_SIZE)
        sort_column = request.args.get("sort_column", "saved_at")
        sort_direction = _normalize_sort_direction(request.args.get("sort_direction", "desc"))

        videos_sort_columns = {
            "id": Video.id,
            "youtube_video_id": Video.youtube_video_id,
            "title": Video.title,
            "channel_username": Channel.channel_username,
            "views": Video.views,
            "likes": Video.likes,
            "comments": Video.comments,
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
        channels_page = Channel.query.order_by(channels_order).paginate(page=page, per_page=limit, error_out=False)
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
                headers={"Content-Disposition": "attachment; filename=exported_data.csv"},
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

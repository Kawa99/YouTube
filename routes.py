import os

from database import init_db, save_video
from export import build_xlsx_export_file, open_videos_db_connection, stream_all_tables_csv
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
from tasks import RedisError, enqueue_channel_job, get_channel_job
from youtube_api import (
    YOUTUBE_API_KEY,
    extract_video_id,
    get_channel_id_from_url,
    get_video_data,
    is_valid_youtube_channel_url,
    is_valid_youtube_video_url,
)


def fetch_rows_as_dicts(conn, query):
    cursor = conn.execute(query)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def register_routes(app, limiter):
    """Register application routes and initialize the database."""
    init_db()

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
        conn = open_videos_db_connection()

        videos_query = """
        SELECT
            v.id,
            v.youtube_video_id,
            v.title,
            c.channel_username,
            v.views,
            v.likes,
            v.comments,
            v.posted,
            v.video_length,
            v.saved_at,
            c.subscribers
        FROM videos v
        JOIN channels c ON v.channel_id = c.id
        ORDER BY v.saved_at DESC
        """

        channels_query = "SELECT id, channel_username, subscribers FROM channels ORDER BY subscribers DESC"

        history_query = """
        SELECT
            ch.id,
            c.channel_username,
            ch.previous_subscribers,
            ch.recorded_at
        FROM channel_history ch
        JOIN channels c ON ch.channel_id = c.id
        ORDER BY ch.recorded_at DESC
        """

        videos = fetch_rows_as_dicts(conn, videos_query)
        channels = fetch_rows_as_dicts(conn, channels_query)
        history = fetch_rows_as_dicts(conn, history_query)

        conn.close()

        data = {
            "videos": videos,
            "channels": channels,
            "history": history,
            "counts": {
                "total_videos": len(videos),
                "total_channels": len(channels),
                "total_history_records": len(history),
            },
        }

        return jsonify(data)

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

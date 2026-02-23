import csv
import io
import os
import random
import re
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timezone
from queue import Queue as StdlibQueue
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import isodate
import requests
from database import init_db, save_video
from flask import (
    Flask,
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
from openpyxl import Workbook
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from youtube_transcript_api import YouTubeTranscriptApi, _errors as transcript_errors

try:
    from redis import Redis
    from redis.exceptions import RedisError
    from rq import Queue, get_current_job
    from rq.exceptions import NoSuchJobError
    from rq.job import Job
    RQ_AVAILABLE = True
except ModuleNotFoundError:
    Redis = None
    Queue = None
    NoSuchJobError = Exception
    Job = None
    RQ_AVAILABLE = False

    class RedisError(Exception):
        pass

    def get_current_job():
        return None

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ModuleNotFoundError:
    Limiter = None

    def get_remote_address():  # noqa: D401
        return "127.0.0.1"


class NoopLimiter:
    """Fallback limiter used when Flask-Limiter is unavailable."""

    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default-dev-key")
if Limiter is not None:
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[])
else:
    limiter = NoopLimiter()

# Initialize the database when app starts.
init_db()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = (3.05, 15)
API_MAX_RETRIES = int(os.environ.get("API_MAX_RETRIES", "5"))
API_BACKOFF_BASE_SECONDS = float(os.environ.get("API_BACKOFF_BASE_SECONDS", "0.5"))
TRANSCRIPT_UNAVAILABLE_MESSAGE = "Transcript unavailable or disabled by the uploader."
EXPORT_TABLES = ("videos", "channels", "channel_videos", "channel_history")
DB_FETCH_CHUNK_SIZE = 1000
YOUTUBE_VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
YOUTUBE_CHANNEL_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RQ_QUEUE_NAME = os.environ.get("RQ_QUEUE_NAME", "channel-scrape")
CHANNEL_JOB_TIMEOUT = int(os.environ.get("CHANNEL_JOB_TIMEOUT_SECONDS", "7200"))
CHANNEL_JOB_RESULT_TTL = int(os.environ.get("CHANNEL_JOB_RESULT_TTL_SECONDS", "86400"))


def _transcript_error(name):
    return getattr(transcript_errors, name, type(name, (Exception,), {}))


TranscriptsDisabled = _transcript_error("TranscriptsDisabled")
NoTranscriptFound = _transcript_error("NoTranscriptFound")
NON_RETRIABLE_TRANSCRIPT_EXCEPTIONS = (
    TranscriptsDisabled,
    NoTranscriptFound,
    _transcript_error("VideoUnavailable"),
    _transcript_error("InvalidVideoId"),
    _transcript_error("NotTranslatable"),
    _transcript_error("TranslationLanguageNotAvailable"),
)
RETRIABLE_TRANSCRIPT_EXCEPTIONS = (
    _transcript_error("TooManyRequests"),
    _transcript_error("RequestBlocked"),
    _transcript_error("IpBlocked"),
    _transcript_error("CouldNotRetrieveTranscript"),
    _transcript_error("YouTubeRequestFailed"),
)

# Create a resilient session for outbound HTTP calls.
session = requests.Session()
retries = Retry(
    total=API_MAX_RETRIES,
    connect=API_MAX_RETRIES,
    read=API_MAX_RETRIES,
    status=API_MAX_RETRIES,
    backoff_factor=API_BACKOFF_BASE_SECONDS,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset({"GET"}),
    raise_on_status=False,
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))

if RQ_AVAILABLE:
    # Redis-backed RQ queue.
    redis_connection = Redis.from_url(REDIS_URL)
    channel_queue = Queue(RQ_QUEUE_NAME, connection=redis_connection, default_timeout=CHANNEL_JOB_TIMEOUT)
else:
    redis_connection = None
    channel_queue = None
    LOCAL_JOB_QUEUE = StdlibQueue()
    LOCAL_JOBS = {}
    LOCAL_JOBS_LOCK = threading.Lock()
    LOCAL_WORKER_THREAD = None


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _sleep_with_backoff(attempt, base_delay=API_BACKOFF_BASE_SECONDS, max_delay=8.0):
    delay = min(max_delay, base_delay * (2 ** attempt))
    jitter = random.uniform(0, delay * 0.2 if delay > 0 else 0)
    time.sleep(delay + jitter)


def request_json_with_retry(url, params=None, timeout=REQUEST_TIMEOUT):
    """GET JSON with a retry-enabled session."""
    params = params or {}

    try:
        response = session.get(url, params=params, timeout=timeout)
        if response.status_code >= 400:
            return {}
        return response.json()
    except (requests.RequestException, ValueError):
        return {}


def youtube_api_get(endpoint, params):
    payload = dict(params)
    payload["key"] = YOUTUBE_API_KEY
    return request_json_with_retry(f"{YOUTUBE_API_BASE_URL}/{endpoint}", params=payload)


def _get_queue():
    if not RQ_AVAILABLE:
        raise RedisError("Redis/RQ dependencies are not installed.")
    redis_connection.ping()
    return channel_queue


def _job_payload_defaults(channel_id, max_videos):
    return {
        "channel_id": channel_id,
        "max_videos": max_videos,
        "message": "Job is queued.",
        "queued_at": utc_now_iso(),
        "started_at": None,
        "completed_at": None,
        "total_videos": 0,
        "current": 0,
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "progress_pct": 0,
        "current_video_id": None,
        "error": None,
    }


def _local_update_job(job_id, **updates):
    with LOCAL_JOBS_LOCK:
        if job_id in LOCAL_JOBS:
            LOCAL_JOBS[job_id].update(updates)


def _local_get_job(job_id):
    with LOCAL_JOBS_LOCK:
        job = LOCAL_JOBS.get(job_id)
        return dict(job) if job else None


def _local_channel_worker():
    while True:
        job_id = LOCAL_JOB_QUEUE.get()
        if job_id is None:
            LOCAL_JOB_QUEUE.task_done()
            return

        job = _local_get_job(job_id)
        if not job:
            LOCAL_JOB_QUEUE.task_done()
            continue

        _local_update_job(
            job_id,
            status="running",
            started_at=utc_now_iso(),
            message="Fetching channel videos...",
            error=None,
        )

        try:
            video_ids = get_channel_videos(job["channel_id"], job["max_videos"])
            total_videos = len(video_ids)
            _local_update_job(job_id, total_videos=total_videos)

            if total_videos == 0:
                _local_update_job(
                    job_id,
                    status="completed",
                    completed_at=utc_now_iso(),
                    progress_pct=100,
                    message="No videos found for this channel.",
                )
                LOCAL_JOB_QUEUE.task_done()
                continue

            processed_count = 0
            failed_count = 0
            skipped_count = 0

            for index, video_id in enumerate(video_ids, start=1):
                try:
                    video_data = get_video_data(video_id)
                    if video_data:
                        save_result = save_video(video_data)
                        if save_result.get("created"):
                            processed_count += 1
                        else:
                            skipped_count += 1
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1

                _local_update_job(
                    job_id,
                    current=index,
                    processed=processed_count,
                    failed=failed_count,
                    skipped=skipped_count,
                    current_video_id=video_id,
                    progress_pct=int((index / total_videos) * 100),
                    message=f"Processing videos ({index}/{total_videos})",
                )

            _local_update_job(
                job_id,
                status="completed",
                completed_at=utc_now_iso(),
                progress_pct=100,
                message=(
                    "Channel processing complete. "
                    f"Inserted: {processed_count}, Updated/Skipped: {skipped_count}, Failed: {failed_count}."
                ),
            )
        except Exception as exc:
            _local_update_job(
                job_id,
                status="failed",
                completed_at=utc_now_iso(),
                message="Channel processing failed.",
                error=str(exc),
            )
        finally:
            LOCAL_JOB_QUEUE.task_done()


def _start_local_worker():
    global LOCAL_WORKER_THREAD
    if LOCAL_WORKER_THREAD and LOCAL_WORKER_THREAD.is_alive():
        return

    LOCAL_WORKER_THREAD = threading.Thread(target=_local_channel_worker, daemon=True, name="local-channel-worker")
    LOCAL_WORKER_THREAD.start()


def enqueue_channel_job(channel_id, max_videos):
    if not RQ_AVAILABLE:
        _start_local_worker()
        job_id = uuid4().hex
        payload = _job_payload_defaults(channel_id, max_videos)
        payload.update({"id": job_id, "status": "queued"})
        with LOCAL_JOBS_LOCK:
            LOCAL_JOBS[job_id] = payload
        LOCAL_JOB_QUEUE.put(job_id)
        return job_id

    queue = _get_queue()
    job = queue.enqueue(
        process_channel_background,
        channel_id,
        max_videos,
        job_timeout=CHANNEL_JOB_TIMEOUT,
        result_ttl=CHANNEL_JOB_RESULT_TTL,
        failure_ttl=CHANNEL_JOB_RESULT_TTL,
    )
    job.meta.update(_job_payload_defaults(channel_id, max_videos))
    job.save_meta()
    return job.id


def _normalize_job_status(raw_status):
    return {
        "queued": "queued",
        "deferred": "queued",
        "scheduled": "queued",
        "started": "running",
        "finished": "completed",
        "failed": "failed",
        "stopped": "failed",
        "canceled": "failed",
    }.get(raw_status, raw_status)


def get_channel_job(job_id):
    if not job_id:
        return None

    if not RQ_AVAILABLE:
        return _local_get_job(job_id)

    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except (NoSuchJobError, RedisError, ValueError):
        return None

    raw_status = job.get_status(refresh=True)
    status = _normalize_job_status(raw_status)
    meta = dict(job.meta or {})
    total_videos = int(meta.get("total_videos", 0) or 0)
    current = int(meta.get("current", 0) or 0)
    progress_pct = int(meta.get("progress_pct", 0) or 0)

    if total_videos > 0 and progress_pct == 0 and current > 0:
        progress_pct = int((current / total_videos) * 100)
    if status == "completed":
        progress_pct = 100

    message = meta.get("message")
    if not message:
        if status == "queued":
            message = "Job is queued."
        elif status == "running":
            message = "Processing channel videos..."
        elif status == "completed":
            message = "Channel processing complete."
        else:
            message = "Job failed."

    error = meta.get("error")
    if status == "failed" and not error and job.exc_info:
        error = job.exc_info.strip().splitlines()[-1]

    return {
        "id": job.id,
        "channel_id": meta.get("channel_id"),
        "max_videos": meta.get("max_videos"),
        "status": status,
        "message": message,
        "queued_at": meta.get("queued_at"),
        "started_at": meta.get("started_at"),
        "completed_at": meta.get("completed_at"),
        "total_videos": total_videos,
        "current": current,
        "processed": int(meta.get("processed", 0) or 0),
        "failed": int(meta.get("failed", 0) or 0),
        "skipped": int(meta.get("skipped", 0) or 0),
        "progress_pct": progress_pct,
        "current_video_id": meta.get("current_video_id"),
        "error": error,
    }


def _parse_input_url(raw_url):
    if not raw_url:
        return None

    normalized = raw_url.strip()
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    if not parsed.netloc:
        return None
    return parsed


def is_valid_youtube_video_url(video_url):
    parsed = _parse_input_url(video_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_VIDEO_HOSTS)


def is_valid_youtube_channel_url(channel_url):
    parsed = _parse_input_url(channel_url)
    return bool(parsed and parsed.netloc.lower() in YOUTUBE_CHANNEL_HOSTS)


def extract_video_id(video_url):
    """Extract video ID from supported YouTube URL formats."""
    parsed = _parse_input_url(video_url)
    if not parsed:
        return None

    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id = None

    if host in {"youtu.be", "www.youtu.be"}:
        if path_parts:
            video_id = path_parts[0]
    elif host in YOUTUBE_CHANNEL_HOSTS:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts and path_parts[0] in {"embed", "shorts", "live"} and len(path_parts) > 1:
            video_id = path_parts[1]

    if not video_id or not VIDEO_ID_PATTERN.match(video_id):
        return None

    return video_id


def extract_channel_info(channel_url):
    """Extract (identifier_type, identifier) from common YouTube channel URL formats."""
    parsed = _parse_input_url(channel_url)
    if not parsed:
        return None, None

    host = parsed.netloc.lower()
    if host not in YOUTUBE_CHANNEL_HOSTS:
        return None, None

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return None, None

    first = path_parts[0]
    if first == "channel" and len(path_parts) > 1:
        return "channel_id", path_parts[1]
    if first == "user" and len(path_parts) > 1:
        return "username", path_parts[1]
    if first == "c" and len(path_parts) > 1:
        return "custom", path_parts[1]
    if first.startswith("@"):
        return "handle", first

    reserved = {"watch", "shorts", "embed", "playlist", "feed", "results", "live"}
    if first not in reserved:
        return "custom", first

    return None, None


def get_channel_id_from_url(channel_url):
    """Resolve a canonical YouTube channel ID (UC...) from various URL formats."""
    identifier_type, identifier = extract_channel_info(channel_url)
    if not identifier:
        return None

    handle_no_at = identifier[1:] if identifier.startswith("@") else identifier

    call_plan = []
    if identifier_type == "channel_id":
        call_plan.append(("channels", {"part": "id", "id": identifier}))
    elif identifier_type == "username":
        call_plan.append(("channels", {"part": "id", "forUsername": identifier}))
    elif identifier_type == "handle":
        call_plan.append(("channels", {"part": "id", "forHandle": identifier}))
        call_plan.append(("channels", {"part": "id", "forHandle": handle_no_at}))
    else:
        call_plan.append(("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}))

    call_plan.extend(
        [
            ("channels", {"part": "id", "id": identifier}),
            ("channels", {"part": "id", "forUsername": identifier}),
            ("channels", {"part": "id", "forHandle": identifier}),
            ("channels", {"part": "id", "forHandle": handle_no_at}),
            ("search", {"part": "snippet", "type": "channel", "q": identifier, "maxResults": 1}),
        ]
    )

    for endpoint, params in call_plan:
        response = youtube_api_get(endpoint, params)
        items = response.get("items", [])
        if not items:
            continue

        if endpoint == "channels":
            return items[0].get("id")

        item = items[0]
        item_id = item.get("id")
        search_id = item_id.get("channelId") if isinstance(item_id, dict) else None
        search_id = search_id or item.get("snippet", {}).get("channelId")
        if search_id:
            return search_id

    return None


def get_channel_videos_from_search(channel_id, max_results=50):
    """Fallback: fetch channel videos using search endpoint ordered by date."""
    videos = []
    next_page_token = None

    while len(videos) < max_results:
        params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(50, max_results - len(videos)),
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        response = youtube_api_get("search", params)
        items = response.get("items", [])
        if not items:
            break

        for item in items:
            item_id = item.get("id")
            video_id = item_id.get("videoId") if isinstance(item_id, dict) else None
            if video_id:
                videos.append(video_id)
                if len(videos) >= max_results:
                    break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def get_channel_videos(channel_id, max_results=50):
    """Get up to max_results recent video IDs from a channel uploads playlist."""
    videos = []
    next_page_token = None

    channel_response = youtube_api_get("channels", {"part": "contentDetails", "id": channel_id})
    items = channel_response.get("items", [])
    if not items:
        return videos

    uploads_playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        return get_channel_videos_from_search(channel_id, max_results)

    while len(videos) < max_results:
        playlist_params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(50, max_results - len(videos)),
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token

        playlist_response = youtube_api_get("playlistItems", playlist_params)
        items = playlist_response.get("items", [])
        if not items:
            break

        for item in items:
            if len(videos) >= max_results:
                break
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                videos.append(video_id)

        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token:
            break

    if not videos:
        return get_channel_videos_from_search(channel_id, max_results)

    return videos


def parse_duration(duration):
    """Converts YouTube ISO 8601 duration format to HH:MM:SS."""
    try:
        parsed_duration = isodate.parse_duration(duration)
        return str(parsed_duration)
    except Exception:
        return "Unknown"


def _should_retry_transcript_exception(exc):
    if isinstance(exc, NON_RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return False

    if isinstance(exc, RETRIABLE_TRANSCRIPT_EXCEPTIONS):
        return True

    message = str(exc).lower()
    retryable_markers = ["429", "rate limit", "timed out", "temporar", "try again"]
    return any(marker in message for marker in retryable_markers)


def get_transcript(video_id):
    """Fetch transcript with retry for transient errors."""
    api = YouTubeTranscriptApi()

    for attempt in range(API_MAX_RETRIES):
        try:
            transcript = api.fetch(video_id)
            return " ".join([line.text for line in transcript])
        except (TranscriptsDisabled, NoTranscriptFound):
            return TRANSCRIPT_UNAVAILABLE_MESSAGE
        except Exception as exc:
            if attempt >= API_MAX_RETRIES - 1 or not _should_retry_transcript_exception(exc):
                return TRANSCRIPT_UNAVAILABLE_MESSAGE
            _sleep_with_backoff(attempt)

    return TRANSCRIPT_UNAVAILABLE_MESSAGE


def get_video_data(video_id):
    """Fetch video details including channel @username and subscribers."""
    response = youtube_api_get(
        "videos",
        {"part": "snippet,statistics,contentDetails", "id": video_id},
    )

    items = response.get("items", [])
    if not items:
        return None

    data = items[0]
    snippet = data.get("snippet", {})
    statistics = data.get("statistics", {})
    content_details = data.get("contentDetails", {})
    channel_id = snippet.get("channelId")

    channel_username = f"@{channel_id}" if channel_id else "@unknown"
    subscribers = "0"

    if channel_id:
        channel_response = youtube_api_get(
            "channels",
            {"part": "snippet,statistics", "id": channel_id},
        )
        channel_items = channel_response.get("items", [])
        if channel_items:
            channel_snippet = channel_items[0].get("snippet", {})
            channel_stats = channel_items[0].get("statistics", {})
            channel_username = channel_snippet.get("customUrl", f"@{channel_id}")
            subscribers = channel_stats.get("subscriberCount", "0")

    published = snippet.get("publishedAt", "")
    posted = published.split("T")[0] if published else ""

    return {
        "youtube_video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "views": statistics.get("viewCount", 0),
        "likes": statistics.get("likeCount", 0),
        "comments": statistics.get("commentCount", 0),
        "posted": posted,
        "channel_username": channel_username,
        "subscribers": subscribers,
        "video_length": parse_duration(content_details.get("duration", "")),
        "transcript": get_transcript(video_id),
    }


def _update_current_job_meta(**updates):
    job = get_current_job()
    if not job:
        return

    job.meta.update(updates)
    job.save_meta()


def process_channel_background(channel_id, max_videos):
    _update_current_job_meta(
        channel_id=channel_id,
        max_videos=max_videos,
        started_at=utc_now_iso(),
        error=None,
        message="Fetching channel videos...",
        progress_pct=0,
    )

    try:
        video_ids = get_channel_videos(channel_id, max_videos)
        total_videos = len(video_ids)
        _update_current_job_meta(total_videos=total_videos)

        if total_videos == 0:
            summary = {
                "inserted": 0,
                "updated_or_skipped": 0,
                "failed": 0,
                "total_videos": 0,
            }
            _update_current_job_meta(
                progress_pct=100,
                completed_at=utc_now_iso(),
                message="No videos found for this channel.",
                **summary,
            )
            return summary

        processed_count = 0
        failed_count = 0
        skipped_count = 0

        for index, video_id in enumerate(video_ids, start=1):
            try:
                video_data = get_video_data(video_id)
                if video_data:
                    save_result = save_video(video_data)
                    if save_result.get("created"):
                        processed_count += 1
                    else:
                        skipped_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

            _update_current_job_meta(
                current=index,
                processed=processed_count,
                failed=failed_count,
                skipped=skipped_count,
                current_video_id=video_id,
                progress_pct=int((index / total_videos) * 100),
                message=f"Processing videos ({index}/{total_videos})",
            )

        summary = {
            "inserted": processed_count,
            "updated_or_skipped": skipped_count,
            "failed": failed_count,
            "total_videos": total_videos,
        }
        _update_current_job_meta(
            completed_at=utc_now_iso(),
            progress_pct=100,
            message=(
                "Channel processing complete. "
                f"Inserted: {processed_count}, Updated/Skipped: {skipped_count}, Failed: {failed_count}."
            ),
            **summary,
        )
        return summary
    except Exception as exc:
        _update_current_job_meta(
            completed_at=utc_now_iso(),
            error=str(exc),
            message="Channel processing failed.",
        )
        raise


def fetch_rows_as_dicts(conn, query):
    cursor = conn.execute(query)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def iter_table_csv(conn, table_name):
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(columns)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    while True:
        rows = cursor.fetchmany(DB_FETCH_CHUNK_SIZE)
        if not rows:
            break

        writer.writerows(rows)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def stream_all_tables_csv():
    conn = sqlite3.connect("videos.db")

    try:
        for table_name in EXPORT_TABLES:
            yield f"=== {table_name.upper()} ===\n"
            yield from iter_table_csv(conn, table_name)
            yield "\n"
    finally:
        conn.close()


def build_xlsx_export_file():
    conn = sqlite3.connect("videos.db")
    workbook = Workbook(write_only=True)

    try:
        for table_name in EXPORT_TABLES:
            sheet = workbook.create_sheet(title=table_name[:31])
            cursor = conn.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            sheet.append(columns)

            while True:
                rows = cursor.fetchmany(DB_FETCH_CHUNK_SIZE)
                if not rows:
                    break
                for row in rows:
                    sheet.append(row)

        temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        workbook.save(temp_file_path)
        return temp_file_path
    finally:
        conn.close()


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
    conn = sqlite3.connect("videos.db")

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

if __name__ == "__main__":
    app.run(debug=True)

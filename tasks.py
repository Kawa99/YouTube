import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import has_app_context
from flask_socketio import SocketIO

from crud import save_video
from youtube_api import get_channel_videos, get_video_data

logger = logging.getLogger(__name__)

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

    def get_current_job() -> None:
        return None


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RQ_QUEUE_NAME = os.environ.get("RQ_QUEUE_NAME", "channel-scrape")
CHANNEL_JOB_TIMEOUT = int(os.environ.get("CHANNEL_JOB_TIMEOUT_SECONDS", "7200"))
CHANNEL_JOB_RESULT_TTL = int(os.environ.get("CHANNEL_JOB_RESULT_TTL_SECONDS", "86400"))
external_sio = SocketIO(message_queue=os.environ.get("REDIS_URL"))

if RQ_AVAILABLE and REDIS_URL:
    redis_connection = Redis.from_url(REDIS_URL)
    channel_queue = Queue(RQ_QUEUE_NAME, connection=redis_connection, default_timeout=CHANNEL_JOB_TIMEOUT)
else:
    redis_connection = None
    channel_queue = None
_worker_app = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_queue() -> Any:
    if not RQ_AVAILABLE or not redis_connection or not channel_queue:
        raise RedisError("Redis/RQ is not installed or configured.")
    redis_connection.ping()
    return channel_queue


def _job_payload_defaults(channel_id: str, max_videos: int) -> Dict[str, Any]:
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


def enqueue_channel_job(channel_id: str, max_videos: int) -> str:
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


def _normalize_job_status(raw_status: Optional[str]) -> Optional[str]:
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


def get_channel_job(job_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not job_id:
        return None

    if not RQ_AVAILABLE or not redis_connection:
        return None

    try:
        redis_connection.ping()
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


def _update_current_job_meta(**updates: Any) -> None:
    job = get_current_job()
    if not job:
        return

    job.meta.update(updates)
    job.save_meta()
    external_sio.emit("progress_update", updates, room=job.id)


def _process_channel_background_impl(channel_id: str, max_videos: int) -> Dict[str, int]:
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
            except Exception as e:
                logger.exception("An error occurred: %s", str(e))
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
    except Exception as e:
        logger.exception("An error occurred: %s", str(e))
        _update_current_job_meta(
            completed_at=utc_now_iso(),
            error=str(e),
            message="Channel processing failed.",
        )
        raise


def process_channel_background(channel_id: str, max_videos: int) -> Dict[str, int]:
    global _worker_app

    if has_app_context():
        return _process_channel_background_impl(channel_id, max_videos)

    # RQ workers run outside request context; build an app context for db.session.
    if _worker_app is None:
        from app import create_app

        _worker_app = create_app()

    with _worker_app.app_context():
        return _process_channel_background_impl(channel_id, max_videos)

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import has_app_context
from flask_socketio import SocketIO

from crud import save_video
from metrics import compute_derived_metrics
from youtube_api import (
    get_channel_id_from_url,
    get_channel_videos_with_metadata,
    get_videos_data,
)

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
TRACKED_CHANNEL_MAX_VIDEOS = int(os.environ.get("TRACKED_CHANNEL_MAX_VIDEOS", "50"))
SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "threading")
YOUTUBE_DAILY_QUOTA_BUDGET = int(os.environ.get("YOUTUBE_DAILY_QUOTA_BUDGET", "10000"))
VIDEO_SAVE_COMMIT_INTERVAL = max(
    1, int(os.environ.get("VIDEO_SAVE_COMMIT_INTERVAL", "50"))
)
external_sio = SocketIO(
    message_queue=os.environ.get("REDIS_URL"),
    async_mode=SOCKETIO_ASYNC_MODE,
)

if RQ_AVAILABLE and REDIS_URL:
    redis_connection = Redis.from_url(REDIS_URL)
    channel_queue = Queue(
        RQ_QUEUE_NAME, connection=redis_connection, default_timeout=CHANNEL_JOB_TIMEOUT
    )
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
        "collection_run_id": None,
        "quota_estimate": None,
        "quota_warning": None,
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


def _channel_identifier_to_url(channel_username: str) -> Optional[str]:
    normalized = str(channel_username or "").strip()
    if not normalized:
        return None
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized
    if normalized.startswith("@"):
        return f"https://www.youtube.com/{normalized}"
    if normalized.startswith("UC"):
        return f"https://www.youtube.com/channel/{normalized}"
    return f"https://www.youtube.com/{normalized}"


def _scrape_tracked_channels_impl() -> Dict[str, int]:
    from models import Channel

    tracked_channels = Channel.query.filter_by(is_tracked=True).all()
    enqueued_jobs = 0
    failed = 0

    for channel in tracked_channels:
        channel_username = str(channel.channel_username or "").strip()
        if not channel_username:
            failed += 1
            continue

        channel_id = (
            channel_username
            if channel_username.startswith("UC")
            else get_channel_id_from_url(_channel_identifier_to_url(channel_username))
        )
        if not channel_id:
            failed += 1
            logger.warning(
                "Skipping tracked channel %s because it could not be resolved.",
                channel_username,
            )
            continue

        try:
            enqueue_channel_job(channel_id, TRACKED_CHANNEL_MAX_VIDEOS)
            enqueued_jobs += 1
        except Exception as e:
            failed += 1
            logger.exception(
                "Failed to enqueue tracked channel %s: %s", channel_id, str(e)
            )

    return {
        "tracked_channels": len(tracked_channels),
        "enqueued_jobs": enqueued_jobs,
        "failed": failed,
    }


def scrape_tracked_channels() -> Dict[str, int]:
    global _worker_app

    if has_app_context():
        return _scrape_tracked_channels_impl()

    # Scheduled RQ jobs run outside request context; build one for db.session.
    if _worker_app is None:
        from app import create_app

        _worker_app = create_app()

    with _worker_app.app_context():
        return _scrape_tracked_channels_impl()


def compute_derived_metrics_job() -> Dict[str, int]:
    global _worker_app

    if has_app_context():
        return compute_derived_metrics()

    if _worker_app is None:
        from app import create_app

        _worker_app = create_app()

    with _worker_app.app_context():
        return compute_derived_metrics()


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
        "collection_run_id": meta.get("collection_run_id"),
        "quota_estimate": meta.get("quota_estimate"),
        "quota_warning": meta.get("quota_warning"),
        "error": error,
    }


def _update_current_job_meta(**updates: Any) -> None:
    job = get_current_job()
    if not job:
        return

    job.meta.update(updates)
    job.save_meta()
    external_sio.emit("progress_update", updates, room=job.id)


def _create_collection_run(
    *,
    run_type: str,
    input_type: str,
    input_value: str,
    requested_limit: int,
    quota_estimate: int,
    created_by: str,
):
    from models import CollectionRun, db

    collection_run = CollectionRun(
        run_type=run_type,
        status="running",
        input_type=input_type,
        input_value=input_value,
        requested_limit=requested_limit,
        quota_estimate=quota_estimate,
        created_by=created_by,
    )
    db.session.add(collection_run)
    db.session.commit()
    return collection_run


def _record_sampling_metadata(collection_run_id: int, external_id: str, payload: dict):
    from models import ApiRawPayload, db

    db.session.add(
        ApiRawPayload(
            source="youtube_collector",
            endpoint="sampling_metadata",
            external_id=external_id,
            payload_json=payload,
            collection_run_id=collection_run_id,
        )
    )
    db.session.commit()


def _finish_collection_run(
    collection_run_id: int,
    *,
    status: str,
    items_found: int,
    items_saved: int,
    items_failed: int,
    error_summary: Optional[str] = None,
    quota_estimate: Optional[int] = None,
):
    from models import CollectionRun, db

    collection_run = db.session.get(CollectionRun, collection_run_id)
    if not collection_run:
        return

    collection_run.status = status
    collection_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    collection_run.items_found = items_found
    collection_run.items_saved = items_saved
    collection_run.items_failed = items_failed
    collection_run.error_summary = error_summary
    if quota_estimate is not None:
        collection_run.quota_estimate = quota_estimate
    db.session.commit()


def _save_result_counts(save_result):
    if save_result.get("created"):
        return 1, 0
    return 0, 1


def _commit_pending_video_saves(pending_saves):
    if not pending_saves:
        return 0, 0, 0

    from models import db

    try:
        db.session.commit()
        created = 0
        updated_or_skipped = 0
        for _, _, save_result in pending_saves:
            result_created, result_updated = _save_result_counts(save_result)
            created += result_created
            updated_or_skipped += result_updated
        return created, updated_or_skipped, 0
    except Exception as exc:
        logger.exception(
            "Bulk video save commit failed for %s pending rows: %s",
            len(pending_saves),
            str(exc),
        )
        db.session.rollback()

    created = 0
    updated_or_skipped = 0
    failed = 0
    for video_id, payload, _ in pending_saves:
        try:
            retry_result = save_video(payload)
            result_created, result_updated = _save_result_counts(retry_result)
            created += result_created
            updated_or_skipped += result_updated
        except Exception as exc:
            logger.exception("Retry save failed for video %s: %s", video_id, str(exc))
            failed += 1
    return created, updated_or_skipped, failed


def _process_channel_background_impl(
    channel_id: str, max_videos: int
) -> Dict[str, int]:
    expected_batches = (max_videos + 49) // 50
    initial_quota_estimate = 1 + expected_batches + expected_batches + 1
    quota_warning = None
    if initial_quota_estimate > YOUTUBE_DAILY_QUOTA_BUDGET:
        quota_warning = (
            f"Estimated quota cost {initial_quota_estimate} exceeds "
            f"daily budget {YOUTUBE_DAILY_QUOTA_BUDGET}."
        )

    collection_run = _create_collection_run(
        run_type="channel_uploads",
        input_type="channel_id",
        input_value=channel_id,
        requested_limit=max_videos,
        quota_estimate=initial_quota_estimate,
        created_by="rq_worker",
    )

    _update_current_job_meta(
        channel_id=channel_id,
        max_videos=max_videos,
        collection_run_id=collection_run.id,
        quota_estimate=initial_quota_estimate,
        quota_warning=quota_warning,
        started_at=utc_now_iso(),
        error=None,
        message="Fetching channel videos...",
        progress_pct=0,
    )

    try:
        collection = get_channel_videos_with_metadata(channel_id, max_videos)
        video_ids = collection["video_ids"]
        total_videos = len(video_ids)
        quota_estimate = collection.get("quota_estimate", initial_quota_estimate)
        _record_sampling_metadata(
            collection_run.id,
            channel_id,
            {
                "mode": collection.get("mode"),
                "quota_estimate": quota_estimate,
                **collection.get("sampling_metadata", {}),
            },
        )
        _update_current_job_meta(
            total_videos=total_videos,
            quota_estimate=quota_estimate,
            quota_warning=quota_warning,
        )

        if total_videos == 0:
            summary = {
                "inserted": 0,
                "updated_or_skipped": 0,
                "failed": 0,
                "total_videos": 0,
            }
            _finish_collection_run(
                collection_run.id,
                status="completed",
                items_found=0,
                items_saved=0,
                items_failed=0,
                quota_estimate=quota_estimate,
            )
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
        video_data_by_id = get_videos_data(video_ids)
        pending_saves = []

        for index, video_id in enumerate(video_ids, start=1):
            try:
                video_data = video_data_by_id.get(video_id)
                if video_data:
                    payload = {**video_data, "collection_run_id": collection_run.id}
                    save_result = save_video(payload, commit=False)
                    pending_saves.append((video_id, payload, save_result))
                    if len(pending_saves) >= VIDEO_SAVE_COMMIT_INTERVAL:
                        created, updated_or_skipped, failed = (
                            _commit_pending_video_saves(pending_saves)
                        )
                        processed_count += created
                        skipped_count += updated_or_skipped
                        failed_count += failed
                        pending_saves = []
                else:
                    failed_count += 1
            except Exception as e:
                logger.exception("An error occurred: %s", str(e))
                if pending_saves:
                    created, updated_or_skipped, failed = _commit_pending_video_saves(
                        pending_saves
                    )
                    processed_count += created
                    skipped_count += updated_or_skipped
                    failed_count += failed
                    pending_saves = []
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

        if pending_saves:
            created, updated_or_skipped, failed = _commit_pending_video_saves(
                pending_saves
            )
            processed_count += created
            skipped_count += updated_or_skipped
            failed_count += failed

        summary = {
            "inserted": processed_count,
            "updated_or_skipped": skipped_count,
            "failed": failed_count,
            "total_videos": total_videos,
        }
        _finish_collection_run(
            collection_run.id,
            status="completed" if failed_count == 0 else "partial",
            items_found=total_videos,
            items_saved=processed_count + skipped_count,
            items_failed=failed_count,
            quota_estimate=quota_estimate,
        )
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
        _finish_collection_run(
            collection_run.id,
            status="failed",
            items_found=0,
            items_saved=0,
            items_failed=1,
            error_summary=str(e),
        )
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

from datetime import UTC, datetime

from sqlalchemy import text

from models import CollectionRun, db
from tasks import (
    RQ_AVAILABLE,
    RQ_QUEUE_NAME,
    REDIS_URL,
    channel_queue,
    redis_connection,
)


def operations_summary():
    redis_health = _redis_health()
    return {
        "checked_at": datetime.now(UTC).replace(tzinfo=None),
        "database": _database_health(),
        "redis": redis_health,
        "queue": _queue_health(redis_health["ok"]),
        "workers": _worker_health(redis_health["ok"]),
        "recent_failures": (
            CollectionRun.query.filter(CollectionRun.status.in_(("failed", "partial")))
            .order_by(CollectionRun.started_at.desc())
            .limit(10)
            .all()
        ),
        "recent_runs": (
            CollectionRun.query.order_by(CollectionRun.started_at.desc())
            .limit(10)
            .all()
        ),
    }


def health_payload():
    summary = operations_summary()
    ok = bool(summary["database"]["ok"] and summary["redis"]["ok"])
    return {
        "ok": ok,
        "checked_at": summary["checked_at"].isoformat(),
        "database": summary["database"],
        "redis": summary["redis"],
        "queue": summary["queue"],
        "workers": summary["workers"],
    }


def _database_health():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": "reachable"}


def _redis_health():
    if not RQ_AVAILABLE or redis_connection is None:
        return {"ok": False, "url": REDIS_URL, "message": "Redis/RQ unavailable"}
    try:
        redis_connection.ping()
    except Exception as exc:
        return {"ok": False, "url": REDIS_URL, "message": str(exc)}
    return {"ok": True, "url": REDIS_URL, "message": "reachable"}


def _queue_health(redis_ok):
    if not redis_ok or channel_queue is None:
        return {"ok": False, "name": RQ_QUEUE_NAME, "queued_jobs": None}
    try:
        return {
            "ok": True,
            "name": channel_queue.name,
            "queued_jobs": len(channel_queue),
        }
    except Exception as exc:
        return {"ok": False, "name": RQ_QUEUE_NAME, "message": str(exc)}


def _worker_health(redis_ok):
    if not redis_ok or redis_connection is None:
        return {"ok": False, "count": 0, "workers": []}
    try:
        from rq import Worker

        workers = Worker.all(connection=redis_connection)
    except Exception as exc:
        return {"ok": False, "count": 0, "workers": [], "message": str(exc)}

    return {
        "ok": bool(workers),
        "count": len(workers),
        "workers": [
            {
                "name": worker.name,
                "state": worker.state,
                "queues": [queue.name for queue in worker.queues],
            }
            for worker in workers
        ],
    }

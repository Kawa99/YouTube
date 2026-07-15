# Operations Guide

This guide covers running, monitoring, backing up, and troubleshooting Baroo.

## Runtime Architecture

Docker Compose starts:

- `web`: Flask/Gunicorn app.
- `worker`: RQ worker for background collection jobs.
- `scheduler`: recurring tracked-channel scheduler.
- `redis`: queue and job-status store.
- `db`: Postgres database.

Local non-Docker mode uses SQLite by default when `DATABASE_URL` is unset, but Docker Compose is the recommended operating mode.

## Daily Commands

Start:

```bash
docker compose up -d --build
```

Apply migrations:

```bash
docker compose exec web flask --app app db upgrade
```

Show service status:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f web worker scheduler redis db
```

Restart a worker after code changes:

```bash
docker compose restart worker
```

Stop without deleting data:

```bash
docker compose down
```

## Health and Monitoring

Use:

- `/operations`: human-readable operations page.
- `/healthz`: deployment health check.
- `/status/<job_id>`: channel job status.
- `/api/channel-jobs/<job_id>`: JSON channel job status.

`/healthz` returns:

- `200` when database and Redis are reachable.
- `503` when a core dependency is unavailable.

Check common signals:

- Redis reachable.
- Queue depth is not growing unexpectedly.
- Worker count is greater than zero.
- Recent failures are understood.
- Collection runs have expected item counts.
- Quota estimates are within budget.

## Scheduler

The scheduler registers a daily tracked-channel scrape job:

- cron: `0 0 * * *`
- job ID: `daily-tracked-channels-scrape`
- queue: `RQ_QUEUE_NAME`

Tracked-channel collection uses:

```env
TRACKED_CHANNEL_MAX_VIDEOS=50
```

If scheduler behavior looks wrong:

```bash
docker compose logs --tail=200 scheduler
docker compose restart scheduler
```

## Worker Troubleshooting

If jobs do not start:

```bash
docker compose ps
docker compose logs --tail=200 worker redis web
```

Check:

- Redis container is running.
- Worker container is running.
- `RQ_QUEUE_NAME` matches between web, worker, and scheduler.
- `REDIS_URL` points to `redis://redis:6379/0` in Compose.
- YouTube API key is configured in web and worker.

If jobs fail partially:

1. Open `/operations`.
2. Inspect recent failed or partial runs.
3. Check worker logs.
4. Confirm YouTube quota and API key status.
5. Re-run with a smaller max video count if needed.

## Quota Management

Important settings:

```env
YOUTUBE_DAILY_QUOTA_BUDGET=10000
DEFAULT_COLLECTION_MAX_VIDEOS=50
TRACKED_CHANNEL_MAX_VIDEOS=50
```

Collection cost is estimated and stored in `collection_runs.quota_estimate`.

General guidance:

- Start with 50 videos per channel for new niches.
- Avoid large tracked-channel lists until the scheduler is stable.
- Keep transcript fetching disabled unless needed.
- Prefer uploads-playlist collection over search when possible.
- Watch daily quota usage when running multiple channel jobs.

## Backup and Restore

Create backup directory:

```bash
mkdir -p backups
```

Postgres backup:

```bash
docker compose exec -T db pg_dump -U baroo -d baroo_db > "backups/baroo_db_$(date +%Y%m%d_%H%M%S).sql"
```

Postgres restore:

```bash
docker compose exec -T db psql -U baroo -d baroo_db < backups/baroo_db.sql
```

SQLite backup:

```bash
cp data/videos.db "backups/videos_$(date +%Y%m%d_%H%M%S).db"
```

Research export backup:

- Download `/export/research.zip`.
- Download `/export/research.jsonl`.
- Download `/export?format=xlsx`.

Export backups are analysis artifacts, not full operational database restores.

## Migrations

Run migrations:

```bash
docker compose exec web flask --app app db upgrade
```

Local migration smoke:

```bash
DATABASE_URL=sqlite:////tmp/youtube_migration_smoke.db .venv/bin/flask --app app db upgrade
```

Before production migrations:

1. Create a DB backup.
2. Run migration on a copy if possible.
3. Apply during a quiet period.
4. Check `/operations`.

## Auth and Secrets

For private local use, admin auth is optional.

For hosted use:

- Set `SECRET_KEY`.
- Set `ADMIN_PASSWORD_HASH`.
- Do not commit `.env`.
- Do not store OAuth tokens in the database.
- Keep `YOUTUBE_API_KEY` and OAuth credentials out of logs.

Generate an admin password hash:

```bash
python - <<'PY'
from werkzeug.security import generate_password_hash
print(generate_password_hash("replace-this-password"))
PY
```

## Common Problems

### `YouTube API key is not configured`

Set `YOUTUBE_API_KEY` in `.env`, then restart:

```bash
docker compose restart web worker scheduler
```

### `Background queue is unavailable`

Redis or RQ worker is unavailable.

```bash
docker compose ps
docker compose logs --tail=200 redis worker
```

### `Job not found`

The job may have expired after `CHANNEL_JOB_RESULT_TTL_SECONDS`, or web/worker may be using different Redis instances.

### Slow UI

- Use `/data` pagination rather than exports for inspection.
- Keep large exports filtered where possible.
- Use Postgres for large datasets.
- Avoid collecting transcripts by default.

### Large Database

- Keep backups.
- Use Postgres in Compose/cloud.
- Avoid storing image blobs in the database.
- Keep thumbnail cache files outside git.

## Verification Gate

Before deploying code changes:

```bash
.venv/bin/black --check .
.venv/bin/ruff check .
.venv/bin/bandit -c bandit.yaml -r .
.venv/bin/pytest tests/ -q
DATABASE_URL=sqlite:////tmp/youtube_migration_smoke.db .venv/bin/flask --app app db upgrade
docker compose config
git diff --check
```

# Diagnostic Report - 2026-05-15

This report documents why many pages and background services are failing in the local Docker Compose app.

I did not apply migrations to the main Docker Postgres database while diagnosing. I only ran read-only checks against the main database, plus disposable migration smoke tests against temporary SQLite and Postgres databases.

## Executive Summary

The main problem is a stale Docker Postgres schema combined with a Fedora SELinux bind-mount labeling bug in `docker-compose.yml`.

The app code expects the Alembic head revision:

```text
4e5f60718293
```

The running Docker database is still at:

```text
0d2f4f59d9ab
```

That means the running code is querying tables and columns that do not exist yet, including:

- `collection_runs`
- `video_labels`
- `videos.youtube_channel_id`
- `videos.thumbnail_url`

The documented migration command fails because `web` cannot read `/app/migrations/env.py` inside the container:

```text
PermissionError: [Errno 13] Permission denied: 'migrations/env.py'
```

This is caused by using the private SELinux mount flag `:Z` for the same host paths across multiple containers:

- [docker-compose.yml](/home/kawa/YouTube/docker-compose.yml:34)
- [docker-compose.yml](/home/kawa/YouTube/docker-compose.yml:74)
- [docker-compose.yml](/home/kawa/YouTube/docker-compose.yml:112)

On Fedora, `:Z` gives the bind mount a private MCS label for one container. Because `web`, `worker`, and `scheduler` all mount the same `data/` and `migrations/` paths with `:Z`, whichever container relabels last can make the mount unreadable to the others.

## Current Service State

`docker compose ps` shows all services are up:

```text
youtube-web        Up, port 5000 published
youtube-worker     Up
youtube-scheduler  Up
youtube-redis      Up
youtube-db         Up
```

So this is not a simple "containers are down" issue.

## Failing Pages

I checked these routes against `http://localhost:5000`:

```text
/healthz           500
/dashboard         500
/collect           200
/operations        500
/data?view=videos  200
/labeling          500
/analysis          500
/packaging         500
/theses            500
/rights            500
/owned             500
/exports           200
/settings          200
```

The pages that do not query the newer research schema can still render. Pages that touch the newer tables fail.

## Log Findings

The web logs show schema mismatch errors:

```text
psycopg2.errors.UndefinedTable: relation "video_labels" does not exist
psycopg2.errors.UndefinedColumn: column videos.youtube_channel_id does not exist
```

The worker logs show background channel jobs failing before collection starts:

```text
psycopg2.errors.UndefinedTable: relation "collection_runs" does not exist
```

That maps directly to the newer models in [models.py](/home/kawa/YouTube/models.py:223) and [models.py](/home/kawa/YouTube/models.py:333), which are not present in the current Docker database.

## Database State

Main Docker Postgres tables currently present:

```text
alembic_version
channel_history
channel_videos
channels
video_history
videos
```

Current migration version:

```text
0d2f4f59d9ab
```

Expected head:

```text
4e5f60718293
```

The missing schema starts at migration:

```text
0d2f4f59d9ab -> 9b7d2f4a6c31, add research engine schema
```

That migration creates `collection_runs`, `video_labels`, `video_snapshots`, `channel_snapshots`, derived metric tables, and the newer channel/video columns.

## Why `flask db upgrade` Fails

Inside `web`, root cannot read the mounted migrations directory:

```text
ls: cannot access '/app/migrations/env.py': Permission denied
migrations/env.py PermissionError [Errno 13] Permission denied
```

Host-side Unix permissions are normal:

```text
-rw-r--r-- kawa:kawa migrations/env.py
```

The actual issue is SELinux labeling. The host `migrations/` path is labeled for the scheduler container category, while `web` has a different container category. That is why the same file is readable from `scheduler` but not from `web`.

`web` also cannot write to `/app/data`, so local SQLite/dev data access would be affected by the same problem:

```text
PermissionError [Errno 13] Permission denied: '/app/data/.codex_perm_probe'
```

## Migration File Health

The Alembic files themselves are valid in clean databases.

Checks run:

```text
63 passed, 44 warnings
```

Fresh SQLite migration smoke test:

```text
upgrade base -> 4e5f60718293 succeeded
```

Fresh temporary Postgres migration smoke test:

```text
upgrade base -> 4e5f60718293 succeeded
```

So the migration failure is environmental, not a broken Alembic script.

## YouTube API Key Findings

The `.env` file has a configured-looking YouTube API key:

```text
configured=True
starts_with_AIza=True
has_braces=False
contains_space=False
```

I made one minimal `videos.list` request using the configured key. Google returned:

```text
status 200
items 1
```

So the current key is accepted by the YouTube Data API at the time of this check.

Important: the key was pasted into chat. Treat it as exposed. Rotate it in Google Cloud, then update `.env`.

Official Google docs:

- YouTube Data API setup: https://developers.google.com/youtube/v3/getting-started
- Create/manage API keys: https://docs.cloud.google.com/api-keys/docs/create-manage-api-keys
- Restrict API keys: https://docs.cloud.google.com/api-keys/docs/add-restrictions-api-keys

Recommended key setup:

1. Go to Google Cloud Console.
2. Select or create a project.
3. Enable `YouTube Data API v3`.
4. Create an API key under APIs & Services credentials.
5. Restrict the key to `YouTube Data API v3`.
6. For local server use, consider application restrictions carefully. If you add IP restrictions, include the public IP that Google sees for your machine/server.
7. Put the new key in `.env` as `YOUTUBE_API_KEY=...`.
8. Restart the app containers.

## Other Issues Found

### `/healthz` can crash instead of reporting unhealthy

[routes.py](/home/kawa/YouTube/routes.py:192) calls `health_payload()`, which calls `operations_summary()`. `operations_summary()` checks database reachability, but it also queries `CollectionRun` unguarded in [operations.py](/home/kawa/YouTube/operations.py:23). When the schema is stale, `/healthz` returns `500` instead of a structured unhealthy response.

This is not the root cause, but it makes diagnosis harder.

### README/operations docs recommend the broken migration command

Both docs tell you to run:

```bash
docker compose exec web flask --app app db upgrade
```

Locations:

- [README.md](/home/kawa/YouTube/README.md:103)
- [docs/operations.md](/home/kawa/YouTube/docs/operations.md:25)

That command is correct in principle, but currently fails because `web` cannot read `migrations/`.

### Flask-Limiter uses in-memory storage

Logs show:

```text
Using the in-memory storage for tracking rate limits
```

This is acceptable for local development, but not production. It is not causing the current page failures.

### Redis host warning

Redis logs warn that host memory overcommit is disabled:

```text
Memory overcommit must be enabled
```

This is not causing the current schema errors, but it can cause Redis background saves to fail under memory pressure.

### `SECRET_KEY` is too short

The current `.env` has a configured `SECRET_KEY`, but it is only 4 characters long. That is weak for Flask session signing. Use a long random value for any real use.

## Recommended Recovery Plan

Back up the current Postgres database first:

```bash
mkdir -p backups
docker compose exec -T db pg_dump -U baroo -d baroo_db > backups/baroo_db_before_migration_2026-05-15.sql
```

Fix the SELinux bind-mount issue by changing shared bind mounts from private `:Z` to shared `:z` in `docker-compose.yml`:

```yaml
- ./data:/app/data:z
- ./migrations:/app/migrations:z
```

Do that for `web`, `worker`, and `scheduler`.

Then recreate the containers so Docker relabels the mounts consistently:

```bash
docker compose down
docker compose up -d --build
```

Verify `web` can read migrations:

```bash
docker compose exec web sh -lc 'python - <<PY
from pathlib import Path
print(Path("migrations/env.py").exists())
print(Path("migrations/env.py").read_text()[:20])
PY'
```

Run migrations:

```bash
docker compose exec web flask --app app db upgrade
```

Confirm the database is at head:

```bash
docker compose exec web flask --app app db current
docker compose exec web flask --app app db heads
```

Restart app services after migration:

```bash
docker compose restart web worker scheduler
```

Check routes:

```bash
curl -i http://localhost:5000/healthz
curl -i http://localhost:5000/dashboard
curl -i http://localhost:5000/operations
```

If old failed RQ jobs remain, inspect `/operations` after the schema is fixed, then requeue or clear failed jobs as appropriate.

## Short-Term Workaround

Right now, the scheduler container can read `migrations/`, so this may work as an emergency workaround:

```bash
docker compose exec scheduler flask --app app db upgrade
```

Use the backup command first. This workaround depends on the current SELinux label state and is not a real fix; recreating containers may change which service can read the mounted path.

## Priority Fix List

1. Change shared bind mounts from `:Z` to `:z` or remove unnecessary shared bind mounts.
2. Back up and migrate the Docker Postgres database to `4e5f60718293`.
3. Rotate the exposed YouTube API key and update `.env`.
4. Replace the short `SECRET_KEY` with a long random value.
5. Make `/healthz` robust when schema checks fail.
6. Update README and operations docs after the Compose mount fix.

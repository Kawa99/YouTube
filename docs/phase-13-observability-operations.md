# Phase 13: Observability, Reliability, and Operations

Phase 13 adds first-pass operational visibility for local and cloud deployment.

## Implemented

- `/operations` shows:
  - database reachability
  - Redis reachability
  - RQ queue depth
  - worker heartbeat count and worker states when available
  - recent failed or partial collection runs
  - recent collection runs
- `/healthz` returns JSON health for deployment checks.
- The dashboard continues to surface failed/partial collection runs for researcher visibility.

## Health Semantics

`/healthz` returns:

- `200` when the database and Redis are reachable.
- `503` when either core dependency is unavailable.

The worker count can be zero while the endpoint still returns dependency status. This allows a process manager or cloud health check to distinguish app dependency health from worker-capacity warnings.

## Existing Reliability Hooks

The collection pipeline already records:

- collection run ID
- run status
- start and completion timestamps
- quota estimate
- items found/saved/failed
- error summary
- job metadata for queued/running/completed channel jobs

## Backup and Restore

For local SQLite:

```bash
cp data/videos.db "data/videos-$(date +%Y%m%d-%H%M%S).db"
```

For Docker Postgres:

```bash
docker compose exec db pg_dump -U baroo -d baroo_db > backups/baroo_db.sql
docker compose exec -T db psql -U baroo -d baroo_db < backups/baroo_db.sql
```

Research exports are also valid backup artifacts for analysis:

- `/export/research.zip`
- `/export/research.jsonl`
- `/export?format=xlsx`

## Remaining Future Work

- Persist structured log correlation IDs for every queued job.
- Add retry-failed-items workflow from the operations page.
- Add scheduler heartbeat persistence.
- Add backup automation for cloud deployments.

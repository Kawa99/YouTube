# Baroo YouTube Tracker

Baroo is a Flask, Redis, RQ, and Postgres/SQLite research engine for finding, validating, and tracking profitable long-form YouTube channel opportunities. It is built for faceless-channel research: collect public competitor data, label videos manually, compute outlier metrics, form content theses, map monetization paths, track owned-channel experiments, and export analysis-ready datasets.

## What It Does

- Collects public YouTube video and channel metadata through the YouTube Data API.
- Stores normalized channels, videos, snapshots, raw collection metadata, labels, derived metrics, theses, monetization evidence, rights records, and owned-channel experiment data.
- Separates public competitor data from private owned-channel analytics.
- Provides task-oriented UI pages for collection, labeling, packaging analysis, thesis validation, rights checks, owned analytics, exports, operations, and settings.
- Produces CSV, XLSX, ZIP, and JSONL exports for notebooks and the research repo.

## Main Workflows

Use these pages during normal research:

- `/dashboard`: current research status, label coverage, failed jobs, top outliers, candidate theses.
- `/collect`: single-video and channel collection entry point.
- `/channel`: channel job queue/status page.
- `/data?view=videos`: paginated stored videos.
- `/data?view=channels`: paginated stored channels.
- `/labeling`: manual review and controlled labels.
- `/analysis`: recompute and review derived market metrics.
- `/packaging`: title/thumbnail pattern research and packaging experiments.
- `/theses`: content thesis, evidence, scorecard, monetization, and red-team workflow.
- `/rights`: asset ledger, rights checklist, and disclosure records.
- `/owned`: owned-channel analytics, retention diagnostics, and 24h/7d/30d experiment checkpoints.
- `/exports`: full and filtered research exports.
- `/operations`: Redis, DB, queue, worker, and recent failure visibility.
- `/settings`: runtime configuration visibility.

Legacy direct routes still work:

- `/`: single-video scraper.
- `/export?format=csv`: full operational CSV export.
- `/export?format=xlsx`: full operational Excel export.
- `/export/research.zip`: analysis-ready research ZIP.
- `/export/research.jsonl`: streaming research JSONL.
- `/healthz`: JSON health check.

## Prerequisites

- Docker and Docker Compose plugin.
- A YouTube Data API v3 key.
- Git.
- Optional for local non-Docker work: Python matching the project environment and virtualenv support.

## Configure Environment

Create `.env`:

```bash
cp .env.example .env
```

Required for collection:

```env
YOUTUBE_API_KEY=your_youtube_data_api_v3_key
SECRET_KEY=change-this-in-real-environments
```

Useful runtime settings:

```env
RQ_QUEUE_NAME=channel-scrape
CHANNEL_JOB_TIMEOUT_SECONDS=7200
CHANNEL_JOB_RESULT_TTL_SECONDS=86400
TRACKED_CHANNEL_MAX_VIDEOS=50
VIDEO_SAVE_COMMIT_INTERVAL=50
TRANSCRIPTS_ENABLED=false
TRANSCRIPT_FETCH_MODE=manual
YOUTUBE_DAILY_QUOTA_BUDGET=10000
```

Optional private-use authentication:

```env
ADMIN_PASSWORD=
ADMIN_PASSWORD_HASH=
```

If either admin value is set, private pages require `/login`. Prefer `ADMIN_PASSWORD_HASH` for hosted use.

Owned analytics metadata:

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
OWNED_ANALYTICS_TOKEN_SECRET_BACKEND=external
```

Raw OAuth tokens must live in an external secret backend; this app stores only `token_secret_ref`.

## Run With Docker Compose

Start the full stack:

```bash
docker compose up -d --build
```

Apply migrations if needed:

```bash
docker compose exec web flask --app app db upgrade
```

Open:

- `http://localhost:5000/dashboard`
- `http://localhost:5000/collect`
- `http://localhost:5000/operations`

Watch services:

```bash
docker compose ps
docker compose logs -f web worker scheduler redis db
```

Stop without deleting data:

```bash
docker compose down
```

Do not run `docker compose down -v` unless you intentionally want to delete Docker volumes.

## Development Loop

For fast local iteration, use the dev override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Then:

- Template and app edits reload in the web container.
- Worker code changes need `docker compose restart worker`.
- Dependency changes need a rebuild.

Local non-Docker path:

```bash
python -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app db upgrade
.venv/bin/python worker.py
.venv/bin/python app.py
```

Docker Compose is the preferred path because it includes Redis, worker, scheduler, and Postgres.

## Collection Modes

Single video:

1. Open `/collect` or `/`.
2. Paste a supported YouTube video URL.
3. Fetch metadata.
4. Save to database.

Channel:

1. Open `/collect` or `/channel`.
2. Paste a channel URL.
3. Set max videos, usually 50 to 200 for first-pass research.
4. Queue the job.
5. Watch status on `/channel` or `/operations`.

Tracked channels:

- Mark channels as tracked from channel detail/API workflows.
- Scheduler queues tracked-channel collection using `TRACKED_CHANNEL_MAX_VIDEOS`.
- Use `/operations` to inspect queue and worker state.

Transcript collection:

- `TRANSCRIPTS_ENABLED=false` by default because market mapping usually does not need transcripts.
- Use `TRANSCRIPT_FETCH_MODE=manual` unless a specific workflow needs transcripts.

## Labeling Workflow

1. Collect enough videos for a niche sample.
2. Open `/labeling?mode=unlabeled`.
3. Label niche, format, faceless status, AI visibility, visual style, packaging pattern, title pattern, thumbnail pattern, topic type, production complexity, policy risk, and confidence.
4. Use bulk labeling only for fields that are truly shared across selected videos.
5. Recompute metrics on `/analysis` after enough labels and snapshots exist.

Manual labels are intentionally human-reviewed. They should not be treated as automated ground truth.

## Research Workflow

The recommended loop is:

1. Choose seed channels.
2. Collect 50 to 200 recent long-form videos per channel.
3. Label videos and channels.
4. Recompute derived metrics.
5. Inspect outliers and repeated topic/format patterns.
6. Create content theses.
7. Add evidence, monetization maps, and red-team reviews.
8. Build packaging experiments.
9. Use rights checks before production.
10. Track owned-channel pilots at 24h, 7d, and 30d.
11. Export datasets and cite limitations in findings.

Detailed guide: `docs/research-workflow.md`.

## Export Workflow

Use `/exports` for:

- full operational CSV
- full operational XLSX
- research ZIP
- research JSONL
- filtered research ZIP

Research ZIP contains schema-aligned CSV files plus generated `data_dictionary.md`. See `docs/data-dictionary.md` for the stable export map.

Null handling:

- CSV exports serialize nulls as empty cells.
- JSONL exports serialize values through the same export serializer and include a `dataset` field.
- Datetimes are ISO formatted.

## Operations

Use `/operations` and `/healthz` to check:

- database reachability
- Redis reachability
- queue depth
- worker heartbeat count
- recent collection runs
- failed or partial runs

Backup examples and troubleshooting live in `docs/operations.md`.

## Quality Gate

Before committing changes:

```bash
.venv/bin/black --check .
.venv/bin/ruff check .
.venv/bin/bandit -c bandit.yaml -r .
.venv/bin/pytest tests/ -q
DATABASE_URL=sqlite:////tmp/youtube_migration_smoke.db .venv/bin/flask --app app db upgrade
docker compose config
git diff --check
```

CI runs formatting, linting, Bandit, tests, and migration smoke checks on `main`, `master`, and `research-engine`.

## Troubleshooting

`YouTube API key is not configured`

- Set `YOUTUBE_API_KEY` in `.env`.
- Restart web and worker containers after changing `.env`.

`Background queue is unavailable`

```bash
docker compose ps
docker compose logs --tail=200 redis worker web
```

Usually Redis or the worker is down, or `REDIS_URL` differs between services.

`Job not found`

- Job metadata may have expired after `CHANNEL_JOB_RESULT_TTL_SECONDS`.
- Confirm web and worker use the same Redis instance and queue name.

No videos found for a channel:

- Verify the channel URL resolves to a real channel.
- Check YouTube API quota.
- Try a canonical `/channel/UC...` URL.

Slow exports:

- Use filtered research exports where possible.
- Keep the database on Postgres for larger datasets.
- Avoid automatic large thumbnail downloads until storage policy is implemented.

## Documentation Index

Start here:

- `docs/research-engine-prd.md`
- `docs/research-workflow.md`
- `docs/data-dictionary.md`
- `docs/operations.md`
- `docs/research-schema-map.md`
- `docs/adr/`
- `docs/phase-0-baseline.md`
- `docs/phase-2-research-schema.md`
- `docs/phase-3-collection-engine.md`
- `docs/phase-4-research-exports.md`
- `docs/phase-5-manual-labeling.md`
- `docs/phase-6-derived-metrics.md`
- `docs/phase-7-packaging-lab.md`
- `docs/phase-8-thesis-workflow.md`
- `docs/phase-9-monetization-mapping.md`
- `docs/phase-10-asset-rights-compliance.md`
- `docs/phase-11-owned-analytics.md`
- `docs/phase-12-ui-ux-restructure.md`
- `docs/phase-13-observability-operations.md`
- `docs/phase-14-security-compliance.md`
- `docs/phase-15-performance-scale.md`
- `docs/phase-16-testing-strategy.md`
- `docs/phase-17-documentation.md`

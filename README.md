# YouTube Tracker (Flask + RQ + Redis)

This webapp does three core things:

- Single-video scrape: fetches video metadata + transcript from a YouTube URL.
- Channel scrape: queues a background job (RQ) to process many channel videos.
- Data operations: browse stored data (`/data`) and export CSV/XLSX (`/export`).

## Stack and runtime

- Flask web app (`app.py`, `routes.py`)
- Background worker (`worker.py`) running RQ jobs from `tasks.py`
- Redis queue + job status store
- SQLite database at `./data/videos.db`
- Docker Compose services:
  - `web` (Gunicorn in production-like mode)
  - `worker` (RQ worker process)
  - `redis` (Redis 7)

## 1. Prerequisites

- Docker + Docker Compose plugin (`docker compose`)
- A YouTube Data API v3 key

## 2. Configure environment

Create or edit `.env` in the project root:

```env
YOUTUBE_API_KEY=your_real_youtube_api_key
RQ_QUEUE_NAME=channel-scrape
SECRET_KEY=change-this-in-real-environments
CHANNEL_JOB_TIMEOUT_SECONDS=7200
CHANNEL_JOB_RESULT_TTL_SECONDS=86400
```

Notes:

- `YOUTUBE_API_KEY` is required.
- In Compose, app + worker use `REDIS_URL=redis://redis:6379/0` internally.

## 3. Production-like workflow (stable)

Use `docker-compose.yml` only for production-like local runs (no source bind-mount, stable runtime behavior):

```bash
docker compose up -d --build
```

Open:

- `http://localhost:5000` (Single Video page)
- `http://localhost:5000/channel` (Channel Scraper page)
- `http://localhost:5000/data` (Data Viewer page)

Useful commands:

```bash
docker compose ps
docker compose logs -f web worker redis
docker compose down
```

## 4. Development workflow (fast iteration)

Professionals split **dev workflow** from **prod workflow**.

**How experts do it**
1. Keep your current `docker-compose.yml` as production-like (stable, no live code mount).
2. Add a `docker-compose.dev.yml` override for local development (bind-mount source code + debug reload).
3. Build once, then iterate without rebuilding on every file change.
4. Rebuild only when dependencies or Dockerfile change.
5. Never use `down -v` unless you intentionally want to wipe state.

**What this looks like in practice**

`docker-compose.dev.yml`:
```yaml
services:
  web:
    volumes:
      - ./:/app
      - ./data:/app/data:Z
    environment:
      FLASK_DEBUG: "1"
    command: flask --app app run --host=0.0.0.0 --port=5000 --debug

  worker:
    volumes:
      - ./:/app
      - ./data:/app/data:Z
```

Run dev:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Daily loop:

- Edit code/templates/css/js: no rebuild needed (web auto-reloads).
- If worker code changed:
```bash
docker compose restart worker
```
- If `requirements.txt` changed:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build web worker
```

**Key rule**
Use `down -v` only for deliberate full reset.
For normal work, this is overkill and slows you down massively.

## 5. Exact webapp usage

### Single Video page (`/`)

1. Paste a valid YouTube video URL:
   - `https://www.youtube.com/watch?v=...`
   - `https://youtu.be/...`
   - `https://www.youtube.com/shorts/...`
2. Click **Extract Data**.
3. Review returned fields:
   - video id, title, description, channel username
   - views, likes, comments, posted date, length
   - transcript (or fallback message if unavailable)
4. Click **Save to Database** to persist/update the record.

### Channel Scraper page (`/channel`)

1. Enter a channel URL (supported examples):
   - `https://www.youtube.com/@channelname`
   - `https://www.youtube.com/channel/UC...`
   - `https://www.youtube.com/c/channelname`
   - `https://www.youtube.com/user/username`
2. Set **Maximum Videos to Process** (`1` to `1000`).
3. Submit to queue a background job.
4. Watch live job status (polled every 2 seconds): queued/running/completed/failed.
5. Progress panel shows total, inserted, failed, skipped, and current video id.

### Data Viewer page (`/data`)

- Shows totals for videos/channels/history.
- Supports table tabs, pagination, sorting, manual refresh, and auto-refresh (5s).
- Uses API endpoint: `/api/data?page=1&limit=25&sort_column=saved_at&sort_direction=desc`

### Exports

- CSV: `/export?format=csv`
- Excel: `/export?format=xlsx`

## 6. Operational behavior and persistence

- SQLite file persists in `./data/videos.db` (mounted into `web` and `worker`).
- Redis data persists in Docker volume `redis-data`.
- Channel jobs run in `worker`; status is fetched from:
  - `/status/<job_id>`
  - `/api/channel-jobs/<job_id>`

## 7. Rebuild vs restart rules

- Restart only:
  - app/worker Python code changes in dev mode (hot reload for `web`, manual restart for `worker`)
- Rebuild required:
  - `requirements.txt` changes
  - `Dockerfile` changes
  - base image or system package changes

## 8. Troubleshooting

### `Background queue is unavailable`

Check:

```bash
docker compose ps
docker compose logs --tail=200 worker redis
```

Usually caused by Redis/worker not running or wrong env values.

### Channel job finds no videos

- Verify `YOUTUBE_API_KEY` is valid and has quota.
- Verify the channel URL resolves to a real channel.

### `Job not found`

- Job may have expired based on `CHANNEL_JOB_RESULT_TTL_SECONDS`.
- Ensure `web` and `worker` are on the same Redis instance/queue.

## 9. Optional local (non-Docker) run

If needed:

```bash
python -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
python worker.py
python app.py
```

For this repository, Docker Compose is the recommended path.

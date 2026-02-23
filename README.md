# YouTube Scraper Flask App

This project is a Flask web app that can:

- Fetch details for a single YouTube video.
- Queue and process channel scraping jobs in the background using Redis + RQ.
- Save video/channel data into a SQLite database.
- Export stored data as CSV or XLSX.

## 1. Prerequisites

Before starting, make sure you have:

- Python 3.10+ installed
- `pip` installed
- Redis server installed (or Docker)
- Internet access (for YouTube API calls and Python package install)

## 2. Get a YouTube API Key (Google Cloud)

You must create and configure a YouTube Data API v3 key.

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Open `APIs & Services` -> `Library`.
4. Search for `YouTube Data API v3` and click `Enable`.
5. Open `APIs & Services` -> `Credentials`.
6. Click `Create Credentials` -> `API key`.
7. Copy the API key value.
8. (Recommended) Click your key and configure restrictions:
   - Application restriction:
     - For local/server use: `IP addresses` (or temporarily unrestricted while testing).
     - Avoid `HTTP referrers` only, because the worker is server-side.
   - API restrictions:
     - Restrict to `YouTube Data API v3`.
9. Save changes.

## 3. Create a Virtual Environment

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 4. Set Environment Variables

This app reads configuration from environment variables.

Required:

- `YOUTUBE_API_KEY`

Recommended:

- `REDIS_URL` (default: `redis://localhost:6379/0`)
- `RQ_QUEUE_NAME` (default: `channel-scrape`)
- `SECRET_KEY` (default fallback exists, but set your own)
- `CHANNEL_JOB_TIMEOUT_SECONDS` (default: `7200`)
- `CHANNEL_JOB_RESULT_TTL_SECONDS` (default: `86400`)

Example:

```bash
export YOUTUBE_API_KEY='YOUR_REAL_YOUTUBE_API_KEY'
export REDIS_URL='redis://localhost:6379/0'
export RQ_QUEUE_NAME='channel-scrape'
export SECRET_KEY='change-this-in-real-environments'
```

Important:

- Run these exports in every terminal where you start:
  - Flask app
  - RQ worker

## 5. Start Redis

Option A: local Redis service

```bash
redis-server
```

Option B: Docker

```bash
docker run --rm -p 6379:6379 redis:7
```

## 6. Start the RQ Worker

Open a new terminal:

```bash
cd /path/to/YouTube
source .venv/bin/activate
export YOUTUBE_API_KEY='YOUR_REAL_YOUTUBE_API_KEY'
export REDIS_URL='redis://localhost:6379/0'
export RQ_QUEUE_NAME='channel-scrape'
python worker.py
```

Keep this terminal running.

## 7. Start the Flask Web App

Open another terminal:

```bash
cd /path/to/YouTube
source .venv/bin/activate
export YOUTUBE_API_KEY='YOUR_REAL_YOUTUBE_API_KEY'
export REDIS_URL='redis://localhost:6379/0'
export RQ_QUEUE_NAME='channel-scrape'
python app.py
```

Then open:

- `http://127.0.0.1:5000`

## 8. Verify Setup Quickly

In your active venv:

```bash
python -c "from redis import Redis; import os; print(Redis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0')).ping())"
```

Expected output:

- `True`

Check API key is visible:

```bash
python -c "import os; print(bool(os.getenv('YOUTUBE_API_KEY')))"
```

Expected output:

- `True`

## 9. How to Use the App

### Single video scrape

1. Open the home page.
2. Paste a YouTube video URL (`youtube.com/watch...` or `youtu.be/...`).
3. Submit to fetch metadata and transcript.

### Channel scrape (background job)

1. Open `/channel`.
2. Paste a YouTube channel URL.
3. Choose max videos.
4. Submit.
5. Watch progress update until job completes.

## 10. Common Issues and Fixes

### Error: `Background queue is unavailable. Ensure Redis and the RQ worker are running.`

Causes:

- Redis is not running.
- Worker is not running.
- `redis` / `rq` not installed in active venv.
- `REDIS_URL` mismatch between app and worker.

Fix:

1. Ensure Redis is running.
2. Ensure `python worker.py` is running in another terminal.
3. Ensure both terminals use the same venv and env vars.
4. Reinstall dependencies:

```bash
pip install -r requirements.txt
```

### Job completes instantly with `No videos found for this channel.`

Causes:

- `YOUTUBE_API_KEY` missing in worker terminal.
- Key restrictions or quota issues in Google Cloud.
- Invalid channel URL or unresolvable channel identifier.

Fix:

1. Confirm worker terminal has `YOUTUBE_API_KEY` exported.
2. Verify key restrictions allow server-side requests.
3. Ensure YouTube Data API v3 is enabled in the same GCP project.
4. Verify quota is available.

### `Job not found` in status endpoint

Causes:

- Worker/app connected to different Redis DB/URL/queue.
- Job expired (`CHANNEL_JOB_RESULT_TTL_SECONDS` too low).

Fix:

1. Confirm same `REDIS_URL` and `RQ_QUEUE_NAME` in app and worker.
2. Increase result TTL if needed.

## 11. Stopping Services

1. Stop Flask app: `Ctrl+C`
2. Stop worker: `Ctrl+C`
3. Stop Redis:
   - Local server: `Ctrl+C`
   - Docker: `Ctrl+C` (container exits with `--rm`)

Deactivate venv:

```bash
deactivate
```

## 12. Project Notes

- API and YouTube communication logic is in `youtube_api.py`.
- Background queue/job logic is in `tasks.py`.
- Worker entrypoint is `worker.py`.
- Main web app is `app.py`.

# Phase 3 Collection Engine

Phase 3 makes YouTube collection batch-oriented, observable, and safer for market research runs.

## Service Layer

- `services/youtube/client.py` owns request timeout, retry, backoff, quota accounting, and structured API errors.
- `services/youtube/parsers.py` converts YouTube API payloads into normalized app records.
- `services/youtube/quota.py` centralizes quota-cost estimates.
- `services/youtube/errors.py` defines retryable, quota, auth, not-found, and bad-request failures.

The legacy `youtube_api.py` module remains as the app-facing facade so existing routes and tests do not need to import lower-level services directly.

## Batched Collection

- `get_videos_data()` batches video IDs into `videos.list` calls with up to 50 IDs per request.
- Channel details are fetched in batches with `channels.list`.
- Channel jobs now fetch all video metadata in batches before saving rows.
- Repeated runs continue to upsert normalized records and append new snapshots.

## Transcript Policy

Transcript collection is optional:

- `TRANSCRIPT_FETCH_MODE=never` always skips transcripts.
- `TRANSCRIPT_FETCH_MODE=manual` uses `TRANSCRIPTS_ENABLED`.
- `TRANSCRIPT_FETCH_MODE=always` fetches transcripts during collection.

Single-video UI refreshes preserve backward-compatible transcript fetching by passing an explicit single-video default.

## Collection Runs

Each channel background job creates a `collection_runs` row with:

- `run_type=channel_uploads`
- status lifecycle: `running`, `completed`, `partial`, or `failed`
- requested limit, quota estimate, counts found/saved/failed
- completion timestamp and error summary when applicable

Saved video and channel snapshots receive the `collection_run_id`, which keeps repeated runs idempotent and traceable.

## Sampling Metadata

Channel uploads and fallback search preserve sampling metadata in `api_raw_payloads` with `endpoint=sampling_metadata`. Keyword search and manual URL list helpers return the same metadata shape for future UI routes.

## Quota Visibility

The channel job status API now returns:

- `collection_run_id`
- `quota_estimate`
- `quota_warning`

The channel job page shows those fields while work is running.

# Phase 15: Performance and Scale

Phase 15 improves the app's behavior as the database grows into thousands of channels, videos, snapshots, labels, and derived metrics.

## Implemented

- Added database indexes for common research filters, joins, and sort paths:
  - video/channel YouTube IDs
  - `published_at`
  - `collection_run_id`
  - `snapshot_at`
  - label `niche` and `format`
  - derived metric `outlier_flag`
  - composite snapshot and label indexes used by common analysis queries
- Kept the existing `/api/data` server-side pagination path and added a large-fixture regression test.
- Added chunked video-save commits for channel collection jobs.
- Kept exports streaming or writing to temporary files instead of building a single in-memory response.
- Documented thumbnail-cache policy.

## Collection Commit Policy

Channel jobs now save video rows with bounded transaction batches controlled by:

```env
VIDEO_SAVE_COMMIT_INTERVAL=50
```

This reduces one-commit-per-video overhead while keeping transactions small. If a batch commit fails, the worker rolls back that batch and retries rows individually, so one bad row does not hide the rest.

## Thumbnail Cache Policy

Thumbnail caching should stay analysis-focused:

- Store only the selected thumbnail URL and optional local path.
- Cache one inspection-friendly size per video, not every YouTube size.
- Keep generated/cache files out of git.
- Prefer filesystem/object storage paths over storing image blobs in the database.
- Add cleanup rules before enabling automatic large-scale thumbnail downloads.

## Current Limits

The UI is expected to remain usable at 10,000 video records through server-side pagination. Heavy analytics still require careful query design, especially for cross-table exports and derived metric recomputation.

## Remaining Future Work

- Add query-plan checks for the most expensive reports once real production data exists.
- Batch insert snapshots more aggressively if channel jobs become DB-bound.
- Add export progress reporting for very large research archives.

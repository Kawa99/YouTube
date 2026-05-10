# Phase 2 Research Schema

Phase 2 adds the normalized persistence layer needed to turn the tracker into a repeatable YouTube market research engine. The existing UI-facing tables remain in place so current routes, exports, and tests keep working while richer research workflows move onto the new tables.

## Compatibility Path

- `channels.subscribers`, `videos.views`, `videos.likes`, `videos.comments`, `video_history`, `channel_history`, and `video_metadata_history` are retained for the current app surface.
- New writes through `save_video` also populate `channel_snapshots`, `video_snapshots`, and `video_metadata_changes`.
- `video_length` remains for display compatibility, but new analysis should use `videos.duration_seconds`.
- `description` and `transcript` remain compatibility fields; new analysis should use `description_full`, `description_excerpt`, `transcript_text`, and `transcript_status`.

## New Research Tables

- `collection_runs`: records what collection job ran, its input, quota estimate, status, and item counts.
- `api_raw_payloads`: stores raw API responses separately from normalized records.
- `video_snapshots`: append-only public video metric snapshots.
- `channel_snapshots`: append-only public channel metric snapshots.
- `video_metadata_changes`: field-level metadata history for titles, thumbnails, and future packaging fields.
- `video_labels`: human-reviewed labels for niche, format, faceless status, monetization signals, policy risk, and production complexity.
- `channel_labels`: channel-level thesis labels for niche, format, sponsor fit, policy risk, and complexity.
- `video_derived_metrics`: repeatable computed metrics such as views per day, relative performance, duration bucket, and outlier flag.

## Migration Backfill

The Phase 2 migration backfills:

- `channels.subscriber_count` from `channels.subscribers`.
- `channels.handle` from `channel_username` when it is an `@handle`.
- `videos.description_full`, `description_excerpt`, `transcript_text`, and `transcript_status` from existing compatibility fields.
- `video_snapshots` from existing `video_history` rows.
- `channel_snapshots` from current channel rows.
- `video_metadata_changes` from existing title and thumbnail history rows.

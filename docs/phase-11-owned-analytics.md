# Phase 11: Owned-Channel Analytics Integration

Phase 11 adds an owned-channel analytics workspace without weakening the public-vs-private data boundary.

## Scope

- `/owned` records private metrics only for channels the operator owns or has explicit authorization to access.
- Public competitor research remains limited to public YouTube API data, manual labels, snapshots, derived metrics, packaging observations, thesis evidence, monetization signals, and rights/compliance metadata.
- Raw OAuth access tokens and refresh tokens are not stored in the application database. The app stores only a `token_secret_ref` that should point to an external secret store.

## OAuth Metadata

The workspace records credential metadata in `owned_analytics_credentials`:

- linked channel
- Google account email
- documented scopes
- external secret reference
- status and revocation timestamp
- notes

Required scopes are:

- `https://www.googleapis.com/auth/yt-analytics.readonly`
- `https://www.googleapis.com/auth/youtube.readonly`

Environment variables reserved for the eventual OAuth flow:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `OWNED_ANALYTICS_TOKEN_SECRET_BACKEND`

## Owned Analytics Tables

`owned_video_analytics` stores dated YouTube Studio metrics:

- views
- impressions
- impression CTR
- average view duration
- average view percentage
- watch time minutes
- subscribers gained
- estimated revenue
- traffic source type
- source

`retention_diagnostics` maps owned metrics to the retention review protocol:

- CTR
- AVD
- APV
- impressions
- dominant traffic source
- retention pattern
- likely cause
- supporting evidence
- next change

Supported patterns:

- `early_cliff`
- `slow_bleed`
- `mid_video_drop`
- `spike_replay`
- `high_ctr_low_retention`
- `low_ctr_high_retention`
- `low_impressions_good_response`
- `good_search_weak_browse`
- `unknown`

## Experiments

`experiments` stores owned-channel test design:

- hypothesis
- variable tested
- title variant
- thumbnail variant
- publish date
- success metric
- production hours and cost
- decision

`experiment_checkpoints` supports the launch-review windows:

- `24h`
- `7d`
- `30d`

Checkpoint metrics include views, impressions, CTR, AVD, APV, watch time, subscribers gained, and traffic source.

## Exports

The full CSV/XLSX export includes the new tables. Research ZIP and JSONL exports include:

- `owned_analytics_credentials.csv`
- `owned_video_analytics.csv`
- `retention_diagnostics.csv`
- `experiments.csv`
- `experiment_checkpoints.csv`

The data dictionary marks owned analytics as `owned_private` and credential rows as `auth_metadata`.

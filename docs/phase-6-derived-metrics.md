# Phase 6 Derived Metrics

Phase 6 turns raw snapshots and manual labels into reproducible decision-support metrics.

## Computation

`metrics.compute_derived_metrics()` reads:

- latest video snapshots
- channel snapshots/subscriber counts captured on video snapshots
- recent videos on the same channel
- manual labels

It writes:

- `video_derived_metrics`
- `channel_derived_summaries`

The active algorithm version is stored on every row as `derived-metrics-v1` unless overridden by `DERIVED_METRICS_ALGORITHM_VERSION`.

## Video Metrics

The metric job computes:

- age days
- views per day
- views per subscriber
- channel recent median views
- relative performance
- duration bucket
- performance tier
- outlier flag
- like rate
- comment rate
- engagement rate

## Outlier Rules

Thresholds are configurable through environment variables:

- `DERIVED_BREAKOUT_THRESHOLD`, default `5`
- `DERIVED_OUTLIER_THRESHOLD`, default `2`
- `DERIVED_UNDERPERFORMER_THRESHOLD`, default `0.5`

Initial classification:

- `breakout`: relative performance >= 5x
- `outlier`: relative performance >= 2x
- `normal`: 0.5x to 2x
- `underperformer`: < 0.5x
- `unknown`: no usable baseline

## Channel Summaries

The job also computes channel-level summaries:

- median recent views
- median views per subscriber
- upload cadence in days
- average duration
- top outlier topics
- format distribution
- packaging pattern distribution
- visible monetization signals

## UI

`/analysis` shows derived analysis separately from raw data:

- top outlier videos
- strong channels by median views per subscriber
- repeated outlier topic clusters
- formats with high relative performance
- packaging patterns linked to outliers
- under-served candidate thesis clusters from repeated outlier label combinations

`POST /analysis/compute` recomputes derived metrics.

# ADR 0005: Derive Metrics in Repeatable Jobs

## Status

Accepted

## Context

The research engine needs metrics such as age days, views per day, views per subscriber, channel recent median views, relative performance, duration buckets, and outlier flags. These are not raw API facts. They depend on formulas, thresholds, snapshots, and algorithm versions.

If these values are computed ad hoc in UI queries, they will be difficult to reproduce and audit.

## Decision

Compute derived metrics in explicit, repeatable jobs and store the results with an algorithm version.

Planned output table:

```text
video_derived_metrics
```

Required properties:

- input snapshot timestamp;
- computed timestamp;
- algorithm version;
- raw inputs remain unchanged;
- recomputation is possible when logic changes.

## Consequences

### Positive

- Makes synthesis reproducible.
- Keeps raw and derived data separate.
- Allows threshold changes without losing past logic.
- Makes outlier claims easier to audit.

### Negative

- Adds another job type.
- Derived metrics can become stale if not recomputed after new snapshots.
- Requires UI to show metric freshness.

## Implementation Notes

- Start with simple documented thresholds.
- Do not optimize formulas prematurely.
- Store null when a metric cannot be computed honestly.
- Avoid hiding low-confidence metrics behind precise-looking decimals.

## Alternatives Considered

### Compute metrics only in exports

Rejected. UI needs the same values as exports.

### Compute metrics live in every query

Rejected. It makes behavior harder to test and reproduce.

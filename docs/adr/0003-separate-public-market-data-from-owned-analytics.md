# ADR 0003: Separate Public Market Data From Owned Analytics

## Status

Accepted

## Context

Competitor research can only use public YouTube data. Owned-channel analytics, such as CTR, AVD, APV, retention, traffic source, and estimated revenue, are private metrics available only for channels the operator owns or can access through authorized OAuth scopes.

Mixing these data types would create misleading analysis and could cause the UI or exports to imply that competitor private metrics are known.

## Decision

Use separate entities and workflows for:

- public market data;
- owned-channel analytics;
- experiment checkpoints.

Public market data includes:

- public channel metadata;
- public video metadata;
- public view/like/comment counts;
- snapshots;
- manual labels;
- derived public metrics.

Owned analytics includes:

- impressions;
- CTR;
- average view duration;
- average percentage viewed;
- watch time;
- traffic source data;
- estimated revenue where available;
- experiment checkpoints.

## Consequences

### Positive

- Prevents false precision.
- Keeps competitor analysis legally and methodologically clean.
- Makes owned launch experiments more trustworthy.
- Aligns with the research repo's evidence standards.

### Negative

- Requires duplicate-looking tables for some video metrics.
- UI must clearly explain why some metrics only exist for owned videos.

## Implementation Notes

- Public video IDs may later link to owned video analytics when the operator's channel is tracked.
- Owned analytics ingestion should require explicit authorization and documented scopes.
- Exports must label owned analytics separately.

## Alternatives Considered

### One combined metrics table

Rejected. It would invite competitor/owned metric confusion.

### Skip owned analytics

Rejected. The eventual channel launch needs retention and experiment diagnostics.

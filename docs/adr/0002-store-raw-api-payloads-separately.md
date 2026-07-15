# ADR 0002: Store Raw API Payloads Separately

## Status

Accepted

## Context

The research engine must preserve evidence and support later reprocessing. YouTube API responses can include fields that are not used immediately but may become useful later. At the same time, normalized app tables should not become opaque JSON blobs.

## Decision

Store raw API payloads in a separate table, behind a configuration flag.

Planned table:

```text
api_raw_payloads
```

Expected fields:

- source
- endpoint
- external_id
- payload_json
- collection_run_id
- created_at

Normalized tables remain the primary query path for UI, exports, and derived metrics.

## Consequences

### Positive

- Preserves source evidence.
- Enables reprocessing when parsing logic changes.
- Keeps normalized tables clean.
- Helps debug API parsing bugs.

### Negative

- Increases database size.
- Requires retention policy later.
- Payloads may include fields we do not need.

## Implementation Notes

- Default can remain disabled for lightweight local use.
- Collection runs should record whether raw payload storage was enabled.
- Raw payloads should not be exported by default.
- Never store secrets or request credentials in payload rows.

## Alternatives Considered

### Store only normalized fields

Rejected. It loses evidence and makes future parser changes harder to verify.

### Store JSON directly on channels/videos

Rejected. It mixes raw evidence with normalized state and complicates UI queries.

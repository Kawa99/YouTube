# ADR 0004: Manual Labels Are Human-Reviewed

## Status

Accepted

## Context

The YouTube API cannot reliably determine whether a video is faceless, AI-assisted, documentary-style, policy-risky, sponsor-friendly, visually generic, or well-packaged. These are research judgments. Automation can assist, but it should not silently become ground truth.

## Decision

Manual labels are first-class, human-reviewed records.

Initial label domains:

- niche;
- format;
- faceless status;
- visible AI use;
- visual style;
- title pattern;
- thumbnail pattern;
- packaging pattern;
- topic type;
- production complexity;
- policy risk;
- monetization signals;
- notes.

Labels must track:

- reviewer;
- review status;
- review timestamp;
- optional confidence;
- later audit history.

## Consequences

### Positive

- Improves dataset trust.
- Makes subjective judgments explicit.
- Supports consistent exports and synthesis.
- Avoids overclaiming from automated classifiers.

### Negative

- Requires human labor.
- Labels may drift without controlled vocabularies.
- Reviewer disagreement may need future adjudication.

## Implementation Notes

- Controlled vocabularies should be short and documented.
- The UI should optimize for fast labeling.
- Bulk labeling is acceptable, but must remain auditable.
- AI-assisted labeling can be added later as suggestions only.

## Alternatives Considered

### Fully automated labeling

Rejected. It would create brittle and overconfident research output.

### Free-text notes only

Rejected. Free text is hard to aggregate, filter, and export reliably.

# Research Engine Product Requirements

## Purpose

The YouTube tracker should become the measurement layer for deciding which faceless long-form YouTube channels to launch, how to validate them, and when to stop or scale.

The product is not a generic YouTube scraper. It is a research operations tool that turns public YouTube metadata, manual review, derived metrics, and owned-channel analytics into launch decisions.

## Problem

The faceless YouTube automation niche is noisy, incentive-corrupted, and full of weak claims. Articles, creator anecdotes, and tool-vendor posts are not enough to choose a channel concept. We need a system that can:

- collect comparable public data from real channels and videos;
- preserve how the data was collected;
- support human labels for things the API cannot know;
- compute reproducible metrics that identify outliers and patterns;
- export evidence into the research repo;
- later ingest owned-channel analytics for actual experiments.

## Users

### Researcher

The researcher studies niches, channels, formats, topics, packaging patterns, and monetization signals.

Needs:

- collect competitor channel/video data;
- review and label videos quickly;
- see data freshness and collection method;
- find outlier topics and formats;
- export datasets with clear schemas;
- avoid mistaking biased samples for market truth.

### Channel operator

The channel operator uses research output to choose a launch thesis, produce pilots, and evaluate early videos.

Needs:

- know which channel theses have evidence;
- track pilot ideas, packaging, and production cost;
- understand policy, rights, and monetization risk;
- compare early owned-channel performance against expectations;
- decide continue / pivot / stop.

### Future analyst

The future analyst may revisit old datasets, compare new collection runs, or reproduce a synthesis.

Needs:

- stable exports;
- data dictionary;
- collection-run metadata;
- raw payload access where enabled;
- versioned derived-metric logic;
- audit trail for manual labels.

## Product Principles

- Preserve raw, normalized, manual, and derived data separately.
- Treat API data as evidence with sampling caveats, not truth about the whole market.
- Make manual judgment structured and auditable.
- Keep competitor public data separate from owned-channel private analytics.
- Do not fabricate unavailable metrics such as competitor CTR, retention, RPM, or revenue.
- Make uncertainty visible in the UI and exports.

## Core Workflows

### Workflow 1: Collect competitor channels

Inputs:

- channel URL;
- channel ID;
- handle;
- seed list;
- tracked-channel refresh job.

System behavior:

- resolve canonical YouTube channel ID;
- collect channel snippet/statistics/content details;
- record a `collection_run`;
- upsert normalized channel;
- append channel snapshot;
- store raw API payload if enabled;
- surface resolution failures and quota errors.

Output:

- normalized channel record;
- channel snapshot;
- collection-run record;
- optional raw payload.

### Workflow 2: Collect recent videos

Inputs:

- channel uploads playlist;
- keyword/search query;
- manual video URL list;
- max video count;
- date filters where supported;
- transcript mode.

System behavior:

- collect video IDs;
- batch fetch video details;
- upsert normalized video records;
- append video snapshots;
- record metadata changes;
- optionally fetch transcripts;
- associate all work with a collection run.

Output:

- videos;
- snapshots;
- metadata changes;
- collection-run summary;
- optional transcripts/raw payloads.

### Workflow 3: Label videos manually

Inputs:

- collected videos;
- reviewer judgment.

Labels:

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

System behavior:

- validate controlled vocabularies;
- save label history;
- mark review status;
- support fast review workflow.

Output:

- auditable manual labels suitable for export and derived analysis.

### Workflow 4: Compute derived metrics

Inputs:

- normalized video/channel records;
- latest snapshots;
- manual labels;
- configurable thresholds.

Metrics:

- age days;
- views per day;
- views per subscriber;
- channel recent median views;
- relative performance;
- duration bucket;
- engagement rate;
- outlier flag;
- upload cadence summary.

System behavior:

- compute metrics in repeatable jobs;
- record algorithm version;
- do not overwrite raw facts;
- allow recomputation when logic changes.

Output:

- derived metrics table and market-opportunity views.

### Workflow 5: Export research tables

Outputs:

- schema-aligned CSV bundle;
- optional JSONL;
- data dictionary;
- collection-run metadata;
- raw/manual/derived separation.

Export must align with the research repo's `16-channel-database-schema.md` and support filtering by niche, format, date, collection run, and label status.

### Workflow 6: Track owned-channel experiments

This is post-launch. It must be separate from competitor public data.

Inputs:

- owned YouTube Analytics data where authorized;
- manual experiment hypotheses;
- title/thumbnail variants;
- 24h, 7d, 30d checkpoints.

System behavior:

- store owned metrics separately;
- support retention diagnostics;
- link metrics to experiments;
- never imply those metrics are available for competitors.

Output:

- experiment decision records;
- continue / pivot / stop evidence.

## Functional Requirements

### Collection

- The system must support channel URL, channel ID, handle, keyword search, and manual video-list collection.
- The system must record collection-run metadata for every collection action.
- The system must batch video API requests where supported.
- The system must make quota and API errors visible.
- Transcript fetching must be optional and non-blocking.

### Storage

- The system must store canonical YouTube IDs.
- The system must keep snapshots append-only.
- The system must store metadata changes for title and thumbnail updates.
- The system must support raw API payload storage behind a flag.
- The system must distinguish public competitor data from owned analytics.

### Labeling

- The system must support controlled vocabularies.
- The system must support unlabeled / reviewed / needs-review statuses.
- The system must preserve who labeled an item and when.
- The system must make label changes auditable.

### Analysis

- The system must compute relative performance against channel baseline.
- The system must flag outliers using documented thresholds.
- The system must store metric algorithm version.
- The system must distinguish raw metrics from derived metrics in UI and export.

### Export

- The system must export normalized, snapshot, manual-label, derived-metric, and collection-run tables.
- Exports must include a data dictionary.
- Exports must be compatible with the research repository's market-lab files.

### Operations

- The system must run locally through Docker Compose.
- The system must support a local non-Docker path.
- Background jobs must expose status and failures.
- Migrations must run from an empty database in CI.

## Non-Functional Requirements

### Reliability

- Duplicate collection should not create duplicate channels or videos.
- Partial failures should preserve successful records and identify failed items.
- Repeated collection should append snapshots.

### Observability

- Collection runs must include status, counts, timestamps, and error summaries.
- API failures must be logged with endpoint and reason.
- Worker/scheduler health should be visible in a later phase.

### Security

- API keys and OAuth credentials must not be committed.
- `.env.example` must include placeholders only.
- If the tool is exposed beyond localhost, authentication is required.

### Performance

- The app should remain usable with at least 10,000 video records.
- Exports should stream or write temp files rather than loading entire datasets into memory where practical.
- Collection should avoid one API call per video where batching is available.

### Data Quality

- Raw public values, manual labels, and derived metrics must not be conflated.
- Missing or hidden API fields must be stored as null or explicit unknowns, not guessed.
- Sampling method must be recorded.

## Out of Scope

- Scraping private competitor analytics.
- Circumventing YouTube API limits.
- Shorts-first strategy.
- Automated legal advice.
- Fully automated AI judgment of channel viability.
- Guaranteeing monetization outcomes.

## Success Metrics

### MVP success

- Collect 30-50 competitor channels and 300-500 recent long-form videos.
- Label top 100 videos by relative performance.
- Export schema-aligned research tables.
- Identify at least 3 candidate channel theses backed by dataset evidence.

### Full system success

- Support hundreds of channels and thousands of videos.
- Show repeatable topic/packaging outliers.
- Track pilot videos and owned-channel experiments.
- Feed a final launch decision in the research repo's synthesis process.

## Key Risks

- API search results are biased and unstable.
- Manual labeling can drift without controlled vocabularies.
- Derived metrics can create false precision.
- Transcript fetching can create operational drag.
- Local Python version mismatch can create dependency friction.
- UI complexity can grow faster than research value.

## Phase 1 Decisions

The initial architecture decisions are recorded in:

- `docs/adr/0001-use-sqlalchemy-and-postgres-compatible-schema.md`
- `docs/adr/0002-store-raw-api-payloads-separately.md`
- `docs/adr/0003-separate-public-market-data-from-owned-analytics.md`
- `docs/adr/0004-manual-labels-are-human-reviewed.md`
- `docs/adr/0005-derive-metrics-in-repeatable-jobs.md`

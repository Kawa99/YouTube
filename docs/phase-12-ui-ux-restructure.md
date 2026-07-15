# Phase 12: UI/UX Restructure

Phase 12 starts moving the product from scraper-first pages toward research-operations navigation.

## Implemented

- Added `/dashboard` for the research operations overview.
- Added `/collect` as the task-oriented collection entry point for single-video and channel collection.
- Added `/exports` as a dedicated export workspace with research ZIP filters.
- Added `/settings` for read-only runtime configuration visibility.
- Reworked the primary navigation around research tasks:
  - Dashboard
  - Collect
  - Channels
  - Videos
  - Labeling
  - Packaging Lab
  - Theses
  - Rights
  - Experiments
  - Exports
  - Settings
- Added query-driven default tabs for `/data?view=channels` and `/data?view=videos`.

## Dashboard Inputs

The dashboard summarizes:

- total channels
- total videos
- labeled/unlabeled count
- label coverage
- collection-run count
- failed/partial collection runs
- logged quota estimate total
- top outlier videos
- active candidate theses

## Remaining Future Work

The current implementation avoids breaking established workflows. Later phases can deepen the UI with:

- saved data-table filters
- column visibility presets
- thumbnail grid review
- keyboard-driven labeling shortcuts
- richer freshness indicators per video/channel row
- unified keyword and bulk-channel collection forms once collection support exists in the backend

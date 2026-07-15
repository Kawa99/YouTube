# Phase 18: Final Integration With This Research Repo

Phase 18 connects Baroo exports to the faceless YouTube research repo so findings and launch decisions can cite internal datasets consistently.

## Implemented

- Added an explicit research export schema version: `1.0.0`.
- Added `manifest.json` to `/export/research.zip`.
- Added `schema_version` to every `/export/research.jsonl` row.
- Added a JSONL manifest row as the first line of the streaming export.
- Added `docs/export-import-contract.md`.
- Updated `docs/data-dictionary.md` to describe the manifest and version fields.
- Updated tests to assert the ZIP manifest and JSONL schema version.

## Research Repo Integration

The companion research repo now defines:

- where dataset snapshots should be placed
- how snapshots should be cited in findings
- how limitations and sampling bias should be recorded
- how synthesis should combine market evidence, theses, niche scores, red-team results, pilots, and launch decisions

## Acceptance Criteria Mapping

- Research outputs can cite internal datasets as evidence: covered by manifest/versioned exports and research repo citation templates.
- Dataset limitations are explicit: covered by research repo dataset-backed finding template and ingestion guide.
- Launch decisions are based on policy, economics, market evidence, and pilot results: covered by the updated synthesis template and launch decision framework.

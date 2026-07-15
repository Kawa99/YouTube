# Phase 7 Packaging Lab

Phase 7 makes title and thumbnail analysis systematic without adding image ML.

## Thumbnail Handling

Videos now store:

- `thumbnail_url`
- `thumbnail_quality`
- `thumbnail_cached_path`
- `thumbnail_phash`

`thumbnail_cached_path` and `thumbnail_phash` are optional placeholders for a later thumbnail cache or perceptual-hash job.

## Packaging Labels

Manual video labels now include:

- title pattern
- thumbnail pattern
- viewer promise
- curiosity type
- clarity score
- specificity score
- honesty score
- visual readability score
- differentiation score

Scores are integer values from 1 to 5. Pattern labels use the taxonomy from `17-packaging-lab.md`.

## Comparison View

`/packaging` shows:

- thumbnail grid
- titles
- channel identity
- relative performance
- channel baseline
- title, thumbnail, and promise labels
- top packaging pattern combinations by niche

The view can be filtered by niche.

## Metadata Change Analysis

The packaging lab reads `video_metadata_changes` for title and thumbnail changes and compares the nearest available snapshots before and after each change.

If snapshots are missing on one side of the change, the performance delta remains blank instead of guessing.

## Pilot Workspace

`/packaging` also stores pilot packaging experiments for future owned videos:

- working title
- niche and format
- title candidates
- thumbnail concepts
- experiment log URL
- final title
- final choice reason
- status

Large thumbnail files are intentionally not stored in the database in this phase.

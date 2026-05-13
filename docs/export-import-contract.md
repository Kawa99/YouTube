# Export/Import Contract

This contract defines how Baroo exports research datasets for the faceless YouTube research repo and downstream notebooks.

## Version

Current schema version: `1.0.0`

The version is exposed in:

- `manifest.json` inside `/export/research.zip`
- every object emitted by `/export/research.jsonl`
- generated `data_dictionary.md` inside the ZIP

Increment the version when filenames, columns, field meanings, null handling, or date serialization change.

## ZIP Contract

Endpoint:

```text
/export/research.zip
```

Filtered endpoint examples:

```text
/export/research.zip?niche=finance
/export/research.zip?channel=@example&date_from=2026-05-01&date_to=2026-05-13
/export/research.zip?collection_run=12&outlier_flag=true
```

Required supporting files:

- `manifest.json`
- `data_dictionary.md`

Required CSV files:

- `channels.csv`
- `videos.csv`
- `manual_labels.csv`
- `snapshots.csv`
- `derived_metrics.csv`
- `content_theses.csv`
- `thesis_evidence.csv`
- `thesis_topics.csv`
- `thesis_scores.csv`
- `red_team_reviews.csv`
- `thesis_monetization_maps.csv`
- `sponsor_evidence.csv`
- `affiliate_product_evidence.csv`
- `assets.csv`
- `video_assets.csv`
- `video_rights_checklists.csv`
- `video_disclosures.csv`
- `owned_analytics_credentials.csv`
- `owned_video_analytics.csv`
- `retention_diagnostics.csv`
- `experiments.csv`
- `experiment_checkpoints.csv`
- `collection_runs.csv`

Every required CSV is present even when it has only a header row.

## Manifest

`manifest.json` is the import entry point. It contains:

- `schema_version`: contract version.
- `generated_at`: ISO 8601 export timestamp.
- `files`: ordered list of dataset filenames and exact columns.
- `supporting_files`: non-CSV files included in the ZIP.
- `filters`: export filters that were active.
- `null_handling`: serialization rule for missing values.
- `date_format`: date/datetime serialization rule.
- `jsonl_contract`: streaming export metadata.

Importers should validate the manifest before loading CSV files. If a required file or expected column is missing, treat the snapshot as incompatible rather than silently accepting partial data.

## JSONL Contract

Endpoint:

```text
/export/research.jsonl
```

Rules:

- One JSON object per line.
- First object has `dataset` set to `manifest`.
- Every object includes `schema_version`.
- Dataset rows include `dataset` plus the same fields documented for the matching CSV.
- JSON nulls are used for missing values.

## Serialization

- CSV nulls are empty cells.
- JSONL nulls are JSON null.
- Dates and datetimes are ISO 8601 strings.
- CSV list/object fields are JSON strings.
- Public competitor datasets and private owned-channel analytics datasets are separate.
- Owned analytics must only be exported for channels the operator owns or is authorized to access.

## Compatibility Rule

The exact CSV headers are defined in `export.py` as `RESEARCH_HEADERS`. The generated manifest and generated data dictionary are produced from the same source. Documentation must be updated in the same change as any contract-breaking export change.

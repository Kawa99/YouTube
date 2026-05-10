# Phase 4 Research Exports

Phase 4 makes app data directly portable into the research repository and external analysis tools.

## Existing Export

`/export?format=csv` and `/export?format=xlsx` now include the core research tables:

- `channels`
- `videos`
- `channel_snapshots`
- `video_snapshots`
- `video_metadata_changes`
- `video_labels`
- `channel_labels`
- `collection_runs`
- `video_derived_metrics`

Compatibility tables are still included for the current UI and older analysis scripts.

## Research ZIP

`/export/research.zip` returns:

- `channels.csv`
- `videos.csv`
- `manual_labels.csv`
- `snapshots.csv`
- `derived_metrics.csv`
- `collection_runs.csv`
- `data_dictionary.md`

These files are schema-aligned for downstream analysis instead of direct table dumps.

## JSONL

`/export/research.jsonl` emits one JSON object per row with a `dataset` field. This is useful for scripts, notebook ingestion, and LLM-assisted research workflows.

## Filters

Research exports accept:

- `niche`
- `format`
- `channel`
- `date_from`
- `date_to`
- `collection_run`
- `labeled=true|false`
- `outlier_flag=true|false`

Examples:

```text
/export/research.zip?niche=finance&outlier_flag=true
/export/research.jsonl?channel=@competitor&collection_run=12
```

# Research Schema Map

This document maps the research repository's market-lab files to the YouTube tracker's planned application entities.

The source research repo is expected at:

```text
/home/kawa/faceless-youtube-research
```

## Mapping Principles

- API facts become normalized records and snapshots.
- Human judgments become manual labels.
- Calculated values become derived metrics with algorithm versions.
- Private owned-channel metrics stay separate from public competitor data.
- Export shape should match the research repo even if internal table names differ.

## Source File: `15-youtube-data-collection-plan.md`

### Research need

Collect comparable public channel/video data and preserve collection method.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Channel-level fields | `channels`, `channel_snapshots` | Canonical channel identity plus changing stats. |
| Video-level fields | `videos`, `video_snapshots` | Canonical video identity plus changing public stats. |
| Collection workflow | `collection_runs` | Records input, mode, counts, status, and errors. |
| API caution / sampling method | `collection_runs` fields | Query, search parameters, and source route must be recorded. |
| Raw source evidence | `api_raw_payloads` | Optional, config-gated payload storage. |

## Source File: `16-channel-database-schema.md`

### Research-to-app table map

| Research table | Planned app table(s) | Notes |
| --- | --- | --- |
| `channels` | `channels`, `channel_snapshots` | Separate stable identity from changing counts. |
| `videos` | `videos`, `video_snapshots` | Separate metadata from changing counts. |
| `manual_labels` | `video_labels`, `channel_labels` | Labels are reviewer-owned records. |
| `snapshots` | `video_snapshots`, `channel_snapshots` | App should keep channel and video snapshots separate. |
| `derived_metrics` | `video_derived_metrics`, later `channel_derived_metrics` | Store algorithm version and computed timestamp. |

### Current model gap

| Current field/entity | Gap | Phase 2 direction |
| --- | --- | --- |
| `Channel.channel_username` | Not canonical identity | Add `youtube_channel_id`, name, handle, URL fields. |
| `Video.video_length` | String format is analysis-hostile | Add `duration_seconds`. |
| `VideoHistory` | Good concept, limited naming/metadata | Normalize into `video_snapshots` or map compatibly. |
| `ChannelHistory` | Tracks only previous subscribers | Replace/extend with full `channel_snapshots`. |
| `VideoMetadataHistory` | Title/thumbnail only, fixed shape | Generalize into metadata-change rows. |

## Source File: `17-packaging-lab.md`

### Research need

Analyze title, thumbnail, topic framing, and viewer promise as a combined packaging unit.

### App entities

| Research field | Planned app entity | Notes |
| --- | --- | --- |
| Title pattern | `video_labels.title_pattern` | Controlled vocabulary. |
| Thumbnail pattern | `video_labels.thumbnail_pattern` | Controlled vocabulary. |
| Packaging pattern | `video_labels.packaging_pattern` | Combined package label. |
| Viewer promise | `video_labels.viewer_promise` or thesis evidence | May start as notes, then normalize. |
| Packaging scorecard | later `video_packaging_scores` or fields on `video_labels` | Do not overbuild before labeling workflow exists. |
| Test design | `experiments`, `experiment_variants` | Owned/pilot workflow, not competitor facts. |

## Source File: `18-audience-demand-map.md`

### Research need

Map viewer segments, viewer jobs, demand signals, and underserved gaps.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Audience segment | `audience_segments` | Phase 8. |
| Viewer jobs | controlled vocabulary | Can begin as thesis fields. |
| Demand evidence | `thesis_evidence` | Link channels/videos/sources to thesis. |
| Gap type | `content_theses` fields or labels | Used for launch reasoning. |

## Source File: `19-content-thesis-bank.md`

### Research need

Store repeatable channel theses, not just video ideas.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Channel thesis | `content_theses` | Core launch candidate entity. |
| First 10 videos | `thesis_topics` | Status can track idea/pilot/used/rejected. |
| First 50-topic backlog | `thesis_topics` | Needed for sustainability evidence. |
| Policy-risk argument | `content_theses.policy_risk_argument` | Human-authored. |
| Kill criteria | `content_theses.kill_criteria` or linked review | Can start as text. |

## Source File: `20-monetization-map.md`

### Research need

Separate Watch Page ads, sponsors, affiliates, fan funding, products, and services.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Revenue paths | `thesis_monetization_paths` | Phase 9. |
| Sponsor evidence | `sponsor_observations` | Link competitor videos/channels to observed sponsors. |
| Affiliate evidence | `affiliate_observations` | Link products/categories to thesis. |
| Scenario model | `thesis_economics_scenarios` | Keep assumptions explicit. |
| Brand-safety concerns | labels or monetization notes | Tie to policy/ad suitability risk. |

## Source File: `21-red-team-review.md`

### Research need

Stress-test candidate channel theses before launch.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Review target | `red_team_reviews` | Linked to thesis. |
| Core objections | `red_team_review_items` | Structured objections and severity. |
| Competitor challenge | `thesis_competitors` or review items | Link competitor channel evidence. |
| Failure pre-mortem | review text fields | Required before pilot. |
| Decision | `content_theses.status` transition | reject / revise / pilot. |

## Source File: `22-prelaunch-pilot-protocol.md`

### Research need

Validate workflow quality and cost before full channel launch.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Pilot package | `pilots` | Linked to thesis. |
| Outlines/scripts/thumbnails | `pilot_assets` or external links | Do not store large files in database initially. |
| Pilot scoring | `pilot_scores` | Structured 1-5 values. |
| Decision | `pilots.decision`, thesis status | Launch candidate / revise / reject. |

## Source File: `23-retention-diagnostics.md`

### Research need

Interpret owned-channel performance after publishing.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| CTR, AVD, APV, impressions | `owned_video_analytics` | Owned-channel only. |
| Retention pattern | `retention_diagnostics` | May be manual if API does not expose enough curve data. |
| 24h/7d/30d reviews | `experiment_checkpoints` | Linked to owned video/experiment. |
| Packaging/content mismatch | diagnostics notes | Human conclusion from metrics. |

## Source File: `24-asset-rights-ledger.md`

### Research need

Track rights and licensing for monetized/pilot production assets.

### App entities

| Research concept | Planned app entity | Notes |
| --- | --- | --- |
| Asset table | `assets` | Source, licensor, terms, proof. |
| Video asset relationship | `video_assets` | Many assets per video. |
| High-risk assets | asset risk fields | Flag before upload. |
| Rights checklist | `video_compliance_checks` | Phase 10. |
| Disclosure tracker | compliance fields | Sponsor, affiliate, synthetic content, attribution. |

## Export Contract

The app should eventually export:

- `channels.csv`
- `videos.csv`
- `manual_labels.csv`
- `snapshots.csv`
- `derived_metrics.csv`
- `collection_runs.csv`
- `data_dictionary.md`

Internal table names can be richer than the export names, but exports must preserve:

- stable IDs;
- collection dates;
- source/method;
- nulls for unavailable data;
- raw/manual/derived separation;
- controlled label values.

## Open Design Questions

- Should raw payload storage default to on for research mode or stay off until needed?
- Should `video_labels` allow multiple reviewers in Phase 5 or defer that to a later review/audit table?
- Should packaging scorecard values live directly on labels or in a separate `video_packaging_scores` table?
- Should content thesis workflow live in this app or remain partly in the research repo until after MVP?
- Which owned analytics fields are actually available through YouTube Analytics API for the operator's channel setup?

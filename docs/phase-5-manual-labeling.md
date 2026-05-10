# Phase 5 Manual Labeling

Phase 5 adds a human review workflow for turning raw YouTube metadata into auditable research labels.

## Reviewer UI

`/labeling` shows a review queue with:

- video thumbnail
- title
- channel
- views, subscribers, duration, and publish date
- description excerpt
- YouTube link
- editable labels
- queue status counts

Reviewers can save, save and move to the next unlabeled video, skip a video, or mark it as needing second review.

## Controlled Vocabularies

`label_vocabularies.py` defines allowed values for:

- niche
- format
- faceless status
- AI use visible
- visual style
- packaging pattern
- topic type
- production complexity
- policy risk
- review status

The route/service layer rejects unsupported values to prevent spelling drift in exports.

## Batch Labeling

The queue sidebar supports selecting videos and bulk applying a controlled label field. Bulk updates use the same validation and audit trail as single-video reviews.

## Audit Trail

`video_label_audits` stores:

- video label ID
- video ID
- action
- reviewer
- previous label values
- new label values
- label confidence
- changed timestamp

`video_labels.label_confidence` stores reviewer confidence on a 0 to 1 scale.

## Export Compatibility

Core exports include `video_label_audits`, and research exports include `label_confidence` in video and manual label datasets.

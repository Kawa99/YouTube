# Phase 8 Thesis Workflow

Phase 8 turns channel research into launch theses that can be scored, supported with evidence, red-teamed, and exported.

## Tables

- `content_theses`: the core channel thesis.
- `thesis_evidence`: channels, videos, links, and notes that support or weaken a thesis.
- `thesis_topics`: topic backlog and title angles for the thesis.
- `thesis_scores`: weighted niche scorecard rows from `10-niche-scoring-model.md`.
- `red_team_reviews`: structured review notes from `21-red-team-review.md`.

## Thesis Status

Allowed thesis statuses:

- `idea`
- `research`
- `pilot`
- `reject`
- `launch`

The `/theses` workspace can move a thesis through these statuses.

## Niche Scorecard

Scores use the weighted factors from the research repo:

- audience demand
- RPM potential
- policy safety
- differentiation
- production feasibility
- research/source availability
- evergreen value
- competition intensity
- sponsorship/affiliate fit
- thumbnail/title viability
- operator fit
- cost control

Each score is 1-5. The app stores score, weight, weighted score, evidence, and confidence.

## Red-Team Review

Red-team reviews store:

- reviewer
- decision under review
- core objections
- competitor challenges
- failure pre-mortem
- early warning signs
- preventive actions
- kill criteria
- decision
- decision rationale

The review is intentionally structured so weak ideas are rejected before pilot work.

## Export

The thesis tables are included in CSV/XLSX full exports and in the research ZIP/JSONL export.

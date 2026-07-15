# Phase 9 Monetization Mapping

Phase 9 makes each money path explicit for a content thesis.

## Tables

- `thesis_monetization_maps`: revenue paths and scenario assumptions per thesis.
- `sponsor_evidence`: observed sponsors, categories, competitor channel, video URL, niche fit, and brand-safety notes.
- `affiliate_product_evidence`: product categories, program/source, fit, audience intent, and disclosure concerns.

## Revenue Paths

Supported labels:

- `watch_page_ads`
- `sponsors`
- `affiliates`
- `memberships`
- `patreon`
- `newsletter`
- `digital_products`
- `consulting_services`
- `licensing`

## Scenario Model

Each monetization map stores separate assumptions for:

- conservative ad RPM
- base ad RPM
- upside ad RPM
- sponsor RPM equivalent
- affiliate RPM equivalent
- membership RPM equivalent
- product RPM equivalent
- break-even view count
- meaningful-income view count

The UI shows the blended base RPM equivalent, but the database keeps each component separate.

## Launch Gate

A thesis cannot move to `launch` status unless it has a monetization map with at least one revenue path and a primary revenue path.

## Export

Monetization maps, sponsor evidence, and affiliate/product evidence are included in full CSV/XLSX exports and research ZIP/JSONL exports.

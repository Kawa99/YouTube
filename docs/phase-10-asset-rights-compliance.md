# Phase 10 Asset Rights and Compliance

Phase 10 prevents rights and disclosure issues from reaching upload.

## Tables

- `assets`: source, licensor, license terms, monetized YouTube permission, proof, attribution, high-risk flag.
- `video_assets`: links assets to videos with intended use, attribution text, and rights decision.
- `video_rights_checklists`: upload-readiness checklist per video.
- `video_disclosures`: sponsor, affiliate, altered/synthetic, and music/license disclosure records.

## High-Risk Warnings

Assets can be manually flagged high risk. The app also automatically flags these asset types:

- archival video
- music
- voice clone
- screenshot

The `/rights` workspace lists high-risk assets separately so they are visible before upload.

## Ready-for-Upload Gate

A video cannot receive a `ready_for_upload` checklist unless:

- at least one asset is linked to the video
- every asset has a ledger row
- unclear assets are blocked
- attribution is captured
- terms allow monetized YouTube use
- every linked asset is marked `use`
- every linked asset has `monetized_youtube_allowed = yes`
- every linked asset has proof saved

This is the first-pass pilot safety gate. It does not replace legal review.

## Export

Assets, video assets, rights checklists, and disclosure records are included in full CSV/XLSX exports and research ZIP/JSONL exports.

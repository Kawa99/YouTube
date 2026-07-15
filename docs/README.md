# Documentation Index

This directory describes the research-engine evolution of the YouTube tracker.

## Current documents

- `production-readiness-remediation-execution-checklist-2026-07-15.md` is the authoritative remediation status ledger and acceptance checklist.
- `remediation/phase-0-containment-recovery-evidence-2026-07-15.md` records the current containment, backup, restore, environment, and regression evidence for the remediation Phase 0 gate.
- `phase-0-baseline.md` records the verified baseline before research-engine feature work.
- `phase-2-research-schema.md` documents the normalized schema and compatibility path.
- `phase-3-collection-engine.md` documents batched collection, quota visibility, and collection-run behavior.
- `phase-4-research-exports.md` documents schema-aligned ZIP/JSONL research exports.
- `phase-5-manual-labeling.md` documents reviewer UI, vocabularies, bulk labeling, and audit trail behavior.
- `phase-6-derived-metrics.md` documents derived metrics, outlier rules, and market analysis views.
- `phase-7-packaging-lab.md` documents systematic title and thumbnail packaging research.
- `phase-8-thesis-workflow.md` documents the content thesis, evidence, topic backlog, scorecard, and red-team workflow.
- `phase-9-monetization-mapping.md` documents explicit revenue paths, sponsor evidence, affiliate/product evidence, and launch gating.
- `phase-10-asset-rights-compliance.md` documents the asset ledger, rights checklist, disclosures, and upload-readiness gate.
- `phase-11-owned-analytics.md` documents owned-channel OAuth metadata, private Studio metrics, retention diagnostics, and 24h/7d/30d experiment checkpoints.
- `phase-12-ui-ux-restructure.md` documents the task-oriented dashboard, collection, exports, settings, and navigation updates.
- `phase-13-observability-operations.md` documents dependency health checks, operations visibility, and backup/restore commands.
- `phase-14-security-compliance.md` documents optional admin auth, secrets rules, and compliance guardrails.
- `phase-15-performance-scale.md` documents scale indexes, chunked collection commits, pagination expectations, and thumbnail-cache policy.
- `phase-16-testing-strategy.md` documents unit, integration, contract, migration, and UI test coverage.
- `phase-17-documentation.md` documents the README rewrite and the user-facing workflow, data dictionary, and operations guides.
- `phase-18-research-repo-integration.md` documents versioned exports and research repo integration.
- `research-workflow.md` explains the reproducible niche-research and launch-validation workflow.
- `data-dictionary.md` documents research export files, headers, semantics, and high-value fields.
- `export-import-contract.md` defines the versioned ZIP/JSONL contract for downstream research imports.
- `operations.md` covers Docker usage, scheduler/worker operations, health checks, backups, restore, and quota management.
- `research-engine-prd.md` defines the product requirements for market research and launch validation.
- `research-schema-map.md` maps the research repository's markdown schemas to app entities and future tables.
- `adr/` records architecture decisions that should guide implementation.

## Related source project

The research requirements come from `/home/kawa/faceless-youtube-research`, especially:

- `15-youtube-data-collection-plan.md`
- `16-channel-database-schema.md`
- `17-packaging-lab.md`
- `18-audience-demand-map.md`
- `19-content-thesis-bank.md`
- `20-monetization-map.md`
- `21-red-team-review.md`
- `22-prelaunch-pilot-protocol.md`
- `23-retention-diagnostics.md`
- `24-asset-rights-ledger.md`
- `25-youtube-tracker-engineering-plan.md`

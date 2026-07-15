# Phase 17: Documentation

Phase 17 turns the accumulated implementation notes into practical operating documentation.

## Implemented

- Rewrote the root `README.md` around:
  - purpose
  - setup
  - workflows
  - environment variables
  - collection modes
  - labeling workflow
  - export workflow
  - troubleshooting
- Added `docs/research-workflow.md`.
- Added `docs/data-dictionary.md`.
- Added `docs/operations.md`.
- Updated the docs index.

## Documentation Roles

- `README.md`: start here; run the system and understand the main workflows.
- `docs/research-workflow.md`: repeatable market research and launch-validation procedure.
- `docs/data-dictionary.md`: export filenames, headers, semantics, and high-value fields.
- `docs/operations.md`: Docker, scheduler, worker, health, backup, restore, quota, and troubleshooting.
- Phase docs: implementation history and rationale.
- ADRs: architecture decisions.

## Acceptance Criteria Mapping

- Future user can run the system from docs alone: covered by README and operations guide.
- Data fields are documented: covered by data dictionary and generated ZIP dictionary.
- Research workflow is reproducible: covered by research workflow guide.

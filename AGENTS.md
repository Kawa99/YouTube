# Repository Operating Instructions

These instructions apply to the entire repository. Follow them for every human
or automated change unless a more specific `AGENTS.md` is added below a
subdirectory.

## Supported environment

- Python 3.11 is the supported runtime.
- Docker Compose is the canonical local integration environment.
- PostgreSQL is the production database target.
- SQLite is supported only for the documented local and migration-smoke paths.
- Redis/RQ is required for background jobs.
- The default branch is `master`.

Do not silently introduce another runtime, database, queue, or package manager.
Record an ADR and update CI and the operating documentation when a supported
environment changes.

## Safe setup and startup

1. Copy `.env.example` to `.env` and replace placeholders locally. Never commit
   `.env` or print its values in logs, test output, screenshots, or evidence.
2. Validate configuration:

   ```bash
   docker compose config --quiet
   ```

3. Start the contained stack:

   ```bash
   docker compose up -d --build
   ```

   The web service must publish only `127.0.0.1:5000`. PostgreSQL and Redis must
   not publish host ports. The unattended scheduler is intentionally excluded
   from the default profile while the Phase 1 collection-correctness blockers
   remain open.

4. Apply migrations and verify health:

   ```bash
   docker compose exec -T web flask --app app db upgrade
   curl --fail --silent --show-error http://127.0.0.1:5000/healthz
   ```

5. Start scheduled collection only after an authorized review confirms that
   its current data-integrity and false-success risks are accepted:

   ```bash
   docker compose --profile scheduled-collection up -d scheduler
   ```

   Pause it with:

   ```bash
   docker compose --profile scheduled-collection stop scheduler
   ```

Do not use `docker compose down -v` unless the user explicitly authorizes
destruction of the named Docker volumes and a verified restore point exists.

## Required change workflow

1. Start from a clean `master` synchronized with `origin/master`.
2. Create a narrowly named task branch.
3. Reproduce or establish the pre-change behavior before editing.
4. Keep the diff limited to one checklist task or one inseparable change.
5. Preserve unrelated user changes and ignored runtime data.
6. Add positive, negative, boundary, and failure-path tests appropriate to the
   change. Add concurrency, replay, and migration tests when durable state or
   background work is involved.
7. Run focused checks during development and the full gate before completion.
8. Review the final diff and record exact evidence in the remediation ledger.
9. Merge or push only when every applicable acceptance criterion is evidenced.

Never weaken a test to make a change pass. Replace an obsolete test only when
the changed requirement and equal or stronger replacement coverage are clear.

## Canonical verification commands

Run the repository gate in the containerized Python 3.11 environment:

```bash
docker compose run --rm web black --check .
docker compose run --rm web ruff check .
docker compose run --rm web bandit -c bandit.yaml -r .
docker compose run --rm web pytest tests/ -v
docker compose config --quiet
git diff --check
```

For migration-affecting work, also run:

```bash
docker compose exec -T web flask --app app db current
docker compose exec -T web flask --app app db check
docker compose run --rm -e DATABASE_URL=sqlite:////tmp/youtube_migration_smoke.db web flask --app app db upgrade
```

`flask db check` is currently expected to expose the audited `MIG-002` drift
until that Phase 1 task is completed. Do not report the repository as fully
clean or hide that failure. A change must not introduce additional drift.

After container or runtime changes, rebuild and perform at least these smoke
checks:

```bash
docker compose up -d --build
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:5000/healthz
```

Confirm that the scheduler remains stopped unless the current task explicitly
authorizes scheduled collection.

## Database and migration rules

- Never edit a migration that may have been applied to persistent data. Create
  a new migration.
- Back up the target database before migration rehearsals.
- Test upgrade, transformed data invariants, and recovery on a disposable copy
  before touching persistent data.
- Test PostgreSQL for every persistence change. Test SQLite only when the
  affected workflow claims SQLite support.
- Never stamp a database, drop persistent data, truncate tables, or rewrite
  user data without explicit authorization.
- Keep migrations deterministic and free of network calls or application-side
  effects.

## Backup and recovery rules

- Store local operational backups only under ignored `backups/` paths with
  directories mode `0700` and files mode `0600`.
- Never commit database dumps, Redis snapshots, `.env`, tokens, credentials,
  private analytics, or raw customer/provider records.
- Use `pg_dump` custom archives for PostgreSQL and verify with `pg_restore
  --list` plus a disposable restore and row-count comparison.
- Use SQLite's `.backup` command, then verify `PRAGMA quick_check` and a
  schema-and-content hash on a disposable restore.
- Force and validate an RDB snapshot when Redis state is required, then restore
  it into an isolated portless Redis container and compare key counts without
  printing keys or values.
- Record checksums, schema revisions, counts, duration, permissions, and the
  recovery procedure. A backup without a tested restore is not complete.

## Security and privacy rules

- Never expose secret values through commands, diffs, fixtures, logs, telemetry,
  error messages, completion records, or prompts.
- Do not add real credentials to Compose files, images, source, or examples.
- Keep the web listener loopback-only until the authentication and network
  perimeter checklist tasks are complete.
- Treat public research data, private owned analytics, credential metadata,
  operational telemetry, and exports as separate trust classes.
- Do not rotate or revoke a real secret, change a production firewall, publish
  a service, or contact external users without explicit authorization.

## Remediation ledger

`docs/production-readiness-remediation-execution-checklist-2026-07-15.md` is the
authoritative status ledger. Work top to bottom, one task at a time. Check an
item only after its stated behavior is proven. Record blockers and leave the
item unchecked when verification is unavailable.

Use the comprehensive audit for finding evidence and the failure-mode playbook
for pre-mortems, fault injection, boundary cases, and debugging procedures.

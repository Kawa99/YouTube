# ADR 0001: Use SQLAlchemy and a Postgres-Compatible Schema

## Status

Accepted

## Context

The current application already uses Flask-SQLAlchemy, Flask-Migrate, Alembic, SQLite for local use, and Postgres in Docker Compose. The research-engine roadmap requires a more normalized schema with collection runs, snapshots, manual labels, derived metrics, experiments, and asset records.

The system must remain easy to run locally, but it also needs to handle larger datasets than the current lightweight tracker.

## Decision

Continue using SQLAlchemy models and Alembic migrations. Design new tables to be Postgres-compatible first, while keeping SQLite compatibility for local development and CI migration smoke tests.

Implementation rules:

- Use Alembic migrations for every schema change.
- Test migrations against SQLite in CI.
- Avoid migration operations that SQLite cannot execute directly unless using Alembic batch mode.
- Use canonical external IDs as unique business keys where available.
- Keep integer primary keys or UUIDs as internal implementation keys where helpful.
- Add explicit indexes for query-heavy fields.

## Consequences

### Positive

- Reuses the current app stack.
- Keeps migration history explicit.
- Supports local SQLite and Docker Postgres paths.
- Avoids an early rewrite into a different storage system.

### Negative

- SQLite/Postgres compatibility requires discipline.
- Some migrations need Alembic batch mode.
- Large analytical workloads may eventually outgrow the app database.

## Alternatives Considered

### CSV-first storage

Rejected. It is simple but weak for snapshots, labels, audit history, and UI workflows.

### SQLite-only

Rejected. It is good for local use but a poor long-term default for concurrent background jobs and larger datasets.

### Separate warehouse from day one

Rejected for now. It adds operational complexity before the research workflow is proven.

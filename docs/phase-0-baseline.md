# Phase 0 Baseline

Date: 2026-05-10

Branch: `research-engine`

Base commit:

```text
848fabc feat: add thumbnail URL handling and metadata history tracking for videos
```

## Scope

This document records the baseline state before the research-engine feature work starts. Phase 0 is intentionally limited to setup, verification, and non-behavioral cleanup.

## Environment

Observed local environment:

```text
Python 3.14.4
pytest 9.0.2
```

The local virtualenv already existed at `.venv/`.

## Baseline Checks

### Black

Initial command:

```bash
.venv/bin/black --check .
```

Initial result:

```text
would reformat tests/test_crud.py
would reformat tests/test_youtube_api.py
2 files would be reformatted, 17 files would be left unchanged.
```

Action taken:

```bash
.venv/bin/black tests/test_crud.py tests/test_youtube_api.py
```

This was a formatting-only cleanup.

Final result:

```text
19 files would be left unchanged.
```

### Ruff

Initial command:

```bash
.venv/bin/ruff check .
```

Initial result:

```text
.venv/bin/ruff: No such file or directory
```

Action taken:

```bash
.venv/bin/python -m pip install ruff
```

Note: the full `pip install -r requirements.txt` command could not complete under Python 3.14 because `psycopg2-binary==2.9.9` attempted a source build and `pg_config` was unavailable. CI uses Python 3.11, where the pinned dependency is expected to resolve normally. This should be revisited in Phase 0/1 if Python 3.14 local development is required.

Final result:

```text
All checks passed.
```

### Bandit

Command:

```bash
.venv/bin/bandit -c bandit.yaml -r .
```

Result:

```text
No issues identified.
```

### Pytest

Command:

```bash
.venv/bin/pytest tests/ -v
```

Result:

```text
32 passed, 36 warnings
```

Warnings observed:

- Flask-Limiter warns about in-memory rate-limit storage in tests.
- SQLAlchemy warns about `datetime.utcnow()` defaults.
- SQLAlchemy warns about legacy `Query.get()` usage.

These warnings are not Phase 0 blockers, but they should be tracked as future cleanup candidates.

### Migration smoke test

Initial command:

```bash
rm -f /tmp/youtube_phase0_smoke.db
DATABASE_URL=sqlite:////tmp/youtube_phase0_smoke.db FLASK_APP=app.py .venv/bin/flask db upgrade
```

Initial result:

```text
sqlite3.OperationalError: near "ALTER": syntax error
ALTER TABLE channels ALTER COLUMN is_tracked DROP DEFAULT
```

Cause:

The `0d2f4f59d9ab_add_channel_is_tracked_flag.py` migration used direct `ALTER COLUMN` syntax that SQLite does not support.

Action taken:

- Updated the migration to use Alembic `batch_alter_table` for dropping the temporary default.
- Updated downgrade to use `batch_alter_table` for SQLite-safe column removal.

Final result:

```text
Running upgrade  -> a07144c0dbb0, Initial schema
Running upgrade a07144c0dbb0 -> 6ef545e0e95d, add video history table
Running upgrade 6ef545e0e95d -> 0d2f4f59d9ab, add channel is_tracked flag
```

### Docker Compose config

Command:

```bash
docker compose config --quiet
```

Result:

```text
passed
```

## Phase 0 Artifacts Added

- `.env.example` with safe placeholders and future research-engine flags.
- `docs/phase-0-baseline.md` to capture baseline evidence.
- SQLite-safe migration handling for `is_tracked`.
- CI migration smoke test for Alembic upgrades.

## Phase 0 Open Items

- Decide whether local development should officially support Python 3.14 or standardize on Python 3.11 to match CI.
- If Python 3.14 is supported, update the Postgres driver strategy so dependency installation does not require a local `pg_config`.
- Consider adding a dedicated `requirements-dev.txt` or `pyproject.toml` later so runtime and dev tooling are not mixed.

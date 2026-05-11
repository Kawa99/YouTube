# Phase 16: Testing Strategy

Phase 16 makes the research engine safer to use as a decision-support system by expanding tests around deterministic fixtures, migrations, and scale-sensitive routes.

## Test Layers

### Unit Tests

Covered areas:

- YouTube URL parsing
- YouTube duration parsing
- quota estimation
- API parser behavior
- derived metric classification
- label validation
- optional admin auth
- security/health route behavior

### Integration Tests

Covered workflows:

- collection run creation
- channel job persistence
- repeated video collection snapshots
- title/thumbnail metadata changes
- research exports
- manual labeling audit trail
- owned analytics and experiment checkpoints
- operations and dashboard pages

### Contract Tests

Saved YouTube API fixture payloads live in:

- `tests/fixtures/youtube/videos_list_response.json`
- `tests/fixtures/youtube/channels_list_response.json`

Contract tests assert parser behavior against these saved payloads and avoid live YouTube API calls in CI.

### Migration Tests

Migration tests now verify:

- empty database upgrade to head
- expected performance indexes exist
- the latest migration can downgrade one revision
- downgrade preserves previous-phase tables where expected

### UI Route Tests

Route tests cover:

- main task-oriented pages
- invalid input handling
- export endpoints
- labeling validation
- large paginated data fixture behavior

## CI Behavior

CI runs without a real YouTube API key. The workflow runs:

- Black
- Ruff
- Bandit
- Pytest
- Alembic upgrade smoke test

The workflow now targets `main`, `master`, and `research-engine`.

## Remaining Future Work

- Add more YouTube API fixture variants for missing statistics, disabled comments, private videos, and deleted videos.
- Add explicit query-count or timing budgets once production-like datasets exist.
- Add coverage reporting thresholds after the suite stabilizes.

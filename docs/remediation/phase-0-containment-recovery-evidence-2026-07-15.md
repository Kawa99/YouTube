# Phase 0 Containment and Recovery Evidence

- **Date:** 2026-07-15
- **Repository:** `/home/kawa/YouTube`
- **Branch:** `phase-0`
- **Base commit:** `2e02e209228a67e37c7254678e2a62fd1eb40dd2`
- **Authoritative ledger:** `docs/production-readiness-remediation-execution-checklist-2026-07-15.md`
- **Status:** Complete

This record contains no environment values, database row contents, Redis key
names or values, tokens, passwords, API keys, or private analytics. Local
operational backups remain under the ignored and access-restricted
`backups/phase-0-20260715/` directory and are not Git content.

## 1. Gate status

| Phase 0 prerequisite | Status | Evidence |
| --- | --- | --- |
| Restrict the web listener | PASS | Baseline was `0.0.0.0:5000` and `[::]:5000`; Compose now publishes only `127.0.0.1:5000`, verified with `docker compose ps -a` and `ss -lntp`. |
| Pause unsafe unattended collection | PASS | `youtube-scheduler` was running; it was stopped cleanly and the service now requires the explicit `scheduled-collection` profile. Default `docker compose config --services` excludes it. |
| Back up PostgreSQL, supported SQLite, configuration metadata, and required Redis state | PASS | Custom PostgreSQL archive, ten SQLite online backups, an RDB snapshot, configuration metadata, and `SHA256SUMS` exist under the ignored mode-`0700` backup directory; every backup file is mode `0600`. |
| Perform disposable restore tests | PASS | PostgreSQL restored to a disposable database with matching revision and all 35 table counts; all SQLite restores passed `quick_check` and content-hash comparison; isolated Redis restored all eight non-expired keys. |
| Clean Git baseline and dedicated branch | PASS | Initial `master` was clean and equal to `origin/master`; `phase-0` was created at `2e02e20`. |
| Record versions, migrations, dependencies, images, tests, and warnings | PASS | Runtime, dependency, migration, image, test, and warning baselines are recorded below, including known non-passing drift evidence. |
| Add canonical repository instructions | PASS | Root `AGENTS.md` defines setup, containment, scheduler authorization, test, migration, backup, security, and completion rules. |
| Confirm no production/customer traffic is modified | PASS | On 2026-07-15, the repository owner confirmed the project has only been used locally, has not been published, and serves no production or customer traffic. |
| Record authorization ownership | PASS | On 2026-07-15, the user confirmed they are the sole project owner and therefore the authorized approver for secret rotation, credential revocation, firewall changes, data repair, and deployments. |
| Phase 0 gate | PASS | All prerequisites are evidenced. The complete test, migration, backup-integrity, runtime, containment, secret-scan, and diff gates passed again after the owner confirmations. |

## 2. Containment evidence

### 2.1 Baseline

Commands:

```bash
docker compose ps -a
ss -lntp
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:5000/healthz
```

Observed before containment:

- `youtube-web` published `0.0.0.0:5000->5000/tcp` and
  `[::]:5000->5000/tcp`.
- `youtube-scheduler` was running.
- The worker was idle, the queue contained zero jobs, and PostgreSQL and Redis
  were reachable.

### 2.2 Change and verification

Actions:

```bash
docker compose stop scheduler web
docker compose up -d --no-deps --force-recreate web
```

Configuration changes:

- Web port mapping is `127.0.0.1:5000:5000`.
- Scheduler service profile is `scheduled-collection`.

Observed after containment:

- `youtube-web` publishes only `127.0.0.1:5000->5000/tcp`.
- `ss -lntp` shows the application only at `127.0.0.1:5000`; no application
  listener remains on IPv4 wildcard or IPv6 wildcard.
- `youtube-scheduler` exited cleanly with status `0` and remains stopped.
- Default services are `db`, `redis`, `web`, and `worker`.
- The opt-in profile adds `scheduler`.
- The localhost health response remains HTTP 200 with database, Redis, queue,
  and worker checks successful.

Rollback while Phase 0 containment is required is intentionally limited: revert
the branch change and recreate the web container only after an authenticated,
authorized ingress exists. The scheduler must not be restarted merely to
restore old behavior; starting it requires explicit risk acceptance.

## 3. Runtime and dependency baseline

### 3.1 Version and migration state

| Item | Observed value |
| --- | --- |
| Source commit | `2e02e209228a67e37c7254678e2a62fd1eb40dd2` |
| Supported container Python | `3.11.15` |
| Alembic code head | `4e5f60718293` |
| PostgreSQL applied revision | `4e5f60718293` |
| PostgreSQL public tables | 35 |
| PostgreSQL source size | 23,035,239 bytes |

Commands:

```bash
docker compose exec -T web python --version
docker compose exec -T web flask --app app db heads
docker compose exec -T web flask --app app db current
docker compose exec -T web flask --app app db check
```

`flask db check` fails on the already-audited `MIG-002` drift. It reports
unique-constraint/index representation differences for `assets.asset_id`,
`content_theses.thesis_id`, and `videos.youtube_video_id`, plus missing modeled
indexes for `channel_snapshots.channel_id` and `video_snapshots.video_id`. Phase
0 records this failure; it does not modify applied migrations or conceal the
Phase 1 task.

### 3.2 Container images

| Service/image | Image ID | Observed size |
| --- | --- | --- |
| `postgres:15-alpine` | `5fe8ca7fc662` | 109 MB |
| `redis:7-alpine` | `8b81dd37ff02` | 17.3 MB |
| `youtube-scheduler:latest` | `d01649068bc534e1e6def6fb86c43e3d93cfec62c14656706668248a9d7670b1` | 138,351,346 bytes |
| `youtube-web:latest` | `6ff2a1a337759703721e3a1461beebd908779626ce0c096c2a3969747e2b1ed5` | 138,351,340 bytes |
| `youtube-worker:latest` | `596d80c3c381f43484acd571799a75855c0d02ecc65c33b21abaf8cd095b0c0a` | 138,351,343 bytes |

Image tags remain mutable; immutable image pinning is owned by `SUP-002`, not
Phase 0.

### 3.3 Installed dependency inventory

Command:

```bash
docker compose exec -T web python -m pip freeze --all
```

Observed installed environment:

```text
alembic==1.18.5
annotated-types==0.7.0
bandit==1.9.4
bidict==0.23.1
black==26.5.1
blinker==1.9.0
certifi==2025.1.31
charset-normalizer==3.4.1
click==8.1.8
colorama==0.4.6
coverage==7.15.1
crontab==1.0.5
defusedxml==0.7.1
Deprecated==1.3.1
et_xmlfile==2.0.0
Flask==3.1.0
Flask-Limiter==3.12
Flask-Migrate==4.0.5
Flask-SocketIO==5.3.6
Flask-SQLAlchemy==3.1.1
freezegun==1.5.5
gevent==26.5.0
gevent-websocket==0.10.1
greenlet==3.5.3
gunicorn==26.0.0
h11==0.16.0
idna==3.10
iniconfig==2.3.0
isodate==0.7.2
itsdangerous==2.2.0
Jinja2==3.1.5
limits==5.8.0
Mako==1.3.12
markdown-it-py==4.2.0
MarkupSafe==3.0.2
mdurl==0.1.2
mypy_extensions==1.1.0
numpy==2.2.3
openpyxl==3.1.5
ordered-set==4.1.0
packaging==26.2
pandas==2.2.3
pathspec==1.1.1
pip==24.0
platformdirs==4.10.0
pluggy==1.6.0
psycopg2-binary==2.9.9
pydantic==2.12.5
pydantic_core==2.41.5
Pygments==2.20.0
pytest==9.0.2
pytest-cov==7.1.0
python-dateutil==2.9.0.post0
python-engineio==4.13.3
python-socketio==5.16.3
pytokens==0.4.1
pytz==2025.1
PyYAML==6.0.3
redis==5.2.1
requests==2.32.3
responses==0.26.2
rich==13.9.4
rq==1.16.2
rq-scheduler==0.13.1
ruff==0.15.21
sentry-sdk==1.39.1
setuptools==79.0.1
simple-websocket==1.1.0
six==1.17.0
SQLAlchemy==2.0.51
stevedore==5.9.0
typing-inspection==0.4.2
typing_extensions==4.16.0
tzdata==2025.1
urllib3==2.3.0
Werkzeug==3.1.3
wheel==0.46.3
wrapt==2.2.2
wsproto==1.3.2
youtube-transcript-api==1.2.4
zope.event==6.2
zope.interface==8.5
```

The direct dependency manifest hash at baseline was
`b85bb1cc90061093334348ee093945ffc9cf4c183a0122526e54e90cc0b4ce19`.
Locking, advisory remediation, and reproducible builds remain owned by
`SUP-001`.

## 4. Backup inventory and checksums

Backup directory:

```text
backups/phase-0-20260715/
```

- Directory and subdirectories: mode `0700`.
- Backup files and manifests: mode `0600`.
- Git status: ignored through the repository `backups/` rule.
- Secret values: deliberately excluded from configuration metadata.
- Integrity command: `sha256sum -c backups/phase-0-20260715/SHA256SUMS`.
- Integrity result: every listed file `OK`.

| Artifact | SHA-256 |
| --- | --- |
| PostgreSQL custom archive | `c22d1c0a8ecd5c22c96257e82369e70b7ec945fe0186011b00169c46eab7ac92` |
| Redis RDB | `d9801761103e0ea44843d961a13d4c2f45929838b0ab5743bbb7503bd97924be` |
| Configuration metadata | `101d3851dd7b3c792e59eb320ab856fdac8abb2a8dc052a2ab67471e551d9285` |

The per-file SQLite SHA-256 values are retained in the ignored `SHA256SUMS`
manifest. Content-equivalence SHA-3 values are shown in the restore evidence.

## 5. PostgreSQL backup and disposable restore

Backup command:

```bash
docker compose exec -T db pg_dump -U baroo -d baroo_db \
  --format=custom --no-owner --no-privileges \
  --file=/tmp/phase0-postgresql.dump
```

- Backup tool wall time: approximately 4.3 seconds.
- Archive size: 1,678,307 bytes.
- `pg_restore --list` successfully read 313 TOC entries.
- Dump and restore tool versions: PostgreSQL 15.16.

The archive was restored with `--exit-on-error` into the disposable database
`baroo_phase0_restore_20260715`. Restore tool wall time was approximately 4.4
seconds. The restored database was 21,241,191 bytes and reported Alembic
revision `4e5f60718293`.

Exact source and restored row counts matched:

| Table | Rows | Table | Rows |
| --- | ---: | --- | ---: |
| `affiliate_product_evidence` | 0 | `alembic_version` | 1 |
| `api_raw_payloads` | 42 | `assets` | 0 |
| `channel_derived_summaries` | 38 | `channel_history` | 0 |
| `channel_labels` | 0 | `channel_snapshots` | 1,685 |
| `channel_videos` | 1,775 | `channels` | 110 |
| `collection_runs` | 42 | `content_theses` | 0 |
| `experiment_checkpoints` | 0 | `experiments` | 0 |
| `owned_analytics_credentials` | 0 | `owned_video_analytics` | 0 |
| `packaging_experiments` | 0 | `red_team_reviews` | 0 |
| `retention_diagnostics` | 0 | `sponsor_evidence` | 0 |
| `thesis_evidence` | 0 | `thesis_monetization_maps` | 0 |
| `thesis_scores` | 0 | `thesis_topics` | 0 |
| `video_assets` | 0 | `video_derived_metrics` | 1,587 |
| `video_disclosures` | 0 | `video_history` | 1,688 |
| `video_label_audits` | 1,784 | `video_labels` | 1,684 |
| `video_metadata_changes` | 0 | `video_metadata_history` | 0 |
| `video_rights_checklists` | 0 | `video_snapshots` | 1,688 |
| `videos` | 1,775 |  |  |

The disposable PostgreSQL database was dropped only after the comparison
passed. The source database was never modified by the restore rehearsal.

Recovery procedure:

1. Stop writers and identify an authorized empty recovery target.
2. Verify `SHA256SUMS` and `pg_restore --list`.
3. Create the empty target database.
4. Restore with `--no-owner --no-privileges --exit-on-error`.
5. Compare the Alembic revision and exact per-table counts.
6. Point a controlled application instance at the restored target and run smoke
   checks before any cutover.

## 6. SQLite backup and disposable restore

Ten SQLite databases were backed up using SQLite's online `.backup` command.
Every source and backup passed `PRAGMA quick_check`. Each backup was restored
into `/tmp/youtube-phase0-sqlite-restore-20260715/`; every restored database
again passed `quick_check` and produced the same schema-and-content SHA-3 hash
as its source.

- Ten-file online backup elapsed time: approximately 0.55 seconds.
- Ten-file disposable restore and verification elapsed time: approximately
  5.92 seconds.

| Source | User tables | Source and restored SHA-3 |
| --- | ---: | --- |
| `videos.db` | 4 | `32dd8fa8a34484bedb27849db6175c15fa4bbd063837a3e9b7bb2958` |
| `instance/videos.db` | 4 | `84ee5f2326bb2103760cdd93ad230420059e01115d2ee4dc0051d43f` |
| `data/videos.db` | 5 | `0acec3a4f17b03605d1c50bf0dd1179122739debbd5fdbf712aef019` |
| `data/browser-tryout.db` | 30 | `6d18d2313aa10817e0a97370acdfebac2d55b55c0c4a9a56d630ec17` |
| `data/local-webapp.db` | 35 | `476d768a084b6f5aa530efabc2eecdded30a47138af04374cb48a689` |
| `data/loneliness-pilot-2026-05-17.db` | 35 | `717d82326b7932b6fbe9e37c5723a837fc16037de4354b12f2cd7323` |
| `data/loneliness-refined-2026-05-18.db` | 35 | `831f4c5dc6fefe449758fd5f6bf3c81fea05fdc238e7536b9ca9621a` |
| `data/loneliness-broader-2026-05-22.db` | 34 | `8d6d40b41983b24a9c3003de97fc2d75e9b26422aa93e2c314e3a4a2` |
| `data/reddit-stories-2026-06-11.db` | 4 | `0f567c986d85cb30e2643c90d4246dc2bc098f230ffebd77037907dc` |
| `data/tiny-tale99-2026-06-12.db` | 4 | `b9302df9aa396a2ef2184e559278ee3f964f2c905a4d91157c7d1cc6` |

Recovery procedure:

1. Stop the writer for the selected SQLite database.
2. Verify the backup checksum and `PRAGMA quick_check`.
3. Restore into a new path, never over the only known-good file.
4. Re-run `quick_check` and compare the schema-and-content hash.
5. Confirm the application is configured for that exact path before a
   controlled restart.

## 7. Redis backup and isolated restore

The scheduler was stopped and the worker queue was idle before snapshotting.
`redis-cli SAVE` completed successfully. One TTL key expired between the first
inventory count and the completed snapshot, so the source and restore
comparison correctly used the post-snapshot count of eight non-expired keys.

- RDB size: 1,438 bytes.
- `redis-check-rdb`: checksum OK, eight keys read, one key with expiry, zero
  already expired.
- Disposable restore container: no published ports and no connection to the
  application Compose project.
- Restore result: `PING` returned `PONG`, `DBSIZE` returned `8`, loading was
  complete, and `rdb_last_load_keys_loaded` was `8`.
- The disposable container was stopped and auto-removed after verification.

Recovery procedure:

1. Confirm Redis state is required; do not restore stale jobs reflexively.
2. Verify the SHA-256 and `redis-check-rdb` result.
3. Restore into an isolated, portless instance using the same supported major
   Redis version.
4. Compare key counts and persistence load status without listing key names or
   values.
5. Review queued/scheduled job safety and TTLs before any controlled cutover.

## 8. Known baseline warnings and deferred findings

These are pre-existing and must not be mistaken for Phase 0 regressions:

- Flask-Limiter uses in-memory storage in the inspected configuration.
- RQ emits a deprecation warning for `worker.state`.
- SQLAlchemy emits legacy `Query.get()` warnings.
- Alembic model/migration drift is present as detailed above.
- Compose currently contains weak/default secret and database credential
  patterns owned by Phase 1 security tasks.
- Existing local `.env`, SQLite files, and the tracked root `dump.rdb` were mode
  `0644` at baseline. Durable local-file lifecycle remediation is owned by
  `SEC-015`; Phase 0 backup artifacts themselves are restricted.
- Mutable image tags and unlocked tooling are owned by `SUP-001`/`SUP-002`.

## 9. Final regression evidence

### 9.1 Clean build and application smoke

Command:

```bash
docker compose up -d --build
docker compose --profile scheduled-collection build scheduler
```

Results:

- Web and worker images built successfully from the Phase 0 branch.
- The scheduler image built successfully but was not started.
- The Docker build context obeyed `.dockerignore`; `backups/`, `data/`, `.env`,
  database files, Redis snapshots, and logs are excluded.
- Web, worker, PostgreSQL, and Redis are running.
- Scheduler remains stopped with its prior clean exit status `0`.
- Resolved default Compose configuration contains no scheduler service and
  publishes web only to host IP `127.0.0.1`.
- `/`, `/dashboard`, `/data`, `/operations`, and `/healthz` each returned HTTP
  200 from `127.0.0.1:5000`.
- `ss -lntp` reconfirmed no application listener on IPv4 or IPv6 wildcard.

### 9.2 Complete repository gate

Command:

```bash
./test_local.sh
```

Results:

- Black: PASS; 49 files unchanged.
- Ruff: PASS; no lint findings.
- Bandit: PASS; 8,398 lines scanned and zero Low, Medium, or High findings.
- Pytest: PASS; 63 of 63 tests passed in 24.86 seconds.
- Final repeated run warnings: 47 occurrences in the same three pre-existing audited classes:
  Flask-Limiter in-memory storage, deprecated RQ `worker.state`, and legacy
  SQLAlchemy `Query.get()`. No new warning category was introduced. Warning
  elimination remains owned by `CI-010` and the relevant security/reliability
  tasks.

### 9.3 Migration verification

Fresh disposable SQLite command:

```bash
docker compose run --rm \
  -e DATABASE_URL=sqlite:////tmp/youtube_phase0_final_migration.db \
  web flask --app app db upgrade
```

Result: PASS. A new database upgraded through all 12 revisions from the initial
schema to `4e5f60718293`.

Persistent PostgreSQL results:

- `flask db current`: PASS, `4e5f60718293 (head)`.
- `flask db upgrade`: PASS and no-op at current head.
- `flask db check`: expected baseline failure; the operation list is the same
  audited `MIG-002` set recorded in section 3.1 and contains no Phase 0 schema
  change.

### 9.4 Backup and configuration re-verification

- `sha256sum -c backups/phase-0-20260715/SHA256SUMS`: PASS for every artifact.
- `docker compose config --quiet`: PASS.
- Default `docker compose config --services`: `db`, `redis`, `web`, `worker`.
- Profile-enabled service list additionally contains `scheduler`.

### 9.5 Final source review

The final source review was repeated after the owner confirmations and before
commit. Results:

- No application Python, model, migration, route, template, or test behavior
  was changed.
- Runtime behavior changed only to reduce exposure and stop unattended work.
- Documentation and `AGENTS.md` describe the same contained operating state.
- Operational backup files remain ignored and outside the Docker build context.
- No secret value appears in the tracked diff or evidence document.
- `git diff --check` passed.
- The targeted private-key/token pattern scan returned no matches.
- The final repeated application gate passed all 63 tests with the original 47
  documented warnings and no new warning class.

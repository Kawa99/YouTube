# Comprehensive Engineering, Product, Security, Data, Networking, and Debugging Audit

**System:** YouTube Research Engine  
**Repository:** /home/kawa/YouTube  
**Audit date:** 2026-07-14  
**Audit type:** Multidisciplinary static review plus read-only runtime, database, migration, dependency, and test verification  
**Overall decision:** **Not production-ready for an internet-exposed, multi-user, or business-critical deployment**

## 1. Executive assessment

The application is a useful and unusually broad research prototype. It has a real domain model, Alembic migrations, a background job path, typed YouTube client errors, manual-label audit concepts, public/private data separation, export contracts, and a meaningful test suite. Those are good foundations.

It does not yet meet the public production-engineering bar normally associated with mature teams at Google, Amazon, Meta, or similarly regulated/high-scale organizations. This statement is not a claim about any company's confidential internal checklist. It means the implementation falls materially short of current public standards and practices such as OWASP ASVS 5.0, NIST SSDF, WCAG 2.2 AA, least-privilege deployment, reproducible supply chains, reliable distributed-job semantics, explicit service-level indicators, and statistically defensible analytics.

The most urgent facts are:

1. **The inspected live application has authentication disabled.** Its web service listens on all host interfaces, and the application contains private analytics, credentials metadata, exports, settings, job operations, and state-changing endpoints.
2. **The inspected session secret is only four characters.** The source also includes known development fallbacks. A weak Flask signing secret makes session integrity untrustworthy if authentication is later enabled.
3. **There is no CSRF defense.** Twenty-nine POST forms have no tokens, and one expensive job-starting mutation is exposed as GET.
4. **A confirmed integer-overflow path can silently lose an entire pending batch while reporting earlier rolled-back records as saved.** PostgreSQL logs contain real integer-overflow failures for channel counts above 2,147,483,647.
5. **YouTube API failures are converted into empty data and can be recorded as successful zero-result collections.** This corrupts operational truth and research completeness.
6. **The default local SQLite database cannot be upgraded by the documented migration command.** Key pages return HTTP 500 with the repository's normal local configuration.
7. **Redis is unauthenticated, has protected mode disabled, listens on all container interfaces, and transports RQ pickle jobs on a flat network.** A container-network foothold could become destructive queue access or code execution.
8. **The production Socket.IO topology is unsupported.** Gunicorn is configured with three workers even though Flask-SocketIO documents that Gunicorn cannot provide the sticky sessions required for that multi-worker topology.
9. **The dependency audit found 30 known advisories across 15 installed packages in the local environment, including multiple directly pinned runtime packages.** There is no lockfile, hash verification, SBOM, container scan, or automated dependency gate.
10. **The UI has keyboard, labeling, live-region, auto-refresh, information architecture, and responsive-navigation defects.** WCAG 2.2 AA conformance cannot be claimed.

If this service is reachable beyond a trusted single-user workstation, the immediate recommendation is to remove public reachability until the Critical security and data-integrity findings are remediated and independently retested.

## 2. Scope and evidence

### 2.1 What was reviewed

The review covered all first-party tracked source and operational material:

- Flask application factory, security hook, routes, CRUD, schemas, metrics, exports, background tasks, worker, scheduler, operations, rights, thesis, packaging, owned analytics, and YouTube client/service modules.
- Every Jinja template and first-party JavaScript/CSS asset.
- SQLAlchemy models and every Alembic migration.
- Dockerfile, production and development Compose files, requirements, Bandit configuration, CI workflow, test launcher, and environment contract.
- All automated tests and YouTube fixtures.
- Product requirements, phase documents, ADRs, workflow guides, data dictionary, export/import contract, schema map, operations guide, and previous diagnostic material.
- Tracked artifacts and ignored runtime-data categories.

The tracked first-party corpus is approximately 21,459 lines across source, templates, tests, migrations, and documentation. Runtime data files were inspected through metadata, schema, aggregate, integrity, and permissions checks; secret values and private row contents are intentionally not reproduced in this report.

### 2.2 Dynamic checks performed

- Read-only inspection of the running Flask/Gunicorn, worker, scheduler, PostgreSQL, and Redis containers.
- Internal HTTP checks of representative routes, response headers, redirect behavior, response sizes, and timings.
- PostgreSQL aggregate, schema, migration-head, duplicate, range, foreign-key-index, and recent-log checks.
- SQLite schema/integrity/foreign-key checks for local databases and a copy-based migration rehearsal.
- Redis bind, protected-mode, authentication, TLS, persistence, memory, and queue checks.
- Docker process user, bind address, health configuration, dependency order, and live container configuration checks.
- Fresh SQLite migration plus Alembic model-drift checks against both SQLite and live PostgreSQL.
- Unit/integration tests, coverage, Ruff, Black, Bandit, pip check, Compose validation, and dependency-vulnerability audit.

### 2.3 Checks deliberately not performed

No destructive exploit, credential use, external penetration test, production load test, browser-matrix test, assistive-technology session, third-party secret-backend access, or data mutation was performed. Network perimeter/firewall configuration outside this repository was not available. Therefore, "listens on all interfaces" is confirmed; "reachable from the public internet" is not.

### 2.4 Quality-gate results

| Check | Result | Interpretation |
|---|---:|---|
| Pytest | 63 passed, 44 warnings | Existing tested paths pass; warnings expose maintenance debt |
| Coverage | 78% overall, 56 warnings | No enforced threshold; critical integration paths remain weak |
| youtube_api.py coverage | 37% | Failure, quota, pagination, and retry behavior is under-tested |
| tasks.py coverage | 51% | Transaction, retry, interruption, and accounting paths are under-tested |
| operations.py coverage | 66% | Health and failure reporting are incomplete |
| scheduler.py / worker.py | Not imported by coverage run | Startup, reconnect, and shutdown behavior is untested |
| Ruff | Passed | Style/static lint is healthy within configured rules |
| Black | All 49 first-party Python files unchanged | Python formatting is consistent |
| Bandit | 0 configured findings | Does not invalidate the architecture/control findings below |
| pip check | Passed | Installed package metadata is internally consistent |
| Dependency vulnerability audit | 30 advisories in 15 locally installed packages | Upgrade and image-level verification are required |
| Fresh SQLite migration | Passed | A blank database can reach Alembic head |
| Alembic model-drift check | Failed on fresh SQLite and live PostgreSQL | Models and migrations are not in sync |
| Legacy local database upgrade | Failed: channels already exists | Documented local upgrade path is broken |
| Docker Compose config | Passed | YAML resolves; production hardening remains inadequate |

The warnings included Flask-Limiter's in-memory backend warning, deprecated SQLAlchemy Query.get use, and unclosed SQLite connection ResourceWarnings. A green unit suite and green Bandit result must not be treated as production approval.

## 3. Architecture and trust boundaries

The current deployment has the following consequential flow:

    Browser
      |
      | HTTP + Socket.IO; no repository TLS proxy
      v
    Gunicorn / Flask web (3 sync workers, root)
      |            |                  |
      |            |                  +--> Third-party browser CDNs and YouTube embeds
      |            |
      |            +--> Redis / RQ (no ACL/password/TLS, flat network)
      |                         |
      |                         +--> Worker (root) --> YouTube API / transcript service
      |                         |
      |                         +--> Scheduler (root)
      |
      +--> PostgreSQL (shared owner credential)
                  |
                  +--> public research data
                  +--> private owned analytics
                  +--> credential references and rights records

The browser, web process, queue, workers, scheduler, database, external APIs, and browser-loaded third parties are distinct trust boundaries. The current configuration largely treats them as one trusted environment. That assumption is the root cause of several Critical and High findings.

## 4. Severity model

| Severity | Meaning used in this report |
|---|---|
| **Critical** | Likely unauthorized access, session compromise, remote code path, silent material data loss, or inability to trust core results; blocks production |
| **High** | Serious confidentiality, integrity, availability, accessibility, or operational risk under plausible conditions; fix before broad use |
| **Medium** | Material correctness, scale, usability, maintainability, or defense-in-depth gap; schedule and track |
| **Low** | Localized polish or engineering-hygiene issue with limited immediate impact |

Priority is based on impact and exploitability, not implementation effort.

## 5. Immediate release blockers

| ID | Severity | Release blocker |
|---|---|---|
| SEC-001 | Critical | Authentication is fail-open and disabled in the inspected runtime |
| SEC-002 | Critical | Four-character live session secret plus committed development fallbacks |
| SEC-003 | Critical | No CSRF protection; mutation via GET |
| DATA-001 | Critical | 32-bit count overflow plus batch rollback/accounting bug |
| REL-001 | Critical | API failures can be recorded as successful empty collections |
| MIG-001 | Critical | Default local database is operationally stale and cannot follow documented upgrade path |
| SEC-008 | Critical | Unauthenticated Redis plus RQ pickle trust on flat container network |
| REL-006 | High | Unsupported three-worker Gunicorn/Socket.IO deployment topology |
| SUP-001 | High | Known vulnerable dependencies and non-reproducible supply chain |
| UX-001 | High | Keyboard-inaccessible core tables and custom controls |

## 6. Detailed security, privacy, and abuse findings

### SEC-001 — Critical — Authentication fails open and is disabled in the inspected runtime

**Evidence:** security.py treats authentication as enabled only when ADMIN_PASSWORD or ADMIN_PASSWORD_HASH exists. The inspected runtime had neither, so auth_enabled was false. The web service binds to 0.0.0.0:5000 and IPv6 all interfaces. /login redirects to the dashboard because there is nothing to authenticate. The auth exemption list and routes expose private analytics, exports, settings, operational details, labels, rights records, theses, and mutations.

**Trigger / edge case:** A developer omits or misspells an auth environment variable, a secret injection fails, a new environment uses defaults, or the host port is reachable by another user/device.

**Actual behavior:** The application silently becomes fully open.

**Impact:** Unauthorized viewing and modification of collected data, private channel analytics, credential metadata, research decisions, rights records, jobs, and exports. The failure mode is least secure precisely when configuration is incomplete.

**Expected behavior:** Production startup must fail closed if identity configuration is missing or invalid. Each human must have an identity; authorization must be role- and resource-aware; service endpoints must use service identities.

**Required correction:**

1. Make APP_ENV=production require a valid identity provider configuration and a cryptographically strong secret; abort startup otherwise.
2. Use OIDC/OAuth with a mature provider, short-lived sessions, MFA policy, role mapping, and explicit authorization decorators.
3. Separate roles such as viewer, researcher, rights editor, analytics editor, operator, and administrator.
4. Enforce authorization independently for HTTP, Socket.IO, exports, queue status, and APIs.
5. Bind only to a private interface behind an authenticated TLS reverse proxy until controls are complete.

**Acceptance tests:** Production boots must fail with missing auth configuration. Anonymous requests to every non-public route must return 401/403. Cross-role tests must cover reads, writes, exports, job events, and object IDs. A deployment test must verify the public listener exists only at the intended proxy.

### SEC-002 — Critical — Session secrets and key lifecycle are below minimum standard

**Evidence:** app.py:47 falls back to default-dev-key. docker-compose.yml falls back to change-this-in-real-environments. The inspected environment's SECRET_KEY length was four characters. A prior repository diagnostic records that the YouTube API key had been exposed in conversation and should be rotated. Secret values are not reproduced here.

**Actual behavior:** Known/default/weak signing material can be accepted without warning. Secrets are broadly injected into web, worker, and scheduler containers.

**Impact:** Flask session forgery, authentication bypass after auth is enabled, longer exposure window for API credentials, accidental log/process-environment leakage, and excessive blast radius.

**Expected behavior:** At least 256 bits of random signing material from a secret manager, startup validation, environment-specific keys, scheduled/emergency rotation, minimal distribution, and documented revocation.

**Required correction:** Rotate the API key and Flask secret; invalidate existing sessions; reject known defaults and secrets below 32 random bytes; move secrets to a managed secret store or Docker secrets; inject each secret only into consumers that need it; record owner, purpose, creation, expiry, and last rotation without storing values.

**Acceptance tests:** Secret scanner passes git history and build context. Production startup rejects weak/default values. Rotation integration test proves old sessions fail and the app continues with the new key.

### SEC-003 — Critical — CSRF is absent and an expensive mutation uses GET

**Evidence:** No CSRF library, token generation, or validation exists. Twenty-nine POST forms have no CSRF field. /process_channel/{channel_id}/{max_videos} is a GET route that enqueues work. /api/channel/{id}/toggle-tracking is a tokenless POST.

**Trigger:** A logged-in user visits an attacker-controlled page; a browser extension, preview bot, link scanner, or prefetcher follows a job URL; a malicious page submits a hidden form.

**Actual behavior:** State changes and quota-consuming collection can occur without an unforgeable user-intent token. SameSite=Lax is not a general substitute and does not make a state-changing GET safe.

**Impact:** Unauthorized jobs, quota exhaustion, data changes, rights/analytics manipulation, logout, duplicate collections, and denial of service.

**Expected behavior:** GET/HEAD are safe and idempotent. Every browser-originating mutation requires a CSRF token and appropriate Origin/Referer validation. APIs use explicit authentication and anti-CSRF strategy.

**Required correction:** Convert process_channel to POST; add Flask-WTF or an equivalent centrally enforced CSRF layer; use per-session tokens; validate Origin for sensitive endpoints; set SameSite and Secure cookies; add explicit confirmation for expensive operations.

**Acceptance tests:** A cross-site form and missing/invalid token receive 403. Crawling all GET links changes no state and enqueues no work. Valid tokens survive normal multi-tab usage and fail after session rotation.

### SEC-004 — High — HTTP security baseline is absent

**Evidence:** Representative live responses included zero of seven checked protections: Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options, framing protection, Referrer-Policy, Permissions-Policy, and Cache-Control. SESSION_COOKIE_SECURE is not configured. There is no TLS proxy configuration in the repository. Flask's own security documentation recommends explicit CSRF, security headers, Secure/HttpOnly/SameSite cookies, and bounded resource use.

**Actual behavior:** Browsers receive no application-wide mitigation for content injection, clickjacking, MIME sniffing, downgrade, referrer leakage, or unnecessary browser capabilities. Sensitive responses can be cached according to intermediary defaults.

**Expected behavior:** TLS-only ingress; HSTS after validation; nonce- or hash-based CSP; frame-ancestors; nosniff; strict referrer and permission policies; secure session cookies; no-store on sensitive/private/export responses.

**Correction:** Add a centralized response policy, proxy-aware HTTPS configuration, and tests. Self-host scripts/styles before enforcing CSP; remove unsafe inline code or supply nonces. Do not enable HSTS until HTTPS is correctly deployed.

### SEC-005 — High — Health, settings, errors, and exports leak sensitive operational context

**Evidence:** operations.py returns REDIS_URL, queue/worker names, and exception strings. Settings exposes Redis configuration. Several route handlers flash raw exception strings. Export datasets include owned_analytics_credentials fields such as email, scopes, and token_secret_ref, alongside private analytics. In the inspected auth-disabled runtime these routes were not protected.

**Actual behavior:** A user can learn topology and secret-reference naming; failures disclose internal details; broad exports combine high-sensitivity domains.

**Impact:** Reconnaissance, privacy breach, phishing/context leakage, easier lateral movement, and accidental disclosure through exported ZIP/CSV files.

**Expected behavior:** A public liveness response contains only status and opaque version. Detailed diagnostics require operator authorization. Errors return stable codes and correlation IDs. Sensitive datasets require separate permission, explicit confirmation, logging, and minimization.

**Correction:** Redact URLs/usernames/secrets; split public and private export scopes; exclude credential references by default; apply no-store and audit logging; map internal exceptions to safe messages.

### SEC-006 — High — CSV and spreadsheet formula injection

**Evidence:** export.py:1678-1696 writes untrusted YouTube and manually entered strings to CSV/XLSX without neutralizing leading equals, plus, minus, at-sign, tab, or carriage-return formula triggers.

**Trigger:** A channel title, video title, thesis field, note, or imported value begins with a spreadsheet formula marker and a user opens the export in Excel, LibreOffice, or another spreadsheet.

**Actual behavior:** The spreadsheet may evaluate attacker-controlled content.

**Impact:** Local command attempts in vulnerable clients, data exfiltration through external formulas, misleading calculations, or credential prompts.

**Expected behavior:** Values are data, not formulas, unless a trusted export field explicitly requires a formula.

**Correction:** Apply a shared spreadsheet-cell sanitizer before every CSV/XLSX sink, document the escaping contract, and consider a safe JSON/Parquet alternative for machine consumers.

**Acceptance tests:** Parameterized tests cover =, +, -, @, leading whitespace, tab, CR/LF, apostrophes, UTF-8, and round trips in supported spreadsheet clients.

### SEC-007 — High — Browser supply chain, CSP incompatibility, and third-party privacy exposure

**Evidence:** templates/base.html loads the Tailwind runtime from cdn.tailwindcss.com, unversioned Toastify assets from jsDelivr, and Google Fonts. video_detail.html loads unversioned Chart.js. Only Socket.IO has a version. No third-party asset has Subresource Integrity. Numerous inline scripts and styles require unsafe CSP allowances.

**Actual behavior:** Rendering, security, performance, and availability depend on mutable third-party responses. Browsers contact Google, jsDelivr, Tailwind CDN, and YouTube, disclosing client metadata. Tailwind's browser runtime is a development convenience rather than a production asset pipeline.

**Expected behavior:** Build, purge, fingerprint, and self-host production CSS/JS; lock dependencies; verify integrity; serve under a restrictive CSP. Document unavoidable third-party requests and privacy behavior.

**Correction:** Introduce a frontend build, package lockfile, static asset hashes, long-lived immutable caching, CSP nonces/hashes, and dependency scanning. Use youtube-nocookie.com where appropriate and a click-to-load privacy mode.

### SEC-008 — Critical — Redis/RQ trust boundary permits a high-impact compromise

**Evidence:** Live Redis had requirepass empty, bind to all IPv4/IPv6 container interfaces, protected-mode no, TLS port zero, and the default unrestricted user. The Compose network is flat. RQ serializes Python jobs using pickle-compatible semantics. Redis is not published to the host, which reduces but does not remove risk.

**Trigger:** Any compromised container, server-side request path, future debug service, accidental port publish, or neighbor with access to the Compose network reaches Redis.

**Actual behavior:** The client can inspect/alter queues, flush data, manipulate job payloads, or use administrative Redis commands.

**Impact:** Queue corruption, job forgery, denial of service, information disclosure, and a plausible code-execution path in a worker that deserializes attacker-controlled jobs.

**Expected behavior:** Network isolation plus authenticated least-privilege ACL users, encryption where traffic crosses hosts, dangerous-command restrictions, separate queue/pub-sub/key namespaces, and no untrusted serialization.

**Correction:** Create distinct Redis ACL users for web, worker, Socket.IO, and scheduler; remove administrative/dangerous commands; use long generated credentials; bind only to the private service network; segment networks; enable TLS for multi-host deployments; consider a serializer that cannot execute code.

**Acceptance tests:** Anonymous connection fails. Each service identity can access only required commands/keys/channels. A compromised web identity cannot flush Redis, mutate scheduler keys, or inject an executable worker payload.

### SEC-009 — High — Containers run as root and lack workload confinement

**Evidence:** All inspected containers ran as UID 0. The Dockerfile defines no USER. Compose defines no read_only filesystem, cap_drop, security_opt no-new-privileges, tmpfs, init, resource limits, or seccomp/AppArmor profile.

**Actual behavior:** A process compromise receives the container's maximum default privileges and writable filesystem.

**Expected behavior:** Explicit non-root UID/GID, read-only root filesystem, minimal writable mounts, dropped capabilities, no-new-privileges, resource budgets, and a reviewed runtime profile.

**Correction:** Create an unprivileged application user in the image, fix volume ownership, add an init, drop all capabilities, and add back only proven requirements. Keep PostgreSQL/Redis on their images' intended unprivileged users and verify rather than assume.

### SEC-010 — High — Database privilege and secret distribution violate least privilege

**Evidence:** Web, worker, scheduler, and migration paths share the same PostgreSQL owner credential. The Compose fallback credential is hard-coded. Secrets irrelevant to some roles are injected into all application containers.

**Impact:** A web compromise can alter schema and all data; a scheduler compromise reaches private analytics; credential rotation is all-or-nothing.

**Expected behavior:** Separate migration owner, application read/write role, read-only/reporting role, and narrowly scoped service identities. Each workload receives only required secrets.

### SEC-011 — High — Stored unsafe URL schemes can execute when clicked

**Evidence:** Packaging experiment_log_url is accepted from form data without an allowlisted scheme and rendered as href in templates/packaging_lab.html:213. Jinja escaping protects HTML syntax but does not make javascript: or data: URLs safe.

**Actual behavior:** A crafted stored link can execute script in the page's origin when an authorized user clicks it.

**Expected behavior:** Canonicalize URLs and allow only https, with an optional explicit http development exception; reject credentials, control characters, and dangerous schemes.

**Acceptance tests:** javascript:, data:, vbscript:, mixed-case/whitespace/encoded schemes, protocol-relative URLs, userinfo, and valid HTTPS cases.

### SEC-012 — Medium — Open redirect normalization is incomplete

**Evidence:** security.py's _safe_next accepts a value beginning with one slash and rejects two leading slashes, but does not reject backslashes or normalize browser/proxy interpretations first.

**Risk:** A value such as a slash followed by backslash and a hostname may be interpreted differently by clients or intermediaries. This is a conditional finding and requires browser/proxy confirmation.

**Expected behavior:** Resolve against a fixed origin, require same-origin path-only output, reject backslashes/control characters, and use a framework-vetted helper.

### SEC-013 — High — Request/input resource limits are missing

**Evidence:** There is no MAX_CONTENT_LENGTH, route body limit, universal field length bound, or server-side pagination limit for many manual forms. Several text areas and URLs are stored without bounded validation.

**Impact:** Memory/DB/log amplification, oversized exports, slow validation, and unauthenticated storage denial of service in the inspected configuration.

**Expected behavior:** Enforce limits at proxy, WSGI, schema, database, and job layers; return 413/422 with usable messages.

### SEC-014 — Medium — Client-supplied fetched metadata is trusted

**Evidence:** The /save flow validates request.form and persists hidden fields populated by the browser rather than re-fetching or signing the server-originated result.

**Actual behavior:** A user can modify hidden fields and store arbitrary view counts, titles, IDs, or URLs within schema type limits.

**Expected behavior:** Treat the browser as untrusted. Persist a server-side result token/reference or refetch the canonical resource. Validate IDs, nonnegative ranges, URL schemes, lengths, and cross-field consistency.

### SEC-015 — Medium — Sensitive local files have broad owner-readable permissions and weak lifecycle controls

**Evidence:** Ignored .env, database, backup SQL, and log files are mode 0644 in the workspace. Runtime data is approximately 104 MB. A SQL backup and multiple databases are locally readable to other same-host users. No encryption, retention schedule, secure deletion policy, or restore-test evidence exists.

**Expected behavior:** 0600 files or a restricted service account, encrypted backup storage, access logging, retention/deletion rules, and regularly tested restoration.

### SEC-016 — Medium — Security telemetry may over-collect and under-identify releases

**Evidence:** app.py, worker, and scheduler configure Sentry traces_sample_rate=1.0. The SDK is substantially old. Environment, release, PII scrubbing, sampling policy, and data residency are not explicitly configured. Database errors have logged full failed statements containing collected descriptions and emails.

**Impact:** Excess cost, privacy leakage, noisy telemetry, and inability to correlate incidents with a release.

**Expected behavior:** Structured redacted logs, environment/release tags, explicit send_default_pii=false, targeted sampling, retention controls, and secret/content scrubbers.

## 7. Reliability, backend, networking, and debugging findings

### REL-001 — Critical — Upstream API failure is reported as a valid empty result

**Evidence:** youtube_api.py:116-121 catches YouTubeAPIError and returns an empty dictionary. tasks.py:451-472 treats zero discovered videos as completed and emits "No videos found for this channel."

**Trigger:** Invalid/revoked key, quota exhaustion, transient network failure, 403/429/5xx response, malformed response, or upstream outage during channel discovery.

**Actual behavior:** A typed failure is erased. The collection run becomes completed with zero items, indistinguishable from a legitimately empty channel.

**Impact:** Silent missing data, false research conclusions, broken retry/alert logic, misleading job success rates, and wasted debugging time.

**Expected behavior:** Preserve a result type with success/empty/not-found/retryable-failure/permanent-failure. Only a successful API response containing an empty collection may become completed-empty.

**Correction:** Stop returning {} on exceptions; propagate typed errors with endpoint/status/reason/retryability; mark run failed or retrying; retain an opaque error code; alert on auth/quota failures.

**Acceptance tests:** Fixtures for 400, 401, 403 key error, 403 quota, 404, 429, 500, timeout, DNS error, invalid JSON, and legitimate empty channel must yield distinct run states.

### REL-002 — High — Retries multiply across layers and quota accounting ignores attempts

**Evidence:** The requests session has urllib3 retries while YouTubeClient.request_json also loops retries. With a configured count of five, a logical call can cause roughly multiplicative transport attempts. QuotaTracker increments a logical endpoint call rather than actual retries.

**Actual behavior:** An outage can create a retry storm, longer-than-expected latency, more quota use, and synchronized load. Retry duration can exceed the web/worker timeout assumptions.

**Expected behavior:** One retry owner per call chain, bounded total deadline/attempt budget, exponential backoff with jitter, Retry-After support, and metrics for every physical attempt. Amazon's public reliability guidance explicitly warns that retries can magnify overload and recommends bounded backoff and jitter.

**Correction:** Disable one retry layer; use a monotonic deadline; classify idempotency and retryable statuses; cap attempts; add full jitter; track logical calls, physical attempts, sleep, and quota units.

### REL-003 — High — Quota budget is informational, process-local, and incorrect on fallback paths

**Evidence:** QuotaTracker holds estimated_used only in process memory, never resets by API quota day, is not shared across web/workers, and its would_exceed method is not used to block work. Fallback estimates do not consistently include search's 100-unit cost or multiple pages.

**Actual behavior:** Each process believes it owns the full daily budget; restarts reset use; expensive fallback resolution can consume much more than displayed.

**Expected behavior:** A durable, atomic, date-keyed quota ledger shared by all callers; reserved budget before work; actual cost reconciliation; separate projects/keys; warning and hard-stop policies.

**Acceptance tests:** Concurrent workers cannot reserve more than budget. Day rollover follows the provider's quota timezone. Retry/fallback/search pagination costs reconcile to call logs.

### REL-004 — High — Collection jobs are neither idempotent nor deduplicated

**Evidence:** Repeated requests enqueue jobs without an idempotency key or active-channel lock. Scheduler recreation and multiple schedulers can race. Concurrent saves rely on uniqueness errors and append snapshots.

**Actual behavior:** Double-clicks, retries, cron overlap, or multiple processes can collect the same channel simultaneously.

**Impact:** Duplicate snapshots, API quota waste, unique-constraint failures, misleading progress, and competing transactions.

**Expected behavior:** Idempotency key derived from channel, request parameters, and time window; one active collection per channel; explicit force/replay semantics; database advisory lock or atomic Redis lock with fencing.

### REL-005 — High — A single worker/queue creates head-of-line blocking and no cancellation

**Evidence:** Long channel/transcript/metrics jobs share the queue path. UI supports polling but no cancel, pause, priority, deadline, or retry control.

**Actual behavior:** One slow transcript/API call can delay unrelated work; users cannot stop mistaken jobs.

**Expected behavior:** Separate bounded queues by workload, multiple supervised workers, per-job deadlines, cancellation checkpoints, fair scheduling, dead-letter handling, and visible retry history.

### REL-006 — High — Gunicorn and Socket.IO topology is unsupported

**Evidence:** The live web process used three synchronous Gunicorn workers. Flask-SocketIO is in threading mode and uses Redis. Flask-SocketIO's deployment documentation states Gunicorn cannot use more than one worker for Socket.IO because its load balancer lacks sticky sessions; scaling requires multiple single-worker instances behind a sticky-session-capable load balancer.

**Actual behavior:** Polling/WebSocket requests from one browser can reach different workers. Room membership and transport upgrade can fail intermittently even though Redis message distribution exists.

**Expected behavior:** One supported async/threaded worker per instance behind sticky load balancing, or a server/topology explicitly supported for multi-process Socket.IO.

**Acceptance tests:** A load test must maintain thousands of connect/join/poll/upgrade/disconnect cycles with zero unknown-session errors across restarts and scale changes.

### REL-007 — High — Synchronous heavy work runs inside 30-second web workers

**Evidence:** Metrics recomputation deletes and rebuilds results in a request transaction. Exports materialize datasets and build ZIP/CSV files synchronously. Gunicorn uses its default-style 30-second timeout. Existing operations documentation records an /analysis/compute timeout.

**Actual behavior:** Large computations can kill a worker mid-request, leave the user with 5xx, repeat work on retry, and reduce web capacity.

**Expected behavior:** Enqueue durable jobs, return 202 plus status URL, stream safe exports where appropriate, set deadlines, checkpoint progress, and atomically publish completed results.

### REL-008 — High — Database, Redis, and transcript calls lack end-to-end deadlines

**Evidence:** No explicit database connect/statement timeout, Redis socket timeout, or transcript-library deadline is configured. get_video_data defaults include_transcript to true, overriding the broader transcripts-off posture for single-video collection.

**Impact:** Hung dependencies consume workers indefinitely, defeat health checks, and block queues. Transcript requests can be slow or IP-blocked.

**Expected behavior:** Connect/read/total deadlines at every network boundary, cancellation propagation, circuit breakers for repeated provider failures, and transcripts disabled unless explicitly requested.

### REL-009 — High — Health checking is not safe or correctly separated

**Evidence:** /healthz calls operations_summary, which executes unguarded CollectionRun queries before it can report dependency status. On the stale local schema it returns a generic HTML 500 because collection_runs does not exist. It also checks Redis and reveals details.

**Actual behavior:** A schema mismatch breaks the health route itself. Liveness is coupled to database/Redis readiness and can cause restart storms during dependency incidents.

**Expected behavior:** /livez only proves the process/event loop is alive. /readyz performs bounded dependency and schema-head checks and returns a minimal structured 503. Detailed diagnostics require operator auth.

### REL-010 — High — Service startup and reconnect behavior is fragile

**Evidence:** Compose depends_on does not wait for healthy dependencies; no service defines a healthcheck. Worker/scheduler logs show connection reset/refused failures and process exits/restarts. There is no top-level reconnect/supervision loop beyond container restart policy.

**Expected behavior:** Dependency health conditions, jittered reconnect loops, readiness gates, graceful signal handling, bounded shutdown, and alerts on crash loops.

### REL-011 — High — Scheduler updates are non-atomic and duplicate schedulers can race

**Evidence:** Schedule management cancels and recreates cron jobs. There is no singleton leader lease. Midnight is hard-coded in UTC rather than an explicit business timezone/configuration.

**Actual behavior:** A crash between cancel/create loses the schedule; two schedulers can create duplicate work; users can misunderstand execution time.

**Expected behavior:** Database-backed desired schedule, single elected scheduler, transactional/versioned updates, explicit IANA timezone, next-run preview, and reconciliation.

### REL-012 — Medium — Rate limiting is local to each worker and proxy identity is undefined

**Evidence:** Flask-Limiter reports the in-memory backend. With three workers, counters are independent and reset on restart. get_remote_address is used without a documented trusted-proxy chain.

**Actual behavior:** Effective limits multiply across workers. Behind a proxy, all clients may share one address or untrusted forwarded addresses may be misinterpreted.

**Expected behavior:** Shared Redis limiter namespace, endpoint-specific user/API-key keys, trusted-proxy configuration, and separate abuse controls for expensive jobs/login/export.

### REL-013 — Medium — Global extension state and import-time parsing reduce isolation

**Evidence:** The module-global SocketIO object is recreated by create_app. Environment integers/floats and clients are initialized at import. Worker and scheduler call the full web app factory even when they do not serve HTTP.

**Impact:** Test leakage, duplicated handlers, cryptic startup crashes on invalid environment values, and unnecessary initialization in non-web roles.

**Expected behavior:** Immutable validated Settings object, role-specific factories, extension init_app pattern, and startup error messages naming invalid configuration.

### REL-014 — Medium — No stable API error contract or correlation path

**Evidence:** There are no application-wide 404/405/413/422/500 JSON/HTML handlers. Routes frequently catch Exception, flash raw text, and redirect.

**Expected behavior:** Stable error code, user-safe message, correlation ID, retryability, field-level validation details, structured log, and trace linkage.

### REL-015 — Medium — Performance is acceptable only at current size and has no capacity evidence

**Evidence:** Internal single-request observations were approximately 12 ms for health, 115 ms dashboard, 28 ms /api/data, 77 ms analysis, 90 ms packaging, and 88 ms owned analytics. Representative response bodies reached approximately 163 KB for packaging, 74 KB owned analytics, and 73 KB analysis. These are warm, unloaded, local measurements, not a load test.

**Expected behavior:** Defined SLOs and capacity envelope, percentile latency/error/saturation metrics, representative load and soak tests, query budgets, response budgets, and regression gates. Google SRE's public guidance centers monitoring on latency, traffic, errors, and saturation rather than isolated averages.

### REL-016 — Medium — Network architecture has no explicit production perimeter

**Evidence:** Web publishes 5000 on every host interface. Redis/PostgreSQL share a default flat network with every application role. There is no ingress proxy, TLS, egress policy, DNS policy, network segmentation, WAF/rate gateway, or documented firewall contract.

**Expected behavior:** Private web bind, TLS ingress with trusted proxy headers, separate frontend/backend/data networks, default-deny service access, restricted egress to required APIs, and infrastructure-as-code tests.

## 8. Database, migration, and data-integrity findings

### DATA-001 — Critical — 32-bit overflow combines with transaction rollback to silently misreport saved data

**Evidence:** Models use SQLAlchemy Integer for YouTube views/subscribers/channel totals and snapshot counts. PostgreSQL integer is limited to 2,147,483,647. Live PostgreSQL logs contain integer out of range errors for real channel totals above three billion; the largest stored channel view count was already 1,949,372,644. In crud.py:327-334, save_video(commit=False) flushes and calls db.session.rollback on any exception. In tasks.py:497-506, the caller then passes earlier pending_saves to _commit_pending_video_saves and increments inserted/updated counts after committing the now-empty transaction.

**Trigger:** Any row in a commit interval contains a count above the 32-bit limit or another flush error after earlier rows have been flushed but not committed.

**Actual behavior:**

1. Rows A through N are flushed and listed as pending.
2. Row N+1 overflows.
3. save_video rolls back the entire SQLAlchemy transaction, including A through N.
4. The outer loop "commits" pending A through N after rollback.
5. The empty commit succeeds and their pre-rollback result objects are counted as saved.
6. Only N+1 is counted failed; A through N are missing despite a success summary.

**Impact:** Silent batch data loss, false operational metrics, incomplete snapshots, and research results that cannot be trusted.

**Expected behavior:** Provider count fields use BigInteger. A row failure cannot erase unrelated successful rows, and committed row counts are derived from commit results rather than pre-commit intent.

**Required correction:**

1. Migrate all external count fields to BIGINT using a safe online migration plan.
2. Remove rollback ownership from nested CRUD helpers; establish one transaction owner.
3. Use savepoints per record or validated chunks, then commit and count only durable rows.
4. Mark overflow/validation separately from transport failures.
5. Reconcile affected collection runs and recollect channels whose counts exceeded range.

**Acceptance tests:** A chunk containing counts 2,147,483,647, 2,147,483,648, values above three billion, a mid-chunk unique conflict, and a malformed row must preserve valid records and report exact committed/failed totals. After any simulated commit failure, database count must equal items_saved.

### MIG-001 — Critical — Default local database is stale and cannot be migrated as documented

**Evidence:** With DATABASE_URL unset, app.py uses data/videos.db. That database has five legacy tables, 160 videos, eight channels, and an empty Alembic version table. /dashboard fails because video_labels is absent and /healthz fails because collection_runs is absent. A copy followed by the documented flask db upgrade fails immediately because channels already exists. A fresh empty database upgrades successfully.

**Actual behavior:** The repository's normal local startup can render shell pages but core pages return 500. The documented upgrade path cannot adopt the legacy schema.

**Expected behavior:** Every supported previous schema has a tested, non-destructive upgrade path, or startup stops with a precise migration instruction and automated backup.

**Correction:** Write a legacy-baseline/adoption migration or dedicated one-time converter; detect schema fingerprint; back up; migrate on a copy; validate row counts, FKs, and samples; stamp only after equivalence is proven. Do not simply stamp the existing DB.

**Acceptance tests:** CI must include a sanitized legacy fixture and upgrade it to head while preserving expected counts and relationships. Startup against old schema must never serve partial functionality.

### MIG-002 — High — Models and migration head have drifted

**Evidence:** flask db check fails against both a freshly upgraded SQLite database and the live PostgreSQL database. Detected differences include uniqueness/index definitions for assets.asset_id, content_theses.thesis_id, videos.youtube_video_id, and snapshot indexes.

**Impact:** A developer's schema depends on database history rather than code truth; generated migrations may oscillate; tests pass on a shape different from production.

**Expected behavior:** Alembic check is clean on every supported database, and CI blocks model changes without a migration.

### DATA-002 — High — Channel snapshots are written once per video, not once per collection

**Evidence:** crud.py:316-325 adds ChannelSnapshot inside save_video. Live data had 1,685 channel snapshots and 1,688 video snapshots; a single channel/run had up to 50 channel snapshots at effectively the same sampling time.

**Actual behavior:** A 50-video collection records the same channel-level measurement approximately 50 times.

**Impact:** Bloated tables, distorted time-series counts/aggregation, misleading change frequency, and slower queries.

**Expected behavior:** Exactly one channel snapshot per channel and collection run/sampling timestamp, protected by a unique constraint.

### DATA-003 — High — Redundant canonical and history fields create drift risk

**Evidence:** All 1,775 live videos had description equal to description_full and transcript equal to transcript_text. VideoHistory and VideoSnapshot had nearly matching populations. VideoMetadataHistory overlaps VideoMetadataChange. Channel subscribers duplicates subscriber_count.

**Impact:** Storage amplification, ambiguous source of truth, twice the migration/validation burden, and eventual disagreement.

**Expected behavior:** One canonical field/table per semantic fact; compatibility views or explicit deprecation migrations where needed; derived/search excerpts computed or separately justified.

### DATA-004 — High — SQLite foreign keys are not enabled

**Evidence:** SQLite connections defaulted PRAGMA foreign_keys to off and the application installs no connection hook to enable it. Current quick_check and foreign_key_check found no existing corruption, but writes are not protected.

**Actual behavior:** Local/test databases can accept orphaned references that PostgreSQL rejects.

**Expected behavior:** PRAGMA foreign_keys=ON for every SQLite connection, verified at startup/tests, or PostgreSQL as the only supported execution database.

### DATA-005 — High — Foreign-key joins and deletes lack sufficient indexing

**Evidence:** A PostgreSQL catalog check found 27 foreign-key column references without a matching leading index. This is an approximation by referencing column and should be reviewed constraint-by-constraint.

**Impact:** Full scans on joins/deletes, long lock duration, and nonlinear degradation as tables grow.

**Expected behavior:** Index foreign keys used for joins, cascades, and filters; validate with EXPLAIN ANALYZE and production-like cardinality.

### DATA-006 — High — Domain constraints and idempotency constraints are incomplete

**Evidence:** Models lack database checks for nonnegative counts, percentages, confidence/rate ranges, duration, money, and status enums. Missing or unclear uniqueness includes video label per video, daily owned analytics per video/date, experiment checkpoint number, video/asset link, and current derived-metric identity.

**Actual behavior:** UI validation can be bypassed; concurrent requests can create duplicates; impossible states such as negative views or percentages above 100 can persist.

**Expected behavior:** Database CheckConstraint and UniqueConstraint rules encode invariants; the service maps violations to 409/422; jobs use upsert/idempotency semantics.

### DATA-007 — High — Floating-point types are used for money and exact business values

**Evidence:** Revenue/cost/value fields use Float.

**Impact:** Rounding artifacts, inconsistent aggregation, and unreliable equality/reconciliation.

**Expected behavior:** Numeric/Decimal with declared precision and scale plus currency/unit. PostgreSQL specifically recommends numeric for monetary amounts and exact quantities.

### DATA-008 — High — Time semantics are naive and inconsistent

**Evidence:** Most DateTime values are timezone-naive with UTC tzinfo stripped; legacy fields include textual timestamps. Scheduler behavior is UTC while the UI does not consistently state timezone.

**Impact:** DST/timezone ambiguity, incorrect daily grouping, unstable ordering, and hard-to-debug cross-system comparisons.

**Expected behavior:** timezone-aware timestamps in UTC, IANA timezone for scheduled/user display, explicit date semantics for provider quota day and analytics day.

### DATA-009 — Medium — No optimistic concurrency protection

**Evidence:** Editable labels, status, rights, analytics, and thesis records have no row version/ETag.

**Actual behavior:** Two tabs/users overwrite each other with last-write-wins and no warning.

**Expected behavior:** Version column or If-Match; return 409 with a merge/reload experience; audit before/after and actor.

### DATA-010 — Medium — SQLite journaling is unsuitable for concurrent web/worker use

**Evidence:** Local SQLite databases use delete journal mode. Web and worker can access the same file.

**Impact:** database is locked errors, serialized writers, and fragile crash behavior.

**Expected behavior:** PostgreSQL for concurrent execution. If SQLite remains a supported single-user mode, enable WAL/busy timeout, one-writer assumptions, foreign keys, and explicit limitations.

### DATA-011 — Medium — Primary and provider identifier strategy is not scale-ready

**Evidence:** Many primary keys and counters are 32-bit Integer. Provider IDs are strings with inconsistent index/uniqueness state due migration drift.

**Expected behavior:** BIGINT generated internal IDs where table growth can be high; immutable, unique, indexed provider IDs; UUID/ULID only where distributed creation is needed.

### DATA-012 — High — Raw-source reproducibility is promised but not implemented

**Evidence:** ApiRawPayload exists in the model/ADR, but collection tasks store only selected parsed fields/sampling metadata. RAW_PAYLOAD_STORAGE_ENABLED is a placeholder without a complete persistence lifecycle.

**Impact:** Parser changes, upstream anomalies, disputes, and research recalculation cannot be reproduced from the original response.

**Expected behavior:** Privacy-reviewed raw response archive or immutable normalized event with checksum, request metadata, parser version, retention, compression, and replay tooling.

### DATA-013 — High — Rights readiness can become stale without invalidation

**Evidence:** Rights checklists are append-only point-in-time records. Later asset/link/license/disclosure changes do not invalidate or recompute a previous ready result. attribution_required does not enforce nonempty attribution text.

**Actual behavior:** A video can remain represented as ready after a linked asset's license or attribution changes.

**Expected behavior:** Readiness is a derived state from versioned current inputs, or a signed snapshot tied to exact asset/link versions. Any dependency change invalidates/requires review.

### DATA-014 — Medium — OAuth "revoke" changes metadata but does not revoke the credential

**Evidence:** The revoke route updates local credential status; no call revokes the external token or deletes/disables its secret-backend value. The UI language presents revocation as complete.

**Impact:** Users believe access has ended while the token may remain usable.

**Expected behavior:** External provider revocation, secret deletion/disable, local state update, result verification, and audit event. If only local disable is possible, label it accurately.

### DATA-015 — High — Owned analytics lacks ownership, range, uniqueness, and provenance enforcement

**Evidence:** Analytics can be attached to any video record without a verified ownership relationship. Duplicate date/checkpoint rows are possible. Inputs permit negative/impossible values and potentially NaN/Infinity through float parsing. Currency/units and source provenance are incomplete.

**Expected behavior:** Verified channel ownership, unique natural keys, finite numeric validation, domain ranges, unit/currency columns, import batch lineage, and correction history.

### DATA-016 — Medium — Current database integrity is clean but operational status semantics are inconsistent

**Evidence:** Live PostgreSQL was at Alembic head 4e5f60718293 with approximately 110 channels, 1,775 videos, 1,684 labels, and 42 collection runs. Aggregate checks found no duplicate labels/dates/checkpoints, negative current counts, or FK violations. However, at least one run recorded four failed items while its status was completed; all 42 statuses were completed.

**Interpretation:** Current rows are not broadly corrupt, but historical/status logic cannot be treated as a reliable success ledger. Repair must include data reconciliation, not only code changes.

## 9. Analytics and data-science findings

### DS-001 — High — Relative performance compares videos at incomparable ages

**Evidence:** Performance metrics compare lifetime views among recent videos without age-matched exposure windows. views_per_day divides lifetime views by age and clips sub-day age to one day.

**Actual behavior:** A one-hour-old video is penalized by a one-day denominator; old and new videos are ranked using unequal opportunity to accumulate views.

**Expected behavior:** Compare fixed post-publication windows such as 24h/7d/28d, age-matched survival/growth curves, or model expected views conditional on age, channel, and season.

### DS-002 — High — Missing data is frequently coerced to zero

**Evidence:** Safe integer helpers and metric logic commonly default unavailable/hidden likes, comments, subscribers, or views to zero.

**Impact:** "Unknown" becomes "observed none," biasing engagement rates, channel comparisons, and candidate selection.

**Expected behavior:** Preserve null plus missingness reason; define metric-specific eligibility; report coverage and confidence.

### DS-003 — High — Small samples produce confident-looking outputs

**Evidence:** A one-video channel can compare the video to itself and yield relative performance 1.0. There is no minimum cohort, shrinkage, confidence interval, or stability indicator.

**Expected behavior:** Return insufficient_data below a documented sample threshold, use robust/shrunk estimates, and expose sample size and uncertainty.

### DS-004 — High — "Under-served" and opportunity labels overstate what is measured

**Evidence:** Candidate theses aggregate manually labeled outliers and relative performance. They do not estimate audience demand, creator supply, addressable market, search intent, or causal opportunity.

**Actual behavior:** A descriptive internal score is presented with product language implying market under-supply.

**Expected behavior:** Rename to an honest descriptive construct or add validated demand/supply features, a preregistered formula, calibration, holdout evaluation, and uncertainty.

### DS-005 — High — No validation, backtesting, or decision-quality measurement

**Evidence:** No notebook/pipeline/test evaluates ranking stability, predictive power, false-positive cost, calibration, sensitivity, fairness, or business outcomes. Threshold changes rely on a mutable algorithm version string.

**Expected behavior:** Versioned training/evaluation dataset, temporal holdout, baselines, metric definitions, error analysis, drift checks, and a model/metric card even for heuristics.

### DS-006 — High — Algorithm versions can mix in product queries

**Evidence:** Recompute deletes only rows for the current algorithm_version, leaving older versions. Dashboard/analysis/packaging queries do not consistently filter a single current version, and no natural-key uniqueness prevents duplicates.

**Actual behavior:** A version change can make one video appear multiple times or combine incompatible calculations.

**Expected behavior:** Immutable metric run with code commit/config/input snapshot; one explicitly promoted active run; queries always bind to it; unique metric identity per run/video.

### DS-007 — Medium — Manual labeling quality is not quantified

**Evidence:** The product records audit events but has no blind double-label sample, inter-rater agreement, disagreement workflow, adjudication, label drift monitoring, or gold set.

**Expected behavior:** Label guide version, calibration set, periodic overlap sample, Cohen's kappa or appropriate agreement measure, adjudication, and reviewer-level quality feedback.

### DS-008 — Medium — Selection and survivorship bias are undocumented

**Evidence:** Channels/videos are manually selected and API availability filters the sample. Deleted/private/unavailable videos and transcript failures are not represented as analyzable missingness strata.

**Expected behavior:** Sampling frame, inclusion/exclusion reasons, collection coverage, failure rates, and explicit limits on generalization.

### DS-009 — Medium — Experiments lack statistical design

**Evidence:** Packaging experiments/checkpoints store observations but no preregistered hypothesis, primary metric, sample-size/power rationale, guardrail, stopping rule, comparison unit, or multiple-testing policy.

**Expected behavior:** Experiment protocol, immutable assignment, exposure log, primary/guardrail metrics, minimum duration, and analysis plan.

## 10. UI, UX, HCI, accessibility, and product findings

### UX-001 — High — Core table interactions are not keyboard accessible

**Evidence:** templates/data_viewer.html uses th.sortable click handlers without button semantics, tabindex, keyboard activation, aria-sort, or accessible instruction. Video/channel table rows navigate via onclick without focusability or a real link. channel_detail.html repeats clickable rows.

**Actual behavior:** Keyboard and assistive-technology users cannot reliably sort or open records.

**Expected behavior:** Real buttons inside scoped table headers with aria-sort; real links in the primary cell; visible focus; Enter/Space behavior supplied by native elements. WCAG 2.2 requires all functionality to be keyboard operable.

**Acceptance tests:** Complete collect-to-review-to-export workflows using keyboard only; automated axe checks; NVDA and VoiceOver spot checks; no pointer-only action.

### UX-002 — High — Custom tabs and menus lack accessible interaction models

**Evidence:** Tabs do not implement tablist/tab/tabpanel roles, selected state, roving tabindex, or arrow-key behavior. Theme and export menus lack menu roles, focus placement, Escape behavior, arrow navigation, and reliable focus return.

**Expected behavior:** Prefer disclosure/button patterns where simpler; otherwise implement WAI-ARIA Authoring Practices completely, including focus and state.

### UX-003 — High — Many form controls lack persistent labels and usable errors

**Evidence:** Export filters and numerous owned-analytics, rights, and thesis fields rely on placeholders or adjacent visual text that is not programmatically associated. Server errors are flashes after redirect; fields are not marked aria-invalid and entered data is often lost.

**Actual behavior:** Screen-reader users may hear ambiguous "edit text"; everyone must remember placeholder instructions; validation requires re-entry.

**Expected behavior:** Visible label for every control, description via aria-describedby, required/optional indication, inline error, error summary linked to fields, retained input, and server/client validation parity.

### UX-004 — High — Auto-updating content lacks safe user control

**Evidence:** Data viewer can poll every five seconds. It does not persist user preference, pause when hidden, back off on errors, or consistently expose updates to assistive technology. Overlapping requests are not aborted or sequenced.

**Actual behavior:** Older responses can overwrite newer state; hidden tabs consume network/DB resources; updates may distract or silently change context.

**Expected behavior:** Off by default or explicit user control; pause/stop/frequency control; Page Visibility pause; AbortController and monotonic request ID; backoff; non-disruptive aria-live summary. WCAG 2.2 requires a pause/stop/hide or frequency mechanism for auto-updating information.

### UX-005 — High — Navigation does not scale across viewport or task complexity

**Evidence:** Desktop navigation exposes roughly a dozen peer links at the medium breakpoint. Mobile uses a horizontally scrolling link strip rather than a discoverable menu. Active state is primarily color and lacks aria-current. Footer repeats much of the same list.

**Actual behavior:** Tablet widths can overflow; users must scan a flat list of internal phase names; mobile destinations are hidden off-screen.

**Expected behavior:** Task-based information architecture with a small number of top-level groups, responsive menu, current-page semantics, search/command palette where justified, and usability-tested labels.

### UX-006 — Medium — No skip link, heading/landmark hygiene, or complete table semantics

**Evidence:** Base has no skip-to-content link. theses.html nests a main element inside the base main. Many th elements omit scope; large tables lack captions or equivalent descriptions.

**Expected behavior:** One main landmark, skip link, logical heading hierarchy, scoped headers/captions, and landmark names where multiple regions exist.

### UX-007 — Medium — Motion and loading states ignore user preferences

**Evidence:** Pulse/spinner/transition animations are common and no prefers-reduced-motion CSS exists. Toasts auto-dismiss after about 4.2 seconds.

**Expected behavior:** Respect reduced motion, avoid nonessential indefinite animation, keep actionable errors until dismissed, and provide persistent in-page status.

### UX-008 — Medium — Responsive data tables remain cognitively difficult

**Evidence:** Large tables use horizontal scrolling, dense columns, and a sticky top-0 header underneath a sticky global navigation context. No column chooser, condensed mobile representation, or table-level summary exists.

**Expected behavior:** Prioritized columns, responsive cards or details, configurable columns, preserved first-column context, captions, and tested sticky offsets.

### UX-009 — Medium — Images and embeds miss performance/accessibility/privacy attributes

**Evidence:** YouTube iframe and thumbnails are inconsistent on title, meaningful alt text, loading=lazy, explicit dimensions/aspect ratio, referrer policy, sandbox/allow list, and privacy-enhanced embed host.

**Impact:** Layout shift, unnecessary network/privacy cost, ambiguous screen-reader content, and broad iframe capabilities.

### UX-010 — Medium — No proven color/zoom/reflow accessibility

**Evidence:** No automated contrast/reflow test, high-contrast mode support, 200%/400% zoom evidence, or focus-obscured test exists. Tailwind color combinations and dark mode are extensive.

**Expected behavior:** WCAG 2.2 AA audit at all responsive variants, including contrast, focus appearance/not obscured, reflow, target size, text spacing, and forced-colors.

### PROD-001 — High — Product identity and navigation expose duplicate collection concepts

**Evidence:** /collect, /, and /channel overlap collection workflows; the single-video save path returns users to a legacy-style page. Product documentation describes phases more clearly than the UI explains a coherent end-to-end journey.

**Actual behavior:** A user must learn implementation history rather than one mental model.

**Expected behavior:** One Collect workspace with channel/video modes, consistent job history, next step, and canonical routes with redirects from legacy paths.

### PROD-002 — High — Long-running actions lack job-grade feedback and recovery

**Evidence:** Recompute/export are synchronous; collection has polling but no cancel/retry/replay, estimated completion, per-item error download, or recovery action.

**Expected behavior:** Durable job center with queued/running/retrying/partial/failed/cancelled states, timestamps, progress denominator, remaining estimate, failure categories, retry/cancel, and link to output.

### PROD-003 — High — Older records are inaccessible from normal selectors

**Evidence:** Rights and owned-analytics forms use latest-100 video selectors. Channel detail and thesis views have the opposite issue and can load unbounded collections.

**Actual behavior:** Older videos cannot be selected for key workflows, while other pages degrade as data grows.

**Expected behavior:** Server-side search/autocomplete with stable pagination, filters, recent context, and direct deep-link selection.

### PROD-004 — Medium — Forms are monolithic and provide weak recovery

**Evidence:** Theses and owned analytics contain very large multi-section forms. Errors redirect and commonly lose user input. There are no drafts, autosave, section validation, or clear completion model.

**Expected behavior:** Progressive sections/steps, save draft, explicit review, retained values, field-level error recovery, and unsaved-change warning.

### PROD-005 — Medium — Most records cannot be corrected safely

**Evidence:** Many domain entities are append-only with no correction, supersede, archive, or delete workflow.

**Actual behavior:** Operators must tolerate bad records or edit the database; dashboards can keep using stale entries.

**Expected behavior:** Controlled correction/supersession with reason, actor, timestamp, preserved history, and downstream recomputation.

### PROD-006 — High — Thesis governance is too permissive for decision support

**Evidence:** Status can be changed broadly; launch guarding primarily checks for monetization mapping rather than evidence threshold, red-team review, rights readiness, owner approval, or score validity.

**Expected behavior:** Explicit state machine with permitted transitions, required artifacts/approvals, role checks, audit event, and rollback.

### PROD-007 — Medium — Credential and ownership UI overstates implemented capability

**Evidence:** OAuth configuration is represented, but the integration is largely metadata/secret-reference based. "Revoke" does not revoke externally. Owned analytics can be attached without a verified ownership relationship.

**Expected behavior:** Accurate capability labels, setup verification, connection test, last sync, scope summary, external revoke status, and ownership badge.

### PROD-008 — Medium — No onboarding, global findability, or contextual guidance

**Evidence:** There is no first-run checklist, sample workspace, empty-state walkthrough, global entity search, recent activity, or contextual explanation of derived metrics and data freshness.

**Expected behavior:** Guided first successful collection, visible API/database/worker readiness, searchable entities, freshness/provenance, and links to definitions at decision points.

### PROD-009 — Medium — No localization or explicit locale/timezone contract

**Evidence:** User-facing strings are hard-coded English; date/number rendering is inconsistent and timezone-naive.

**Expected behavior:** At minimum, documented English/UTC policy with localized number/date formatting and explicit display timezone; introduce i18n if the intended audience requires Arabic or other locales.

### PROD-010 — Medium — Product quality is not measured

**Evidence:** No privacy-conscious product analytics, funnel metrics, task completion measurements, usability studies, support categorization, or accessibility feedback channel exists.

**Expected behavior:** Define success/error/abandonment for core workflows and conduct moderated usability tests. For a private single-user tool, lightweight event logs and interviews are sufficient; invasive tracking is not required.

## 11. Export, scalability, and performance findings

### PERF-001 — High — ZIP export amplifies memory and disk use

**Evidence:** Export code materializes query results with list operations, builds complete CSV strings, then writes a temporary ZIP synchronously in a web request. Cleanup is not guaranteed across every exception boundary.

**Actual behavior:** Large exports can hold rows plus serialized copies in memory and disk simultaneously, time out, and leave orphan files.

**Expected behavior:** Background export job, server-side cursor/chunking, incremental CSV/ZIP writes, size estimate/limit, guaranteed finally cleanup, encrypted object storage, expiring signed download, and audit event.

### PERF-002 — Medium — "All tables CSV" is not a valid single rectangular CSV

**Evidence:** The combined export concatenates heterogeneous table sections and marker lines.

**Impact:** Standard parsers treat it as malformed or misaligned data.

**Expected behavior:** One CSV per table in a ZIP, or a documented JSON/Parquet/SQLite package. Keep a manifest containing schema/version/checksums.

### PERF-003 — High — Data viewer does excess work every five seconds

**Evidence:** /api/data counts and fetches videos, channels, and history on every request even when one tab is visible; the same page/sort parameters are shared. The frontend polls by default without request cancellation.

**Expected behavior:** Separate endpoints or a resource parameter; query only visible data; conditional requests/ETag; cached counts; cursor pagination; user-controlled refresh; database query budget.

### PERF-004 — High — Metric computation has N+1 and repeated-query patterns

**Evidence:** Per-video computation queries recent peers/snapshots; channel calculations repeat snapshot access; packaging change display can issue roughly two queries per change.

**Expected behavior:** Set-based SQL/window functions, preloaded aggregates, batch queries, current-run materialized results, and EXPLAIN-tested indexes.

### PERF-005 — Medium — Unbounded detail/dashboard queries will degrade

**Evidence:** Channel detail loads all videos; thesis dashboard loads all theses/evidence structures; multiple selectors build large lists.

**Expected behavior:** Stable cursor pagination, explicit sort, page bounds, batched relationship loading, and query-count tests.

### PERF-006 — Medium — Static delivery has no production asset strategy

**Evidence:** No compression configuration, local asset fingerprinting, cache policy, minified bundle, image optimization pipeline, or response budget exists.

**Expected behavior:** Brotli/gzip at ingress, hashed local assets, immutable cache headers, optimized responsive images, and monitored page-weight budgets.

## 12. CI/CD, supply chain, testing, and maintainability findings

### SUP-001 — High — Dependencies contain known advisories and builds are not reproducible

**Evidence:** The local ignored environment audit found 30 advisories across 15 packages. Directly pinned packages implicated included Flask 3.1.0, Click 8.1.8, idna 3.10, Jinja2 3.1.5, requests 2.32.3, sentry-sdk 1.39.1, urllib3 2.3.0, and Werkzeug 3.1.3; transitive/dev packages were also present. requirements.txt mixes runtime and dev dependencies, leaves several tools unpinned, and has no hashes/lock. Docker separately installs unpinned Gunicorn.

**Important qualification:** This was a local-environment audit, not a digest-level scan of a freshly rebuilt production image. It is sufficient to show the dependency process is not safe, but the exact production count must be re-established after a clean build.

**Expected behavior:** Separate input constraints from compiled hash-locked runtime/dev files; one source of dependency truth; automated upgrade PRs; pip-audit/OSV and image scan gates; SBOM and provenance; scheduled rebuilds.

**Correction:** Upgrade in compatibility-tested batches rather than blindly jumping major versions. Current major-version drift is significant for Redis client, RQ, Sentry, Flask-Limiter, and pandas.

### SUP-002 — High — Base images and GitHub Actions use mutable references

**Evidence:** Docker uses python:3.11-slim, redis:7-alpine, and postgres:15-alpine without digests. GitHub Actions uses actions/checkout@v4 and setup-python@v5 rather than immutable commit SHAs.

**Expected behavior:** Pin production images and actions to verified digests/full SHAs, then use automated reviewed updates. Docker and GitHub both document immutable pinning as the supply-chain-safe option.

### CI-001 — High — CI does not test the deployed architecture

**Evidence:** CI tests only Python 3.11 with fresh SQLite. It does not launch PostgreSQL, Redis, RQ, scheduler, Gunicorn, or Socket.IO; does not test browser behavior; and does not upgrade a legacy database.

**Expected behavior:** Fast unit lane plus PostgreSQL/Redis integration lane, migration-from-supported-versions lane, Socket.IO/job end-to-end lane, and browser smoke/accessibility lane.

### CI-002 — High — Coverage is reported but not enforced

**Evidence:** CI runs pytest without coverage flags or minimum. The local coverage run reached 78%, with core modules at 37-66% and scheduler/worker unimported.

**Expected behavior:** Enforce a reasonable overall floor plus changed-code and critical-module floors. Branch coverage should target failure/rollback/retry/auth behavior, not merely line count.

### CI-003 — High — Schema drift is not a gate

**Evidence:** CI runs flask db upgrade but not flask db check. Current check fails.

**Expected behavior:** Upgrade and check on PostgreSQL, downgrade policy or forward-only verification, legacy fixture upgrade, and data migration assertions.

### CI-004 — High — Security and supply-chain gates are incomplete

**Evidence:** Bandit excludes tests and skips B101; there is no secret-history scan, dependency audit, container/OS scan, CodeQL/SAST, DAST, SBOM, license policy, IaC scan, or artifact attestation.

**Expected behavior:** Risk-based layered scans with suppressions carrying owner/reason/expiry. NIST SSDF calls for security practices integrated throughout the SDLC.

### CI-005 — Medium — Workflow permissions and execution controls are implicit

**Evidence:** CI sets no top-level permissions, timeout-minutes, concurrency cancellation, environment restrictions, or CODEOWNERS for workflows.

**Expected behavior:** permissions: contents: read, explicit timeouts, cancel superseded branch/PR runs, protected branch rules, reviewed workflow ownership, and immutable actions.

### CI-006 — Medium — Python/environment contract is inconsistent

**Evidence:** Container/CI target Python 3.11, while the local ignored venv runs Python 3.14.6. psycopg2-binary 2.9.9 could not resolve cleanly for that local interpreter without build prerequisites. README local setup does not strongly enforce 3.11.

**Expected behavior:** .python-version/tool manager or dev container, supported-version matrix, preflight check, and compatible lock per Python version.

### CI-007 — Medium — Local environment instructions do not actually load .env

**Evidence:** README instructs users to copy .env and run local commands, but python-dotenv is not a dependency and the app does not call load_dotenv. Flask emitted a dotenv installation tip. Shell-exported values or Compose work; plain python app.py does not honor the file.

**Expected behavior:** Either explicitly load validated dotenv in development only or document shell/Compose usage accurately. Never silently use insecure defaults.

### CI-008 — Medium — Test launcher and docs disagree on Compose command

**Evidence:** test_local.sh uses legacy docker-compose while README uses docker compose.

**Expected behavior:** One supported Compose v2 command, preflight detection, and the same entrypoint in CI and docs.

### CI-009 — Medium — Frontend correctness has no automated gate

**Evidence:** No JS lint/type checking, template validation, Playwright/Cypress, axe, visual regression, responsive browser matrix, or performance budget exists.

**Expected behavior:** At least ESLint, template smoke, Playwright critical journeys, axe-core, and a small cross-browser/viewport matrix.

### CI-010 — Medium — Warnings and resource leaks are accepted

**Evidence:** Tests emitted 44-56 warnings depending on coverage instrumentation, including unclosed SQLite connections and deprecated SQLAlchemy access.

**Expected behavior:** Warning budget trends to zero; ResourceWarning fails targeted tests; dependencies/APIs are upgraded before removal deadlines.

### MAINT-001 — Medium — Large modules and mixed responsibilities obstruct safe change

**Evidence:** export.py is about 1,914 lines, test_routes.py about 1,772, routes.py about 1,028, and models.py about 894. Route registration, validation, business logic, persistence, formatting, and UI contracts are interwoven.

**Impact:** High review load, merge conflicts, broad test setup, and difficult ownership.

**Expected behavior:** Domain packages with application services, repositories/query modules, route schemas, export writers, and focused tests. Decompose by behavior, not arbitrary line count.

### MAINT-002 — Medium — Documentation describes intended controls that code does not enforce

**Evidence:** Phase/ADR documents describe security, raw payloads, scale, and repeatable metrics more strongly than the executable controls. Examples include raw payload storage, security posture, and background computation.

**Expected behavior:** Mark documents proposed/implemented/verified; link every requirement to code/test/metric; prevent aspirational docs from being read as current guarantees.

### MAINT-003 — Low — Tracked runtime artifacts should be removed from version control

**Evidence:** dump.rdb and __pycache__/database.cpython-311.pyc are tracked. The Redis dump contained only expired/ephemeral keys at inspection time.

**Impact:** Repository noise, accidental data leakage, non-reproducible diffs, and confusing runtime state.

**Expected behavior:** Remove from tracking, ignore all runtime snapshots/bytecode, scan history, and keep sanitized fixtures under explicit test paths.

## 13. Consolidated debugger's edge-case register

This register turns high-risk observations into concrete behaviors a debugger or QA engineer should reproduce.

| Case | Trigger | Current/likely behavior | Required behavior |
|---|---|---|---|
| Count boundary | Channel views = 2,147,483,648 | PostgreSQL integer overflow | Persist in BIGINT with no special case |
| Mid-batch overflow | Valid rows followed by overflow | Whole transaction rolls back; earlier rows may still be counted saved | Savepoint/chunk preserves valid rows; exact durable accounting |
| Empty channel | Valid successful API response with zero uploads | Completed-empty | Keep completed-empty with provider response evidence |
| API outage | Timeout/403/429 returns empty dictionary | Completed-empty can be recorded | Failed/retrying with typed cause |
| Invalid API key | Provider rejects credentials | May look like no data | Fail fast, disable jobs, operator alert |
| Nested retry | 500 across session and client retry layers | Attempt amplification and long delay | One bounded retry owner with jitter/deadline |
| Two job clicks | Same channel submitted twice | Duplicate active jobs and snapshots | One active job; second returns existing status |
| Two schedulers | Both reconcile at midnight | Duplicate/cancelled jobs possible | Leader lease plus idempotency |
| Redis restart | Queue resets while worker blocks | Process can exit/crash-loop | Reconnect with jitter; readiness false; no job loss |
| PostgreSQL restart | Web health request during restart | Health may hang/fail generically | Bounded ready=503; live=200 |
| Stale schema | Default videos.db | Core pages and health return 500 | Startup blocks with migration workflow |
| Legacy upgrade | flask db upgrade on unversioned schema | Table-already-exists failure | Tested adoption/conversion |
| Concurrent label save | Two reviewers/tabs edit same video | Last writer wins/duplicate possible | Version conflict or adjudication |
| Duplicate analytics day | Same video/date submitted twice | Duplicate rows possible | Unique constraint plus update/correction flow |
| NaN input | Numeric form receives nan or inf | Float parser may persist non-finite value or fail late | 422 finite-number validation |
| Negative analytics | Negative views/revenue/CTR | May persist without DB check | 422 plus DB constraint |
| Unsafe URL | experiment URL is javascript: payload | Executes on click | Reject at input and safe render |
| Formula title | Video title begins with =WEBSERVICE(...) | Spreadsheet evaluates it | Export neutralizes as text |
| Oversized note | Multi-megabyte form value | Memory/DB/log amplification | 413/422 before business logic |
| Hidden-field tamper | Client edits fetched metadata | Arbitrary canonical data saved | Server-side result/refetch |
| CSRF collection | Third-party page causes job submission | Job/data/quota mutation | 403 without valid token/origin |
| GET prefetch | Bot follows process_channel link | Job starts | GET is side-effect free |
| WebSocket cross-user | User joins guessed job ID | Job events disclosed | Object-level authorization |
| WebSocket multi-worker | Poll/upgrade hits different worker | Intermittent session/room failure | Supported sticky topology |
| Slow transcript | Library never returns promptly | Worker stalls queue | Deadline/cancel/circuit breaker |
| Older video | Video outside latest 100 | Cannot select in rights/analytics UI | Searchable server-side selector |
| Large channel | Thousands of videos on detail page | Large query/DOM/latency | Pagination/virtualization |
| Overlapping poll | Slow response exceeds 5-second interval | Stale response overwrites fresh one | Abort/sequence requests |
| Background tab | Data page left hidden | Polls indefinitely | Visibility pause |
| Keyboard sort | Focus user tries table header | Header cannot be activated | Native sort button |
| Screen-reader toast | Error auto-dismisses | Error may be missed | Persistent error plus live announcement |
| 400% zoom | Dense navigation/table | Reflow/overlap risk | No two-dimensional page scroll for core flow |
| Rights mutation | Asset license changes after ready check | Old ready result remains | Invalidate/recompute |
| Credential revoke | User clicks revoke | Only local metadata changes | External revoke verified |
| Algorithm upgrade | New version recomputed | Old/new rows can mix | Query one promoted immutable run |
| Single-video cohort | Only one comparator | Relative score appears meaningful at 1.0 | insufficient_data |
| Missing likes | Provider hides likes | Zero biases engagement | Null with missingness |
| Sub-day video | Age is two hours | Denominator clipped to one day | Fixed-window/age-aware metric |
| Export interruption | Worker killed while ZIP writing | Orphan temp file/failed request | Durable job and guaranteed cleanup |
| Secret omission | Production secret injection fails | App starts insecurely | Startup aborts |
| Proxy deployment | X-Forwarded-For not trusted correctly | Bad rate-limit identity/scheme | Explicit trusted proxy chain |
| Container compromise | Web reaches unrestricted Redis | Queue/data/admin access | ACL and segmented identity |

## 14. Observability and incident-readiness gaps

1. No documented SLOs, error budget, alert thresholds, or capacity envelope.
2. No Prometheus/OpenTelemetry metrics for request latency, queue wait/runtime, failure categories, API attempts/quota, DB pool, export size, scheduler lag, or collection completeness.
3. Logs are unstructured and may contain raw SQL/content; correlation across HTTP request, job ID, collection run, API request, and metric run is incomplete.
4. Health status is a UI summary rather than a monitored liveness/readiness contract.
5. No alert routing, escalation policy, runbook linkage, incident roles, or postmortem template is executable from the repository.
6. No recovery-point objective, recovery-time objective, restore drill, or point-in-time recovery proof.
7. Redis persistence is only RDB-style in the inspected configuration; no maxmemory policy was set, and the host warned vm.overcommit_memory was disabled.
8. No deployment marker, build SHA, migration head, config fingerprint, or algorithm version is consistently attached to telemetry.

Minimum production signals should include:

- **Traffic:** requests/jobs/API units by route/type and actor.
- **Errors:** status/retryability/cause, not only exception strings.
- **Latency:** p50/p95/p99 for web, queue wait, job runtime, DB, Redis, YouTube, transcript, and export.
- **Saturation:** Gunicorn busy workers, queue depth/oldest age, DB pool/locks, Redis memory, disk, CPU, and provider quota.
- **Data quality:** discovered versus fetched versus committed, missingness by field/reason, duplicate/conflict counts, schema/algorithm version, and freshness lag.

## 15. Recommended remediation plan

### Phase 0 — Immediately, before any broader network exposure

1. Restrict host/network access to a trusted local user or private VPN.
2. Rotate the exposed/suspect YouTube API key and the four-character Flask secret; invalidate sessions.
3. Make production startup fail closed without strong auth and secret configuration.
4. Disable or protect exports, settings, operations, owned analytics, Socket.IO rooms, and all mutations.
5. Add CSRF and convert process_channel to POST.
6. Change provider count columns to BIGINT and fix transaction ownership/accounting.
7. Stop converting YouTube failures to empty success; reconcile affected runs.
8. Back up the legacy SQLite database and do not run destructive/stamping migration shortcuts.
9. Authenticate/ACL Redis and isolate it from unneeded containers.
10. Upgrade directly vulnerable dependencies after a clean image audit.

**Exit criteria:** Anonymous access is denied; weak configuration cannot boot; overflow test is green; API failures cannot become completed; CSRF test is green; clean dependency/image report has no unaccepted Critical/High findings.

### Phase 1 — First one to two weeks

1. Implement OIDC identities, roles, per-object authorization, audit events, session policy, and login abuse controls.
2. Build and test legacy schema adoption; make Alembic check clean on PostgreSQL.
3. Create supported liveness/readiness endpoints and dependency timeouts.
4. Move metrics/exports to background jobs with idempotency, cancellation, and exact progress.
5. Replace the Gunicorn/Socket.IO topology with a documented supported topology.
6. Add DB constraints/indexes, one channel snapshot per run, timezone-aware timestamps, Decimal money, and safe URL/formula handling.
7. Self-host pinned frontend assets; introduce CSP/security headers and secure/no-store cookies/responses.
8. Add PostgreSQL/Redis/job integration tests and a legacy migration fixture to CI.

### Phase 2 — Thirty days

1. Decompose routes/export/models around domain services and transaction boundaries.
2. Introduce a quota ledger, single retry policy, deadlines, jitter, circuit breaking, and provider-failure dashboards.
3. Add network segmentation, non-root/read-only containers, least-privilege DB roles, healthchecks, and resource limits.
4. Add SBOM, immutable action/image pins, secret scan, SAST, dependency/container scans, and artifact provenance.
5. Repair core keyboard/form/tab/menu/navigation issues and establish automated WCAG checks.
6. Replace latest-100/unbounded selectors with server-side search and pagination.
7. Implement data lineage: raw/event archive, collection run, parser version, code SHA, algorithm run, and export manifest.

### Phase 3 — Sixty to ninety days

1. Establish SLOs, error budgets, alerts, on-call/runbooks, backup/restore drills, and capacity tests.
2. Redesign research metrics with fixed exposure windows, missingness, cohort eligibility, uncertainty, and backtesting.
3. Add label-quality calibration and experiment-design governance.
4. Validate product information architecture and workflows through moderated usability sessions.
5. Complete a manual WCAG 2.2 AA audit with keyboard, screen readers, zoom/reflow, contrast, and mobile browsers.
6. Commission an independent penetration test after the architecture is hardened.

## 16. Required production acceptance gates

The service should not be called production-ready until all of the following are objectively true:

### Security

- Production refuses to start without validated auth, authorization policy, and strong secret material.
- OWASP ASVS 5.0 Level 2 requirements are mapped to pass/fail evidence; exceptions have owner, compensating control, and expiry.
- All mutations have CSRF/API anti-forgery protection; all GET endpoints are safe.
- No anonymous access to private data, jobs, events, exports, settings, or diagnostics.
- Redis, database, container, proxy, and egress identities are least privilege.
- Clean secret, dependency, container, SAST, and DAST gates; SBOM/provenance published.

### Correctness and data

- BIGINT overflow and mid-batch rollback tests pass with exact committed counts.
- Legitimate empty, not found, auth failure, quota failure, retryable outage, and malformed response are distinguishable.
- Model/migration drift check is clean on PostgreSQL.
- Every supported historical database fixture upgrades with verified row/invariant preservation.
- Database constraints reject impossible values and duplicates.
- Metric run/version/input lineage is immutable and queries cannot mix versions.

### Reliability and operations

- Liveness/readiness, graceful start/stop, dependency restart, and crash-loop tests pass.
- Jobs are idempotent, cancellable, retry-bounded, deadline-aware, and dead-lettered.
- Socket.IO load/upgrade/reconnect tests pass on the exact deployed topology.
- Published SLOs have telemetry and alerts for latency, traffic, errors, saturation, queue age, and data completeness.
- Restore drill meets stated RPO/RTO.

### UI and product

- Critical user journeys pass keyboard-only and screen-reader tests.
- Automated axe checks have no serious/critical violations; manual WCAG 2.2 AA audit is complete.
- Forms have labels, retained values, inline errors, and error summaries.
- Responsive workflows pass at mobile, tablet, desktop, 200%, and 400% zoom.
- Long jobs expose durable status, retry/cancel, partial failures, and outputs.

### Engineering system

- Coverage thresholds protect critical branches; all warnings are triaged.
- CI tests PostgreSQL, Redis/RQ, migration fixtures, Socket.IO, browser journeys, accessibility, and supply chain.
- Actions and production images are immutably pinned and automatically updated through review.
- Performance/capacity regression tests enforce query, latency, queue, memory, and response-size budgets.

## 17. Current strengths worth preserving

These do not cancel the findings, but remediation should build on them:

- SQLAlchemy parameterization and Jinja autoescaping reduce common injection classes.
- YouTube hostname allowlisting exists for main collection inputs.
- The lower-level YouTube client has typed error classes and explicit request timeouts.
- Alembic exists and a blank database reaches head.
- The live PostgreSQL dataset passed the performed FK/negative/duplicate aggregate checks.
- Manual label audit concepts and ADRs show awareness of research governance.
- Public market data and private owned analytics are conceptually separated.
- OAuth values are represented by secret references rather than raw tokens in primary rows.
- Redis and PostgreSQL are not directly published as host ports by Compose.
- Ruff, Black, the current unit suite, and basic Compose validation are green.
- Documentation is extensive and gives a strong starting point for executable requirements.

## 18. Standards and public production references

This audit used public standards rather than inaccessible company-internal rules:

- [OWASP Application Security Verification Standard 5.0](https://owasp.org/www-project-application-security-verification-standard/) — web application security control baseline.
- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final) — secure SDLC and software supply-chain practices.
- [Flask security considerations](https://flask.palletsprojects.com/en/stable/web-security/) — CSRF, headers, cookies, and resource limits.
- [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) — accessibility target, including keyboard access, labels, status messages, and auto-updating content.
- [Flask-SocketIO deployment guidance](https://flask-socketio.readthedocs.io/en/latest/deployment.html) — supported Gunicorn worker and sticky-session topology.
- [Redis security guidance](https://redis.io/docs/latest/operate/oss_and_stack/management/security/) and [Redis ACL documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/) — trusted-network, authentication, ACL, and TLS model.
- [Docker build best practices](https://docs.docker.com/build/building/best-practices/) — minimal trusted images, digest pinning, reproducible builds, and non-root USER.
- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use) — least-privilege tokens, secret handling, full-SHA action pinning, and supply-chain controls.
- [PostgreSQL numeric types](https://www.postgresql.org/docs/current/datatype-numeric.html) — INTEGER/BIGINT ranges and exact NUMERIC use for money.
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — latency, traffic, errors, saturation, and actionable monitoring.
- [Amazon Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — bounded retries, backoff, jitter, and failure amplification.
- [YouTube Data API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost) — endpoint-specific quota accounting.

## 19. Final verdict

This repository is best characterized as a **feature-rich single-user research prototype with a production-shaped architecture, not a production-grade service**.

The app can continue to be useful in a tightly restricted local environment, but the current running configuration must not be treated as secure simply because Redis/PostgreSQL are not host-published or because the tests pass. Authentication fail-open, weak signing material, absent CSRF, silent API-success conversion, confirmed integer overflow, transaction-accounting data loss, stale local migrations, and an unrestricted queue trust boundary are release blockers.

The first engineering milestone should be **trustworthy and safe collection**, not new features: fail-closed identity, correct transaction semantics, typed failure states, durable schema migration, least privilege, and exact data lineage. Once those are in place, accessibility, workflow cohesion, scalable querying, statistical validation, and operational maturity can be improved on a stable foundation.

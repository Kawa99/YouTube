# Production-Readiness Remediation Execution Checklist

- **System:** YouTube Research Engine
- **Repository:** /home/kawa/YouTube
- **Created:** 2026-07-15
- **Source audit:** [Comprehensive Engineering, Product, Security, Data, Networking, and Debugging Audit](comprehensive-engineering-product-security-audit-2026-07-14.md)
- **Purpose:** Execute every audit finding once, in dependency order, with objective proof before marking it complete.

## 1. How this document must be used

This is the authoritative remediation ledger. Work from top to bottom unless a task explicitly names a dependency that is already complete or an urgent containment action requires immediate attention.

Each audit finding appears exactly once as a numbered task. The only authoritative completion marker is the final **TASK COMPLETE** checkbox inside that task. Do not create a second completion checkbox in another document.

No AI system, test suite, or checklist can provide literal 100% certainty. This ledger is designed to reach a strict, evidence-based production standard and to prevent false completion. Security, accessibility, recovery, statistical validity, and customer readiness still require independent human or specialist verification where stated.

### 1.1 Non-negotiable execution rules

1. Work on one task at a time unless two tasks are explicitly declared safe to run in parallel in separate worktrees.
2. Before changing code, reproduce or prove the current failure and save the baseline evidence.
3. Do not mark a criterion complete because code was written. Mark it only after its stated behavior was tested.
4. Never weaken or delete a test merely to make a change pass. If a test is obsolete, document the changed requirement and replace it with equal or stronger coverage.
5. Never silently stamp a database, discard user data, rotate a real secret, revoke a real credential, change a production firewall, or publish a service without explicit user authorization.
6. Use a new migration for schema changes. Never edit a migration already applied to a persistent database.
7. Test migrations on a copy or disposable database before any real database. Preserve pre-migration backup and rollback/recovery instructions.
8. Keep public research data, private owned analytics, credential metadata, logs, and exports in their intended trust boundaries.
9. Do not expose secret values, tokens, private row contents, or personal data in prompts, logs, fixtures, screenshots, commits, or this tracker.
10. Treat warnings, skipped tests, flaky tests, partial migrations, unverified manual steps, and unavailable dependencies as incomplete work.
11. Preserve unrelated user changes and keep each change set narrowly scoped.
12. If acceptance criteria cannot be verified from the available environment, leave them unchecked and record the exact blocker.

### 1.2 Status vocabulary

- **Not started:** No implementation work has begun.
- **In progress:** Some criteria are complete, but **TASK COMPLETE** is unchecked.
- **Blocked:** A named dependency, authorization, environment, external system, or human verification is unavailable. Record it; do not check completion.
- **Complete:** Every task-specific criterion and the Global Definition of Done is checked, evidence is recorded, and no unresolved Critical/High regression remains.
- **Reopened:** A regression, new evidence, or invalid assumption has made a previously completed task unreliable. Uncheck **TASK COMPLETE** and document why.

### 1.3 Global Definition of Done — mandatory for every task

Before checking any **TASK COMPLETE** box, Codex must verify all applicable items below and record each as **PASS**, **BLOCKED**, or **N/A with reason** in that task's completion record. These are reference criteria, not shared status checkboxes; do not mark them once globally and assume they apply to later tasks.

- **G1 — Baseline:** The pre-change behavior was reproduced or established with a test, query, trace, screenshot, or documented inspection.
- **G2 — Scope:** The implementation addresses the root cause and does not include unrelated refactoring.
- **G3 — Positive path:** Automated tests prove the required successful behavior.
- **G4 — Negative and boundary paths:** Tests cover invalid, empty, maximum/minimum, failure, timeout, and authorization cases relevant to the task.
- **G5 — Concurrency/idempotency:** Race, retry, duplicate, interruption, and replay cases are tested when the task can run concurrently or mutate durable state.
- **G6 — Supported databases:** PostgreSQL is tested for all persistence behavior; SQLite is tested only where it remains an explicitly supported mode.
- **G7 — Migration safety:** Upgrade, data transformation, invariant validation, and recovery/rollback are tested when schema or stored data changes.
- **G8 — Security/privacy:** Authentication, authorization, CSRF, secret handling, logging, export, and privacy effects were reviewed where applicable.
- **G9 — Observability:** Failures produce safe structured evidence, stable error codes, and correlation identifiers without leaking sensitive values.
- **G10 — Compatibility:** Existing supported workflows, URLs/contracts, exports, and data remain compatible or have an explicit versioned migration/deprecation.
- **G11 — Full verification:** The relevant focused tests and the complete repository test/lint/format/security/migration suite pass with no new warnings.
- **G12 — Documentation:** Configuration, runbook, data dictionary, ADR, API/export contract, and user instructions are updated where behavior changed.
- **G13 — Review:** The final diff was reviewed for correctness, security, data loss, error handling, accessibility, and unintended changes.
- **G14 — Evidence:** Exact commands, results, test names, migration revision, commit/PR, manual checks, and residual risks are recorded.

If an item is genuinely not applicable, record **N/A** with one sentence explaining why. An unexplained N/A is a failed criterion.

### 1.4 Required completion record

Copy and fill this record beneath the task before checking **TASK COMPLETE**:

    Status:
    Started:
    Completed:
    Implemented by:
    Reviewed by:
    Commit or PR:
    Files changed:
    Migration revision:
    Baseline evidence:
    Focused verification commands and results:
    Full-suite commands and results:
    Manual or external verification:
    Security/privacy review:
    Rollback or recovery procedure:
    Residual risks or N/A explanations:
    Global DoD G1-G14 results:

### 1.5 Standard of comparison

Unless a task specifies something stricter, acceptance is measured against:

- [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/) Level 2 for the authenticated web application.
- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final) for the SDLC and supply chain.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) Level AA for every supported responsive UI state.
- PostgreSQL correctness and operational behavior as the production database.
- Least privilege and defense in depth for identities, containers, database, queue, network, and secrets.
- Bounded deadlines, retries with jitter, idempotency, health/readiness separation, and observable failure semantics for distributed operations.
- Reproducible builds, immutable dependencies, provenance, vulnerability gates, and recoverable deployments.
- Statistically honest labels, uncertainty, missingness, lineage, versioning, and validation for research metrics.

## 2. Phase 0 — Containment and safe working baseline

Complete this gate before normal remediation. These actions do not close audit findings by themselves.

- [x] Restrict the current web listener to the trusted local/private environment until Phase 1 and Phase 2 are complete.
- [x] Pause unattended/scheduled collection if it can trigger the confirmed overflow or false-success paths.
- [x] Create verified backups of PostgreSQL, supported SQLite data, configuration metadata, and required Redis state without copying secrets into the repository.
- [x] Perform a test restore to disposable storage and record row counts, schema version, checksums, duration, and result.
- [x] Capture clean git status and create a dedicated remediation branch or worktree.
- [x] Record the current application version/commit, Alembic head, dependency inventory, container image identifiers, test results, and known warnings.
- [x] Create or update repository-level AGENTS.md with canonical setup, test, migration, security, and completion commands.
- [x] Confirm production/customer traffic is not being modified during destructive or migration rehearsals. The sole owner confirmed on 2026-07-15 that the project is local-only, unpublished, and has no production/customer traffic.
- [x] Record who can authorize secret rotation, credential revocation, firewall changes, data repair, and production deployment. The sole project owner is the authorized approver for each action.
- [x] **PHASE 0 GATE COMPLETE** — all containment and recovery prerequisites above have evidence in `docs/remediation/phase-0-containment-recovery-evidence-2026-07-15.md`.

## 3. Phase 1 — Critical trust and data-integrity blockers

### 3.1 SEC-001 — Make authentication fail closed and enforce authorization

**Depends on:** Phase 0.

**Acceptance criteria**

- [ ] Production startup exits nonzero with a clear safe error when identity configuration is missing, malformed, uses a known default, or cannot initialize.
- [ ] Every route is classified as public, authenticated, or role-restricted; the default classification is deny, not allow.
- [ ] Anonymous HTTP requests to all non-public pages, APIs, exports, job endpoints, settings, and diagnostics return 401/403 without disclosing protected content.
- [ ] Socket.IO connect, room join, and event handlers authenticate the session and authorize access to the requested job/object.
- [ ] At least viewer, researcher/editor, rights/analytics editor, operator, and administrator capabilities are enforced server-side or a documented smaller role model proves equivalent least privilege.
- [ ] Direct-object-reference tests prove one identity cannot read or mutate another unauthorized resource or job.
- [ ] Session login, logout, expiry, rotation, replay, concurrent sessions, and revoked-user behavior are tested.
- [ ] Authentication failures and privileged actions create redacted audit events with actor, action, object, outcome, time, and correlation ID.
- [ ] **TASK COMPLETE — SEC-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.2 SEC-002 — Establish strong secret generation, validation, distribution, and rotation

**Depends on:** Phase 0; coordinate with SEC-001.

**Acceptance criteria**

- [ ] The exposed/suspect YouTube key and weak Flask signing secret are rotated through an authorized process; old values are revoked and not recorded in git or task evidence.
- [ ] Production accepts no built-in/default signing key and rejects secrets with less than 256 bits of cryptographically random entropy.
- [ ] Development defaults are explicitly non-production, cannot be selected by production configuration, and produce a visible warning.
- [ ] Secrets come from a managed secret mechanism or restricted secret files, not committed Compose defaults or broadly readable environment files.
- [ ] Each web, worker, scheduler, migration, and operational role receives only the secrets it requires.
- [ ] Rotation invalidates old sessions safely and supports overlap only where a documented key-ring transition is required.
- [ ] Automated secret scanning covers the working tree, git history, build context, CI logs, fixtures, and generated artifacts.
- [ ] A secret inventory records owner, purpose, consumers, creation, rotation due date, and revocation method without recording secret values.
- [ ] **TASK COMPLETE — SEC-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.3 SEC-003 — Enforce CSRF protection and safe HTTP method semantics

**Depends on:** SEC-001.

**Acceptance criteria**

- [ ] Every state-changing browser route uses POST, PUT, PATCH, or DELETE; crawling every GET/HEAD route changes no durable state and enqueues no work.
- [ ] The channel-processing GET route is removed or becomes a safe compatibility redirect to a confirmation page; job creation requires an authenticated POST.
- [ ] A centrally enforced anti-CSRF mechanism protects every cookie-authenticated mutation, including fetch/AJAX requests and logout.
- [ ] Tokens are bound to the intended session, generated with secure randomness, checked with constant-time framework behavior, and rotated according to session policy.
- [ ] Missing, invalid, expired, cross-session, and reused tokens behave according to the chosen framework policy and return a stable 403 response.
- [ ] Sensitive requests validate Origin and use an explicit same-origin policy as defense in depth.
- [ ] Automated cross-site form, image/link prefetch, multipart, JSON, and JavaScript request tests prove mutations cannot occur without valid user intent.
- [ ] Templates and JavaScript obtain/send tokens without placing them in URLs, logs, browser history, or analytics.
- [ ] **TASK COMPLETE — SEC-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.4 SEC-008 — Secure Redis, RQ serialization, and queue trust boundaries

**Depends on:** SEC-002; coordinate with SEC-009, SEC-010, and REL-016.

**Acceptance criteria**

- [ ] Anonymous Redis connections fail in every non-local-test environment; protected mode/bind/network rules do not expose Redis to untrusted networks.
- [ ] Distinct ACL identities exist for web, worker, scheduler, Socket.IO, and operations where their permissions differ.
- [ ] Each identity is limited to required commands, key prefixes, and Pub/Sub channels; administrative and dangerous commands are denied to application identities.
- [ ] Credentials are strong, rotated, redacted, and delivered through the approved secret mechanism.
- [ ] TLS is used whenever Redis traffic crosses a host or untrusted network boundary; the documented single-host exception is explicitly risk accepted.
- [ ] Queue payload serialization cannot execute attacker-controlled code, or a documented control proves only a narrowly authorized producer can write job payloads and workers reject unsigned/unexpected payloads.
- [ ] A compromised web credential cannot flush Redis, change configuration, read unrelated secrets, alter scheduler state, or enqueue arbitrary executable jobs.
- [ ] Redis restart, credential rotation, ACL denial, malformed payload, poison job, and unavailable Redis tests fail safely and observably.
- [ ] Backup/persistence, memory policy, eviction behavior, and recovery are documented and tested for required Redis data classes.
- [ ] **TASK COMPLETE — SEC-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.5 DATA-001 — Eliminate count overflow and make transaction accounting exact

**Depends on:** Phase 0. Keep unattended collection paused until complete.

**Acceptance criteria**

- [ ] Every external count that can exceed 32-bit range is inventoried and migrated to BIGINT in models and PostgreSQL, including current and snapshot/history fields.
- [ ] Pre-migration queries detect out-of-range, null, negative, truncated, and inconsistent values; results and repair decisions are recorded.
- [ ] The migration upgrades a realistic copy without truncation, table recreation data loss, unacceptable lock time, or silent coercion.
- [ ] Nested CRUD helpers no longer roll back a transaction owned by their caller; transaction ownership is explicit and documented.
- [ ] Per-row savepoints or validated atomic chunks ensure one invalid row cannot erase unrelated valid rows.
- [ ] inserted, updated/skipped, and failed totals are computed from durable commit outcomes and equal database reality after success, partial failure, rollback, retry, and worker termination.
- [ ] Boundary tests include 0, 2,147,483,647, 2,147,483,648, values above three billion, BIGINT maximum-policy boundary, negative input, null input, and malformed input.
- [ ] A mixed batch with a middle overflow/constraint error preserves valid rows exactly once and reports the exact failed row.
- [ ] A reconciliation query identifies affected historical runs/channels; approved repair or recollection is performed with before/after evidence.
- [ ] **TASK COMPLETE — DATA-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.6 REL-001 — Preserve typed upstream failures instead of recording false empty success

**Depends on:** Phase 0; coordinate with REL-002 and REL-014.

**Acceptance criteria**

- [ ] YouTube client/service functions never represent an exception, invalid response, authorization failure, quota failure, or retry exhaustion as an empty successful dictionary/list.
- [ ] Result states distinguish successful nonempty, successful empty, not found, invalid input, permanent failure, retryable failure, quota exhausted, authentication failure, and cancelled.
- [ ] Collection runs and jobs persist the correct terminal/nonterminal state, stable error code, retryability, items discovered/saved/failed, and safe summary.
- [ ] Only a syntactically and semantically valid provider response proving zero results may become completed-empty.
- [ ] Tests cover 400, 401, key-invalid 403, quota 403, 404, 408/timeout, 429 with Retry-After, 500/503, DNS failure, connection reset, malformed JSON, missing required fields, and legitimate empty data.
- [ ] UI/API messages distinguish empty data from failure and offer an appropriate retry/operator action.
- [ ] Metrics and alerts count upstream failures by typed cause without exposing API keys, full response bodies, or private data.
- [ ] Existing collection-run rows with inconsistent states are identified for DATA-016 reconciliation.
- [ ] **TASK COMPLETE — REL-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.7 MIG-001 — Build a non-destructive upgrade path for the legacy local database

**Depends on:** Phase 0 and DATA-001 schema decisions.

**Acceptance criteria**

- [ ] Supported historical schema fingerprints are documented, including the unversioned legacy videos.db shape and expected table/column variants.
- [ ] Startup detects an unsupported/stale schema before serving requests and returns a precise safe migration instruction instead of partial pages/500 errors.
- [ ] A sanitized legacy fixture containing representative channels, videos, nulls, timestamps, duplicates, and edge counts is committed for migration tests.
- [ ] A dedicated adoption/conversion path backs up first, transforms data, establishes Alembic version truth only after validation, and is idempotent or safely refuses a repeat.
- [ ] No migration uses blind stamp, drop/recreate, or destructive coercion as a shortcut.
- [ ] Before/after checks prove row counts, provider IDs, relationships, timestamps, required fields, and documented deduplication/repair outcomes.
- [ ] The converted fixture reaches current head and all core routes/jobs operate against it.
- [ ] Interruption at each migration phase can resume or recover using a documented tested procedure.
- [ ] The real legacy database is changed only after user authorization and a successful copy rehearsal.
- [ ] **TASK COMPLETE — MIG-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 3.8 MIG-002 — Remove model/migration drift and gate it in CI

**Depends on:** MIG-001 and current model decisions; pair with CI-003.

**Acceptance criteria**

- [ ] Every reported uniqueness/index/schema difference is reviewed as intentional model truth or migration truth; no generated change is accepted without semantic review.
- [ ] A new migration makes PostgreSQL match the intended SQLAlchemy metadata without dropping valid data or creating unvalidated duplicate constraints.
- [ ] Fresh PostgreSQL upgrade to head followed by Alembic/flask schema check reports no drift.
- [ ] Upgrade from the previous head on a realistic copy reports no drift and preserves invariants.
- [ ] SQLite check is clean if SQLite remains supported, with documented dialect-specific differences handled explicitly.
- [ ] Index/constraint names are deterministic and consistent across fresh and upgraded databases.
- [ ] CI fails when models change without a migration or when migrations contain unexpected destructive operations.
- [ ] **TASK COMPLETE — MIG-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 4. Phase 2 — Security perimeter and least privilege

### 4.1 SEC-010 — Separate database privileges and minimize secret distribution

**Depends on:** SEC-002 and migration strategy.

**Acceptance criteria**

- [ ] Separate identities exist for migration/schema owner, web read/write, worker, scheduler, read-only reporting/health, and backup/restore where responsibilities differ.
- [ ] Runtime identities cannot create/drop/alter schema, grant roles, bypass row policy, or access unrelated schemas/sequences.
- [ ] Each service receives only its own credential and required database/network access.
- [ ] Default/shared hard-coded database passwords are removed and rejected in production.
- [ ] Grant tests prove required queries succeed and prohibited DDL, credential-table access, and unrelated writes fail.
- [ ] Credential rotation is rehearsed without data loss or extended outage.
- [ ] Migrations run through an explicit privileged deployment step rather than normal web/worker startup.
- [ ] **TASK COMPLETE — SEC-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.2 SEC-009 — Run containers as constrained non-root workloads

**Depends on:** SEC-010 and storage ownership plan.

**Acceptance criteria**

- [ ] Application images define a fixed unprivileged UID/GID and all web/worker/scheduler processes run as it.
- [ ] Root filesystem is read-only where feasible; only documented data/temp paths are writable with least permissions.
- [ ] All Linux capabilities are dropped and only a justified minimum is restored; no-new-privileges is enabled.
- [ ] An init/signal strategy forwards termination and reaps children; graceful shutdown is tested.
- [ ] Resource limits/reservations cover CPU, memory, PIDs, open files, and temporary disk according to measured capacity.
- [ ] Secrets are not baked into images/layers and are unreadable to unrelated UIDs.
- [ ] Container escape/hardening scan and runtime inspection confirm the intended user, mounts, capabilities, seccomp/AppArmor policy, and writable paths.
- [ ] Web, worker, scheduler, PostgreSQL, and Redis restart and persist required data under the constrained configuration.
- [ ] **TASK COMPLETE — SEC-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.3 REL-016 — Define and enforce the production network perimeter

**Depends on:** SEC-001, SEC-008, SEC-009, and SEC-010.

**Acceptance criteria**

- [ ] Only the TLS ingress/reverse proxy publishes a host/public port; Flask/Gunicorn, Redis, and PostgreSQL bind only to required private networks/interfaces.
- [ ] Frontend, application, queue, and data networks are segmented so each service can reach only required peers.
- [ ] Ingress enforces modern TLS, request/body/header/time limits, safe proxy headers, and an allowlisted Host policy.
- [ ] The application trusts forwarded scheme/address/host only from named proxy hops and rejects spoofed forwarded headers.
- [ ] Egress is limited to required DNS, YouTube/provider, Sentry/telemetry, package-update, and approved secret services according to environment.
- [ ] Network tests prove unauthorized service-to-service paths and host access fail while required paths succeed.
- [ ] Firewall/security-group/Compose/IaC configuration is versioned, reviewed, scanned, and documented with a data-flow diagram.
- [ ] External reachability is tested from inside and outside the intended trust zone before release.
- [ ] **TASK COMPLETE — REL-016:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.4 SEC-004 — Establish TLS, cookies, browser headers, and cache policy

**Depends on:** SEC-001, SEC-003, and REL-016. Revalidate the CSP and asset directives after SEC-007 changes the delivery pipeline.

**Acceptance criteria**

- [ ] All production HTTP requests redirect safely to HTTPS at the trusted ingress; application URL generation recognizes the verified proxy scheme.
- [ ] HSTS is enabled only after HTTPS validation, with an approved max-age/includeSubDomains/preload decision.
- [ ] A restrictive Content-Security-Policy uses nonces/hashes or external self-hosted assets; unsafe-inline and unsafe-eval are absent unless narrowly risk accepted.
- [ ] CSP includes frame-ancestors and explicit default/script/style/img/font/connect/frame/form/base/object policies appropriate to the app.
- [ ] X-Content-Type-Options, Referrer-Policy, Permissions-Policy, and appropriate framing protections are present on all responses.
- [ ] Session cookies are Secure, HttpOnly, appropriately SameSite, scoped to the minimum path/domain, rotated on privilege change, and bounded by idle/absolute expiry.
- [ ] Sensitive/private/API/export responses use no-store; public static assets use versioned immutable caching.
- [ ] Automated response tests cover success, redirect, error, login, API, export, and static responses; a browser CSP report/test shows no required resource is blocked.
- [ ] **TASK COMPLETE — SEC-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.5 SEC-005 — Minimize diagnostics, errors, settings, and export disclosure

**Depends on:** SEC-001 and SEC-004; REL-014 later standardizes the full error contract.

**Acceptance criteria**

- [ ] Public liveness reveals only an opaque status/version policy; dependency URLs, queue names, workers, exception strings, paths, SQL, and secrets are absent.
- [ ] Detailed settings/operations diagnostics require the operator role and redact credentials, host details where unnecessary, token references, and private content.
- [ ] User-facing errors use stable safe codes/messages plus correlation IDs; raw exceptions remain only in access-controlled redacted telemetry.
- [ ] Export authorization separates public research, private analytics, credential metadata, and operational datasets.
- [ ] Credential references, emails/scopes, and private analytics are excluded by default and require explicit permission/confirmation when legitimately exported.
- [ ] Sensitive responses have no-store, download audit events, retention/expiry behavior, and filename/content-disposition hardening.
- [ ] Tests assert forbidden strings and fields never appear in anonymous/unauthorized responses or normal error pages.
- [ ] **TASK COMPLETE — SEC-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.6 SEC-013 — Enforce layered request and stored-data limits

**Depends on:** SEC-003 and proxy plan.

**Acceptance criteria**

- [ ] Proxy and Flask enforce documented request body, header, URL, multipart-part, field-count, and upload limits.
- [ ] Every stored string/text/list/numeric input has a justified maximum/minimum in request schema and, where practical, database constraints/types.
- [ ] Pagination, export size, job batch, max videos, transcript, note, URL, and nested payload limits are explicit and cannot be bypassed by alternate routes/content types.
- [ ] Oversized requests fail before expensive parsing/business logic with stable 413 or field-specific 422 responses.
- [ ] Boundary tests cover exactly-at-limit, one-over-limit, multibyte UTF-8, compressed/multipart amplification, many small fields, and missing Content-Length/chunked behavior at ingress.
- [ ] Logs and error messages truncate safely without splitting secrets or allowing log injection.
- [ ] Metrics record rejected size/rate classes without recording payload bodies.
- [ ] **TASK COMPLETE — SEC-013:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.7 SEC-011 — Validate and safely render all user-controlled URLs

**Depends on:** SEC-013.

**Acceptance criteria**

- [ ] One shared URL validator canonicalizes before validation and allowlists HTTPS for external links; any HTTP development exception is explicit and environment-bound.
- [ ] javascript, data, vbscript, file, blob, protocol-relative, credential-bearing, control-character, encoded-obfuscation, mixed-case, and whitespace-prefixed unsafe URLs are rejected.
- [ ] Stored legacy URLs are audited and quarantined/repaired before being rendered as clickable links.
- [ ] Templates use safe link helpers, noreferrer/noopener for new tabs, and clear external-link labeling.
- [ ] Redirect/fetch/embed/link use cases have separate allowlists rather than one overly broad validator.
- [ ] Unit and browser tests prove unsafe schemes cannot execute and valid internationalized HTTPS URLs follow the documented policy.
- [ ] **TASK COMPLETE — SEC-011:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.8 SEC-006 — Prevent spreadsheet formula injection in every export

**Depends on:** SEC-013; coordinate with PERF-001 and PERF-002.

**Acceptance criteria**

- [ ] A single tested sanitizer treats all untrusted CSV/XLSX cell values as data and is used by every spreadsheet export path.
- [ ] Leading equals, plus, minus, at-sign, tab, CR/LF, leading whitespace, apostrophe, BOM, and encoded/Unicode lookalike cases follow a documented neutralization policy.
- [ ] Trusted formula fields, if any, are explicitly typed and cannot be populated from provider/manual data.
- [ ] CSV quoting/encoding/line-ending behavior is RFC-compatible for the documented dialect and does not undo formula neutralization.
- [ ] Round-trip tests open representative files with supported spreadsheet software or a parser that verifies text-cell semantics.
- [ ] Regression tests cover titles, descriptions, notes, labels, thesis data, analytics, rights, and any new generic export writer.
- [ ] **TASK COMPLETE — SEC-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.9 SEC-007 — Replace browser CDN/runtime dependencies with a controlled asset pipeline

**Depends on:** SEC-002; coordinate the resulting lock and scan controls with SUP-001. This task must precede strict CSP completion in SEC-004.

**Acceptance criteria**

- [ ] Tailwind is built/purged at build time; the browser development CDN/runtime is absent from production.
- [ ] Toastify, Chart.js, Socket.IO client, fonts, and other required frontend dependencies are locked, built or vendored, fingerprinted, and self-hosted where feasible.
- [ ] Any unavoidable third-party browser asset is version pinned, integrity protected, allowlisted in CSP, privacy reviewed, and covered by an outage fallback.
- [ ] Inline scripts/styles are removed or receive per-response CSP nonces without reusable/static nonce values.
- [ ] Production assets are minified, content hashed, served with correct MIME/nosniff and immutable caching, and invalidated by filename on change.
- [ ] A clean offline/blocked-third-party browser test preserves core product functionality except explicitly documented external embeds.
- [ ] Dependency/license/vulnerability inventory includes frontend packages and generated bundles.
- [ ] **TASK COMPLETE — SEC-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.10 REL-012 — Make rate limits shared, identity-aware, and proxy-safe

**Depends on:** SEC-001, SEC-008, and REL-016.

**Acceptance criteria**

- [ ] Production rate-limit state uses a shared durable Redis namespace rather than per-process memory.
- [ ] Limit keys use authenticated actor/API client for protected actions and verified client address only where appropriate.
- [ ] Trusted-proxy count and forwarded-address parsing are explicitly configured and spoofing tests pass.
- [ ] Login, collection, export, search, metrics, mutation, and diagnostics have risk/cost-appropriate burst and sustained limits.
- [ ] Limits remain correct across three or more web instances, restarts, clock skew, and concurrent requests.
- [ ] 429 responses include safe retry guidance/Retry-After and do not reveal other users' activity.
- [ ] Operators can observe limit rejections and override only through audited least-privilege controls.
- [ ] **TASK COMPLETE — REL-012:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.11 SEC-012 — Make post-login redirects strictly same-origin

**Depends on:** SEC-001.

**Acceptance criteria**

- [ ] Redirect targets are parsed/canonicalized against the fixed application origin and accepted only as path/query/fragment on that origin.
- [ ] Backslashes, repeated/encoded slashes, control characters, userinfo, scheme-relative URLs, mixed encodings, Unicode separators, and absolute external URLs are rejected.
- [ ] Invalid next values fall back to a safe fixed route without reflecting unsafe content.
- [ ] Browser/proxy tests cover slash-backslash hostname forms and normalization differences in all supported clients.
- [ ] A reusable same-origin redirect helper is the only route from untrusted next/return values to redirects.
- [ ] **TASK COMPLETE — SEC-012:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.12 SEC-014 — Stop trusting client-supplied canonical metadata

**Depends on:** SEC-001, SEC-013, and REL-001.

**Acceptance criteria**

- [ ] The browser submits only an opaque server-side result reference or canonical provider ID; authoritative metadata is read from server state or refetched.
- [ ] Any temporary result token is authenticated, expires, is bound to actor/session and purpose, and cannot be replayed after save.
- [ ] Provider IDs, URLs, counts, timestamps, title/text lengths, and cross-field relationships are validated server-side.
- [ ] Tampering with hidden fields, IDs, channel/video relationships, counts, or result ownership cannot alter saved canonical facts.
- [ ] Stale-result behavior is explicit: reject, refresh, or save with recorded source timestamp/version.
- [ ] Tests cover forged tokens, another user's token, expired token, modified form fields, duplicate save, provider change, and upstream failure.
- [ ] **TASK COMPLETE — SEC-014:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.13 SEC-015 — Protect local databases, backups, logs, and environment files

**Depends on:** Phase 0 and SEC-002.

**Acceptance criteria**

- [ ] Secret, database, backup, and private log files are owned by the intended service/user and are not group/world readable; creation umask is restrictive.
- [ ] Backups are encrypted at rest and in transit using managed keys with tested access recovery and rotation.
- [ ] Retention and deletion schedules exist by data class; expired files are securely removed according to storage capability and policy.
- [ ] Backup/restore access is separately authorized and audited; production backups do not enter developer fixtures.
- [ ] Logs exclude secrets and minimize personal/private content; permissions and rotation prevent uncontrolled growth.
- [ ] Automated checks fail when sensitive paths have unsafe permissions, enter git/build context, or violate retention.
- [ ] Restore drills verify integrity without exposing the restored data to unauthorized users.
- [ ] **TASK COMPLETE — SEC-015:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 4.14 SEC-016 — Make telemetry privacy-safe, versioned, and cost-controlled

**Depends on:** SEC-005; coordinate structured correlation/error fields with the later REL-014 contract.

**Acceptance criteria**

- [ ] Telemetry records environment, release/commit, service role, correlation ID, and safe operation identifiers.
- [ ] send-default-PII and equivalent collection are disabled unless a documented lawful need and consent/control exist.
- [ ] Before-send/log processors remove API keys, cookies, authorization headers, DB URLs, emails where unnecessary, token references, SQL values, descriptions, transcripts, and form bodies.
- [ ] Trace/error sampling is environment- and event-aware, bounded by cost/volume, and preserves Critical failure evidence.
- [ ] Retention, residency, access, deletion, and incident-use policies are documented for the telemetry provider.
- [ ] Synthetic secret/PII canary tests prove sensitive values do not reach logs or Sentry.
- [ ] Alerts and dashboards distinguish release/environment and remain useful after redaction.
- [ ] **TASK COMPLETE — SEC-016:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 5. Phase 3 — Distributed jobs, dependencies, and operational correctness

### 5.1 REL-002 — Consolidate retries under one bounded policy

**Depends on:** REL-001; coordinate retry error fields with the later REL-014 contract.

**Acceptance criteria**

- [ ] Exactly one layer owns retries for each outbound call; nested urllib3/client/task retries cannot multiply attempts.
- [ ] Retry policy classifies idempotency and retryable transport/status/provider reasons; permanent failures are never blindly retried.
- [ ] Each operation has connect, read, per-attempt, and total monotonic deadlines plus a maximum attempt budget.
- [ ] Exponential backoff uses jitter, caps, and Retry-After within the total deadline.
- [ ] Logical calls, physical attempts, delays, status/reason, and quota units are separately observable.
- [ ] Tests with fake time prove exact maximum attempts/duration and no retry on invalid key, bad input, not found, or non-idempotent unsafe operations.
- [ ] A concurrency/outage test proves retry traffic remains bounded and does not synchronize into a thundering herd.
- [ ] **TASK COMPLETE — REL-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.2 REL-003 — Implement a durable, enforced YouTube quota ledger

**Depends on:** REL-002 and SEC-008.

**Acceptance criteria**

- [ ] Quota usage/reservations are atomic and shared across web, workers, scheduler, processes, and restarts.
- [ ] Ledger keys/rows use the provider's documented quota-day boundary and handle rollover deterministically.
- [ ] Endpoint costs include search, pagination, fallback resolution, retries where charged, batch sizes, and future endpoint additions through one reviewed table.
- [ ] Jobs reserve estimated quota before work, reject/defer when policy would exceed budget, and reconcile reservation to actual calls.
- [ ] Concurrent workers cannot reserve more than the configured budget; abandoned reservations expire/reconcile safely.
- [ ] UI/operations show used, reserved, remaining, reset time, estimate confidence, and blocked work without exposing keys.
- [ ] Provider call logs can reconcile ledger totals for a test day and explain any difference.
- [ ] Warning and hard-stop thresholds are configurable, audited, and tested.
- [ ] **TASK COMPLETE — REL-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.3 REL-004 — Make collection jobs idempotent and deduplicated

**Depends on:** DATA-001, REL-003, and SEC-008.

**Acceptance criteria**

- [ ] A documented idempotency key includes channel/provider ID, normalized parameters, actor/tenant, and collection window or explicit force/replay intent.
- [ ] Atomic database/Redis coordination allows only one active equivalent job and returns the existing job to duplicate requests.
- [ ] Database uniqueness and upsert rules protect canonical rows and per-run snapshots under concurrent workers.
- [ ] Locks use expiry plus fencing/ownership so a stale worker cannot commit after a newer owner takes over.
- [ ] Duplicate click, network retry, scheduler overlap, worker crash/restart, and two-process race tests produce one logical run and exact-once durable effects where required.
- [ ] Force recollection is separately authorized, visible, and cannot bypass quota or audit rules.
- [ ] Job/result API exposes deduplicated/reused status clearly.
- [ ] **TASK COMPLETE — REL-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.4 REL-005 — Separate queues and add cancellation, deadlines, and dead-letter handling

**Depends on:** REL-004 and SEC-008.

**Acceptance criteria**

- [ ] Workloads are classified into queues by latency/resource/risk, such as collection, transcript, metrics, and export, with documented worker concurrency.
- [ ] Every job has queue deadline, execution deadline, retry policy, idempotency key, priority policy, and maximum payload/result size.
- [ ] Cooperative cancellation is checked at safe points and produces cancelled status without partial untracked effects.
- [ ] Failed/exhausted/poison jobs move to an inspectable dead-letter path with safe reason, original identity, and controlled replay.
- [ ] Fairness prevents one channel/user/large job from indefinitely blocking unrelated work.
- [ ] Queue saturation, oldest age, runtime, cancellation latency, retry count, and dead-letter count are monitored.
- [ ] Tests cover slow transcript, large export, worker kill, cancellation during each phase, retry exhaustion, and recovery after Redis restart.
- [ ] **TASK COMPLETE — REL-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.5 REL-007 — Move heavy computation and exports out of request workers

**Depends on:** REL-005; coordinate export-specific resource work with PERF-001.

**Acceptance criteria**

- [ ] Metrics recomputation, large exports, and any operation that can exceed the request SLO return 202 with a durable authorized job/status resource.
- [ ] Web requests do not hold database transactions or materialized results while background work executes.
- [ ] Jobs write to staging/versioned outputs and publish atomically only after complete validation.
- [ ] Retrying a timed-out/client-disconnected request returns the existing job rather than duplicating work.
- [ ] Progress is based on durable stages/counts and never reaches 100% before output commit.
- [ ] Gunicorn request timeout no longer terminates legitimate heavy work; a test exceeds 30 seconds in the worker while web health remains responsive.
- [ ] Failed/cancelled jobs clean temporary state and preserve diagnostic evidence.
- [ ] **TASK COMPLETE — REL-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.6 PROD-002 — Give long-running work customer-grade status and recovery

**Depends on:** REL-004, REL-005, and REL-007.

**Acceptance criteria**

- [ ] A job center exposes queued, running, retry-wait, partial, completed, failed, cancelled, and expired states with timestamps.
- [ ] Progress includes meaningful stage, current/total where knowable, remaining estimate labeled as estimate, and last heartbeat.
- [ ] Authorized users can cancel, retry eligible failures, replay with explicit intent, and download per-item failure details.
- [ ] Page refresh, reconnect, another tab, and temporary network loss preserve accurate status.
- [ ] Duplicate submissions lead to the existing job with a clear explanation.
- [ ] Error messages state what happened, what was saved, whether retry is safe, and the next action without exposing internals.
- [ ] Keyboard and screen-reader users receive non-disruptive status updates and can perform every recovery action.
- [ ] End-to-end tests cover success, partial, failure, retry, cancellation, stale job, and authorization.
- [ ] **TASK COMPLETE — PROD-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.7 REL-008 — Apply bounded deadlines to every dependency

**Depends on:** REL-002 and REL-005.

**Acceptance criteria**

- [ ] PostgreSQL connect, pool checkout, lock, and statement timeouts are explicitly configured per workload and fail with typed errors.
- [ ] Redis connect/read/write/health timeouts and retry behavior are explicit.
- [ ] YouTube, transcript, telemetry, secret backend, and any future HTTP client have connect/read/total deadlines.
- [ ] Cancellation/deadline propagates from job/request to child operations where supported.
- [ ] Single-video collection honors the global transcript-disabled default unless the user explicitly opts in.
- [ ] Repeated dependency failures trip a bounded circuit/open state where appropriate and recover through a tested half-open policy.
- [ ] Fault-injection tests simulate hangs, slow reads, lock contention, DNS delay, and partial responses without exhausting all web/worker capacity.
- [ ] Metrics distinguish timeout layer and dependency.
- [ ] **TASK COMPLETE — REL-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.8 REL-006 — Deploy Socket.IO on a supported topology

**Depends on:** SEC-008, REL-005, and REL-016.

**Acceptance criteria**

- [ ] Production topology matches an explicitly supported Flask-SocketIO server/worker model; unsupported multi-worker Gunicorn balancing is removed.
- [ ] If multiple instances are used, the load balancer provides verified sticky sessions and Redis/message-queue coordination.
- [ ] WebSocket and long-polling transports both authenticate, authorize rooms, upgrade, reconnect, and disconnect correctly.
- [ ] Origin/CORS is allowlisted to intended application origins; wildcard origins are absent in production.
- [ ] Graceful deployment drains or reconnects clients without losing authoritative job status.
- [ ] Load tests across all instances show no unknown-session, cross-user event, duplicate event, missing event beyond documented recovery, or room-leak errors.
- [ ] The topology, commands, proxy settings, health checks, and scale procedure are documented and used by CI/staging.
- [ ] **TASK COMPLETE — REL-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.9 REL-009 — Separate liveness, readiness, startup, and protected diagnostics

**Depends on:** REL-008 and SEC-005.

**Acceptance criteria**

- [ ] Liveness performs no database/Redis/external query and reports only whether the process/event loop is alive.
- [ ] Readiness performs bounded checks for required database connectivity, expected migration head, Redis/queue availability, and critical configuration.
- [ ] Startup remains false until initialization/migration compatibility is established; orchestrator does not route traffic early.
- [ ] Dependency failure returns minimal structured 503 with no topology or raw exception.
- [ ] Detailed diagnostics are separately operator-authorized and redacted.
- [ ] Tests cover stale schema, DB down/slow, Redis down/slow, bad credentials, worker unavailable, and external YouTube outage according to whether each should affect readiness.
- [ ] Orchestrator health configuration uses correct endpoints, intervals, thresholds, and startup grace without restart storms.
- [ ] **TASK COMPLETE — REL-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.10 REL-010 — Make startup, shutdown, and reconnect resilient

**Depends on:** REL-008 and REL-009.

**Acceptance criteria**

- [ ] Compose/orchestrator dependency order uses health/readiness rather than process-start order alone.
- [ ] Web, worker, and scheduler retry initial dependency connections with bounded jitter and expose not-ready rather than crash-looping indefinitely.
- [ ] SIGTERM stops new work, completes or safely checkpoints in-flight work within a configured grace period, and exits predictably.
- [ ] Abrupt kill/restart cannot leave a job permanently running without lease expiry/recovery.
- [ ] Database/Redis restart and credential rotation fault tests recover without duplicate durable effects.
- [ ] Crash-loop, restart count, readiness duration, graceful-shutdown duration, and abandoned-job recovery are observable and alerted.
- [ ] Process supervision uses an init and documented restart policy with capped backoff.
- [ ] **TASK COMPLETE — REL-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.11 REL-011 — Make scheduling singleton, transactional, and timezone-explicit

**Depends on:** REL-004, REL-009, and REL-010.

**Acceptance criteria**

- [ ] Exactly one scheduler leader may dispatch a logical schedule at a time, using a renewable lease/election with fencing.
- [ ] Desired schedules are durable/versioned; update is atomic and cannot lose the old schedule before the new state is committed.
- [ ] Every schedule stores an IANA timezone, next-run preview, enabled state, owner, parameters, and audit history.
- [ ] Dispatch uses an idempotency key so leader failover or duplicate scheduler instances cannot create duplicate collection runs.
- [ ] DST transitions, timezone changes, clock skew, missed run, catch-up policy, disabled schedule, and concurrent edit tests are deterministic.
- [ ] UI/API states the timezone and next run unambiguously.
- [ ] Scheduler lag, missed/duplicate dispatch, leader state, and last successful run are monitored.
- [ ] **TASK COMPLETE — REL-011:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.12 REL-014 — Define a stable error and correlation contract

**Depends on:** SEC-005; supports all later phases.

**Acceptance criteria**

- [ ] HTML and API handlers consistently map 400, 401, 403, 404, 405, 409, 413, 422, 429, 500, 502/503, and timeout cases.
- [ ] API errors have a versioned schema containing stable code, safe message, correlation ID, field details where applicable, and retryability.
- [ ] Validation errors preserve submitted safe input and identify fields without echoing secrets.
- [ ] Every HTTP request, job, collection run, provider call, metric run, and export can be linked by correlation/causation IDs.
- [ ] Logs capture typed internal cause and stack only in protected telemetry; users never receive raw exception/SQL/path/credential text.
- [ ] Content negotiation returns appropriate HTML/JSON without generic framework debug pages.
- [ ] Contract tests cover every status/error family and assert redaction.
- [ ] **TASK COMPLETE — REL-014:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 5.13 REL-013 — Remove import-time side effects and isolate service roles

**Depends on:** REL-014 and configuration contract.

**Acceptance criteria**

- [ ] A validated settings object parses environment once during explicit startup and reports all invalid/missing fields together with safe messages.
- [ ] Web, worker, scheduler, migration, and CLI factories initialize only extensions/clients required by that role.
- [ ] SocketIO, limiter, database, and other extensions use stable init-app patterns without duplicate handler registration across app factories.
- [ ] Importing modules performs no network connection, job scheduling, database mutation, app creation, or environment-dependent irreversible work.
- [ ] Multiple app instances in one test process remain isolated and teardown releases resources.
- [ ] Invalid integer/float/URL/enum configuration tests fail before serving/processing with named fields and no secrets.
- [ ] Worker/scheduler startup tests run without unnecessary web initialization.
- [ ] **TASK COMPLETE — REL-013:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 6. Phase 4 — Database invariants, lineage, and durable domain correctness

### 6.1 DATA-004 — Enforce SQLite foreign keys or remove unsupported concurrency claims

**Depends on:** MIG-001 and MIG-002.

**Acceptance criteria**

- [ ] Every supported SQLite connection enables PRAGMA foreign_keys=ON through a tested connection hook before any write.
- [ ] Startup/test diagnostics verify the pragma and fail clearly when enforcement is unavailable.
- [ ] Insert/update/delete tests prove orphan rows and invalid references are rejected consistently.
- [ ] Behavior differences between SQLite and PostgreSQL are documented and cannot hide a production-only integrity failure.
- [ ] If SQLite is not intended for concurrent/runtime support, documentation and startup UI clearly limit it to the approved single-user/test use.
- [ ] Current SQLite files pass quick_check and foreign_key_check after migration, with any repair explicitly approved and evidenced.
- [ ] **TASK COMPLETE — DATA-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.2 DATA-016 — Reconcile historical run status and enforce operational invariants

**Depends on:** DATA-001 and REL-001.

**Acceptance criteria**

- [ ] A written state machine defines allowed collection-run/job states and transitions, including queued, running, retrying, partial, completed, failed, cancelled, and abandoned.
- [ ] completed cannot coexist with failed items unless the documented state is explicitly partial; items_saved/items_failed/items_found equations are defined.
- [ ] Database constraints or transactional service checks prevent impossible terminal combinations.
- [ ] A read-only reconciliation identifies all historical violations, including completed rows with failures and mismatched counts.
- [ ] Repair rules distinguish trustworthy correction, recollection required, and unknown; no historical value is invented.
- [ ] Approved data repair is reversible/audited and produces before/after counts and an exception list.
- [ ] Transition, retry, crash, partial batch, cancellation, and reconciliation tests preserve exact status semantics.
- [ ] **TASK COMPLETE — DATA-016:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.3 DATA-002 — Store one channel snapshot per channel collection

**Depends on:** DATA-001, REL-004, and DATA-016.

**Acceptance criteria**

- [ ] ChannelSnapshot creation occurs once at the channel/run sampling boundary, not inside per-video save behavior.
- [ ] A unique constraint protects the documented natural identity, normally channel plus collection run or channel plus exact sampling event.
- [ ] Concurrent/retried collections cannot create duplicate channel snapshots for one logical run.
- [ ] Historical duplicates are inventoried and deduplicated using a documented deterministic rule without removing distinct sampling events.
- [ ] Downstream time-series calculations are checked before/after repair and no longer count per-video duplicates as separate channel observations.
- [ ] Tests cover zero-video, one-video, 50-video, partial, retried, and concurrently deduplicated collections and assert exactly one intended channel snapshot.
- [ ] **TASK COMPLETE — DATA-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.4 DATA-006 — Encode domain ranges, states, and natural uniqueness in the database

**Depends on:** MIG-002 and domain review.

**Acceptance criteria**

- [ ] Every persisted count, percentage, rate, confidence, duration, score, money, sequence, and status is inventoried with nullability and valid domain.
- [ ] PostgreSQL CheckConstraints reject negative counts, non-finite/impossible rates, invalid percentages, invalid durations, and unsupported state values.
- [ ] UniqueConstraints enforce documented natural identities for labels, daily analytics, experiment checkpoints, video/asset links, derived metrics, and other idempotent records.
- [ ] Existing violations are reported and resolved through approved deterministic rules before constraints validate.
- [ ] Application validation matches database constraints and maps violations to stable 409/422 errors rather than 500.
- [ ] Concurrent duplicate submissions prove one durable record and a safe idempotent/conflict response.
- [ ] Migrations add large-table constraints/indexes with an operationally safe validation/lock plan.
- [ ] **TASK COMPLETE — DATA-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.5 DATA-005 — Index foreign keys and high-value query paths using measured plans

**Depends on:** MIG-002 and DATA-006.

**Acceptance criteria**

- [ ] Every foreign-key constraint is reviewed for leading-index coverage based on join, delete/update, and cascade behavior.
- [ ] Missing indexes are added only after duplicate/redundant index analysis; unused equivalents are not blindly accumulated.
- [ ] Representative EXPLAIN ANALYZE plans at production-like cardinality prove important joins, deletes, and filters avoid unacceptable scans/locks.
- [ ] Composite index column order matches actual predicates/order and pagination keys.
- [ ] Index build migration uses an appropriate low-lock/concurrent strategy for PostgreSQL and has failure cleanup instructions.
- [ ] Write/storage overhead and index size are recorded; indexes have a monitoring/removal policy.
- [ ] Query-plan regression tests or budgets protect the highest-risk paths.
- [ ] **TASK COMPLETE — DATA-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.6 DATA-007 — Store money and exact business values as Decimal/Numeric

**Depends on:** DATA-006.

**Acceptance criteria**

- [ ] Every monetary/exact quantity is inventoried with currency/unit, required precision, scale, rounding mode, and allowed range.
- [ ] Models and PostgreSQL use NUMERIC/Decimal with explicit precision/scale; binary Float is not used for exact financial values.
- [ ] Existing floats are analyzed for rounding ambiguity and migrated through a documented, approved rounding rule.
- [ ] API/forms/exports serialize decimal values without float conversion, scientific-notation surprise, or locale ambiguity.
- [ ] Arithmetic and aggregation use Decimal consistently and define currency mismatch behavior.
- [ ] Tests cover half rounding, very small/large values, negative-policy boundary, sum/reconciliation, import/export, and database round trip.
- [ ] **TASK COMPLETE — DATA-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.7 DATA-008 — Make time, date, and scheduling semantics explicit and timezone-aware

**Depends on:** MIG-002 and REL-011.

**Acceptance criteria**

- [ ] Every temporal field is classified as instant, local date, duration, provider date, schedule local time, or legacy text.
- [ ] Instants use timezone-aware UTC in application and TIMESTAMP WITH TIME ZONE or a documented equivalent in PostgreSQL.
- [ ] Legacy naive/text timestamps are parsed with a justified source timezone; ambiguous/unparseable rows are reported, not guessed silently.
- [ ] API/export includes ISO 8601 offsets/Z; UI states the display timezone and uses locale-aware formatting.
- [ ] Scheduling uses IANA timezone identifiers and documented DST gap/overlap behavior.
- [ ] Tests cover UTC, Asia/Baghdad, positive/negative offsets, DST transition zones, leap day, midnight grouping, provider quota reset, and serialization round trip.
- [ ] No application helper strips tzinfo from an instant.
- [ ] **TASK COMPLETE — DATA-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.8 DATA-015 — Enforce owned-analytics ownership, provenance, ranges, and uniqueness

**Depends on:** SEC-001, DATA-006, DATA-007, and DATA-008.

**Acceptance criteria**

- [ ] Owned analytics may be attached only to a channel/video with a verified current ownership/authorization relationship.
- [ ] Natural keys such as video plus analytics date and experiment plus checkpoint are unique and use idempotent import/update semantics.
- [ ] All numeric inputs require finite values and documented ranges; NaN, Infinity, negative-impossible values, and percentages outside policy are rejected at schema and database layers.
- [ ] Currency, unit, timezone/date definition, source system, credential/connection, import batch, retrieval time, and correction lineage are stored.
- [ ] Manual and automated data are distinguishable; corrections preserve before/after, actor, reason, and source.
- [ ] Authorization prevents public/research roles from reading or exporting private analytics.
- [ ] Tests cover ownership revoked, wrong tenant/user, duplicate date, stale credential, partial import, corrected row, extreme numeric values, and export privacy.
- [ ] **TASK COMPLETE — DATA-015:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.9 DATA-013 — Make rights readiness derived, versioned, and invalidated by dependency changes

**Depends on:** DATA-006; coordinate rights-record conflict handling with the later DATA-009 optimistic-concurrency task.

**Acceptance criteria**

- [ ] A rights-readiness rule set names every required input, including asset license, source, attribution text when required, disclosure, link state, reviewer, and evidence.
- [ ] Readiness is derived from current versioned inputs or a signed snapshot tied to exact asset/link/license versions.
- [ ] Any relevant asset, link, license, attribution, disclosure, or policy change invalidates prior readiness until recomputed/reviewed.
- [ ] Database constraints prevent duplicate active asset links and incomplete required attribution.
- [ ] UI clearly distinguishes current-ready, stale, failed, pending review, and historical ready states with reasons.
- [ ] Tests cover license expiry/change, asset removal, attribution-required with empty text, disclosure change, concurrent review, and restored readiness.
- [ ] Historical checklist records remain auditable and cannot be mistaken for current truth.
- [ ] **TASK COMPLETE — DATA-013:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.10 DATA-014 — Make credential revocation real and accurately represented

**Depends on:** SEC-001, SEC-002, and external provider/secret-backend design.

**Acceptance criteria**

- [ ] Product language distinguishes local disable, secret deletion, provider token revocation, and verified disconnected status.
- [ ] Revoke performs the supported external provider revocation and secret-backend disable/delete before or transactionally with local terminal state.
- [ ] Partial failure produces a retryable revocation-pending state, not a false revoked state.
- [ ] Revocation is idempotent, operator/audit visible, and prevents future sync/job use immediately.
- [ ] Token/reference values are never displayed or exported beyond the minimum authorized metadata.
- [ ] Tests simulate provider success, already revoked, provider unavailable, secret deletion failure, retry, and concurrent sync.
- [ ] A manual staging test verifies the revoked credential can no longer access the provider.
- [ ] **TASK COMPLETE — DATA-014:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.11 DATA-012 — Implement reproducible raw-source or normalized-event lineage

**Depends on:** SEC-015, DATA-008, and privacy/retention decision.

**Acceptance criteria**

- [ ] A written decision selects privacy-reviewed raw response storage or an immutable normalized source event sufficient for replay and explains exclusions.
- [ ] Stored lineage includes request purpose/endpoint/parameters with secrets removed, provider response/request identifiers, retrieval time, checksum, schema/parser version, collection run, and retention class.
- [ ] Payload/event content is compressed/encrypted/access-controlled and separated from normal application queries.
- [ ] Retention/deletion handles provider policy, privacy requests, credentials, transcripts, and owned analytics correctly.
- [ ] Parser replay can reproduce normalized output for a fixture and compare old/new parser versions without mutating current data.
- [ ] Corrupt/missing payload, checksum mismatch, redaction, schema evolution, and deletion tests are present.
- [ ] RAW_PAYLOAD_STORAGE_ENABLED and documentation reflect actual implemented behavior; dead placeholders/claims are removed.
- [ ] **TASK COMPLETE — DATA-012:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.12 DATA-009 — Prevent silent lost updates with optimistic concurrency

**Depends on:** SEC-001 and DATA-006.

**Acceptance criteria**

- [ ] Editable records with concurrent risk have a version/updated token included in forms/API representations.
- [ ] Update/delete requires the expected version through an atomic predicate; stale writes return 409 and do not overwrite current data.
- [ ] Conflict UI shows that the record changed, preserves the user's draft, and offers reload/compare/reapply rather than silent loss.
- [ ] Audit history records actor, previous/new version, reason where required, and correlation ID.
- [ ] Two-tab/two-user tests cover update-update, update-delete, stale retry, bulk action, and automated job versus manual edit.
- [ ] APIs use ETag/If-Match or an equivalently documented contract where appropriate.
- [ ] **TASK COMPLETE — DATA-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.13 DATA-003 — Remove redundant canonical/history storage or define authoritative semantics

**Depends on:** DATA-012 and migration/replay needs.

**Acceptance criteria**

- [ ] Every duplicated field/table pair is inventoried with readers, writers, retention, and claimed source of truth.
- [ ] One canonical representation is selected for description, transcript, subscribers, video/channel snapshots, metadata changes, and history concepts.
- [ ] Redundant fields/tables are removed through a staged compatibility migration or retained only with an explicit distinct semantic and invariant.
- [ ] Read/write paths cannot update one copy without the other during transition; compatibility views/backfill are tested.
- [ ] Historical/current consumers and exports migrate without silent meaning changes.
- [ ] After migration, invariants and storage/query improvements are measured and no ambiguous duplicate source remains in documentation.
- [ ] **TASK COMPLETE — DATA-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.14 DATA-010 — Define a safe SQLite execution mode

**Depends on:** DATA-004 and supported-environment decision.

**Acceptance criteria**

- [ ] Documentation and startup enforce whether SQLite is test-only, single-user local, or a supported runtime; concurrent multi-process claims are absent unless proven.
- [ ] If supported locally, WAL, busy timeout, foreign keys, transaction isolation, backup, and single-writer assumptions are explicitly configured.
- [ ] Web plus worker concurrency/lock tests at the supported limit complete without unexplained database-is-locked/data-loss behavior.
- [ ] Unsupported topologies fail startup or show an unmistakable warning and migration path to PostgreSQL.
- [ ] Backup/restore and crash-recovery tests pass under the selected journal mode.
- [ ] PostgreSQL remains the required production integration-test and deployment target.
- [ ] **TASK COMPLETE — DATA-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 6.15 DATA-011 — Standardize scalable internal and provider identifiers

**Depends on:** MIG-002 and expected scale review.

**Acceptance criteria**

- [ ] Every primary key, foreign key, provider ID, and high-growth sequence is inventoried with expected lifetime cardinality.
- [ ] High-growth internal IDs/foreign keys use compatible BIGINT types; all referencing columns and sequences match exactly.
- [ ] Provider IDs are immutable strings with canonical normalization, length bounds, uniqueness, and indexes matching lookup behavior.
- [ ] Distributed UUID/ULID identifiers are introduced only where offline/distributed creation requires them and ordering/privacy tradeoffs are documented.
- [ ] Migration preserves references and sequence values and tests values beyond 32-bit range.
- [ ] API/export contracts distinguish internal IDs from provider IDs and do not make mutable database IDs a cross-tenant authorization substitute.
- [ ] **TASK COMPLETE — DATA-011:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 7. Phase 5 — Reproducible supply chain, CI, and maintainable delivery

### 7.1 SUP-001 — Lock, upgrade, scan, and reproduce Python/frontend dependencies

**Depends on:** Phase 1; coordinate with SEC-007.

**Acceptance criteria**

- [ ] Runtime, development, test, and optional dependency groups have one source of truth and no package is installed separately/unpinned in Docker or CI.
- [ ] Resolved lock files pin exact versions and cryptographic hashes for each supported Python/platform environment.
- [ ] A clean image/environment installs solely from the lock with no undeclared dependency and passes pip check.
- [ ] All known Critical/High advisories are eliminated or carry documented owner, exploitability analysis, compensating control, expiry, and approval.
- [ ] Major upgrades are performed in compatibility-tested batches with changelog/migration review, not blind latest-version replacement.
- [ ] Automated dependency and license scans cover Python, frontend, container OS, and generated artifacts on PR and schedule.
- [ ] SBOM and dependency provenance are generated for the release and match the built image.
- [ ] **TASK COMPLETE — SUP-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.2 SUP-002 — Pin images and CI actions immutably and automate reviewed updates

**Depends on:** SUP-001.

**Acceptance criteria**

- [ ] Every production base/service image is pinned by verified digest while retaining a human-readable version annotation.
- [ ] Every third-party GitHub Action is pinned to a full commit SHA verified from the intended repository.
- [ ] Automated tooling proposes digest/SHA updates with release/advisory context, CI results, and human review.
- [ ] CI verifies no mutable tag/action reference enters protected workflows or production Compose/IaC.
- [ ] Built-image provenance records source commit, builder, base digests, lock hashes, and SBOM.
- [ ] Rollback selects a previously attested digest rather than rebuilding a mutable tag.
- [ ] **TASK COMPLETE — SUP-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.3 CI-001 — Test the real PostgreSQL/Redis/RQ/Socket.IO deployment architecture

**Depends on:** REL-006, REL-009, SUP-001, and SUP-002.

**Acceptance criteria**

- [ ] CI has a fast unit lane and an integration lane using supported PostgreSQL and Redis versions with health/readiness gates.
- [ ] Integration tests run actual web, worker, scheduler, queue, migration, and Socket.IO components using production-like configuration.
- [ ] End-to-end tests cover authenticated collect, job progress, persistence, retry/partial failure, metrics, export, and authorization.
- [ ] Service restart, stale schema, unavailable dependency, worker crash, and Socket.IO reconnect cases run deterministically.
- [ ] CI uses isolated unique databases/Redis namespaces and cleans up even on failure.
- [ ] Logs/artifacts are redacted and retained long enough to debug failures.
- [ ] A release cannot pass on SQLite-only evidence.
- [ ] **TASK COMPLETE — CI-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.4 CI-003 — Gate every schema and supported-version migration

**Depends on:** MIG-001, MIG-002, and CI-001.

**Acceptance criteria**

- [ ] CI upgrades a blank PostgreSQL database and every supported sanitized historical fixture to head.
- [ ] Alembic schema drift check passes after fresh and incremental upgrades.
- [ ] Data migration assertions verify row counts, relationships, constraints, semantic transforms, and anomaly reports.
- [ ] Migration SQL/operations are reviewed for destructive changes, table locks, rewrite size, transaction behavior, and rollback/recovery.
- [ ] Interrupted/failing migration recovery is tested for high-risk revisions.
- [ ] Model changes without migration and multiple-head/branch mistakes fail CI.
- [ ] **TASK COMPLETE — CI-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.5 CI-002 — Enforce meaningful coverage on critical behavior

**Depends on:** CI-001.

**Acceptance criteria**

- [ ] CI measures line and branch coverage and fails below documented repository and changed-code floors.
- [ ] Stricter critical-path requirements cover auth/authorization, CSRF, migrations, transaction rollback, job state, retry/quota, export sanitization, and data constraints.
- [ ] Scheduler and worker startup/runtime modules are executed by tests rather than remaining unimported.
- [ ] Coverage exclusions are minimal, reviewed, and justified in configuration.
- [ ] Mutation testing or targeted fault tests prove critical assertions fail when behavior is deliberately broken.
- [ ] Coverage trend is published without rewarding low-value tests or blocking justified refactoring solely by percentage.
- [ ] **TASK COMPLETE — CI-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.6 CI-004 — Add layered security and software-supply-chain gates

**Depends on:** SUP-001 and SUP-002.

**Acceptance criteria**

- [ ] PR and scheduled CI run secret-history scan, dependency/advisory scan, SAST, container/OS scan, IaC/Compose scan, and license policy checks.
- [ ] Appropriate CodeQL or equivalent semantic analysis covers Python and workflow files.
- [ ] Staging runs authenticated DAST/API tests against the supported deployment without destructive production behavior.
- [ ] Findings have severity, owner, due date, evidence, and time-bounded suppression containing reason and compensating control.
- [ ] Critical/High findings block release unless an explicitly authorized exception exists.
- [ ] SBOM, signed provenance/attestation, scan results, and release commit are retained together.
- [ ] Scanner credentials/tokens use least privilege and findings/logs do not expose secrets.
- [ ] **TASK COMPLETE — CI-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.7 CI-005 — Harden GitHub Actions permissions and execution controls

**Depends on:** SUP-002.

**Acceptance criteria**

- [ ] Workflow/job permissions are explicit and default to contents read; write/id-token permissions exist only for named required jobs.
- [ ] Jobs have explicit timeouts and concurrency groups cancel superseded PR/branch runs safely.
- [ ] Protected environments require approval for deployment/secrets and prevent untrusted PR code from privileged contexts.
- [ ] Workflow files and dependency-update configuration have CODEOWNERS/review protection.
- [ ] Untrusted inputs are never interpolated into generated shell; intermediate environment/action inputs and safe quoting are used.
- [ ] Caches/artifacts are scoped and treated as untrusted across privilege boundaries.
- [ ] CI includes a workflow-security scan and test of fork/PR permission behavior.
- [ ] **TASK COMPLETE — CI-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.8 CI-006 — Enforce one supported Python and developer environment contract

**Depends on:** SUP-001.

**Acceptance criteria**

- [ ] Supported Python version(s) are declared consistently in README, tooling, CI, Docker, lock metadata, and a version-manager/dev-container file.
- [ ] Startup/preflight rejects unsupported interpreters with a clear instruction before dependency/build failures.
- [ ] Clean setup is tested on every supported OS/interpreter combination or limitations are explicit.
- [ ] Native/build dependencies such as PostgreSQL drivers install reproducibly without relying on accidental local state.
- [ ] Adding/removing a supported version requires dependency resolution, full CI, migration, and runtime compatibility evidence.
- [ ] **TASK COMPLETE — CI-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.9 CI-007 — Make development environment-variable loading accurate and safe

**Depends on:** SEC-002 and CI-006.

**Acceptance criteria**

- [ ] One documented local startup path either explicitly loads a development dotenv file or requires exported/Compose variables; documentation matches executable behavior.
- [ ] Dotenv loading is development-only or cannot override production secret injection unexpectedly.
- [ ] .env.example contains names and safe placeholders, never live/default credentials, and documents required/optional/type constraints.
- [ ] Missing/invalid configuration fails through the validated settings contract rather than insecure fallback.
- [ ] Tests cover local dotenv, explicit environment precedence, production rejection, missing file, malformed values, and secret redaction.
- [ ] **TASK COMPLETE — CI-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.10 CI-008 — Standardize the local Compose/test entrypoint

**Depends on:** CI-006 and CI-007.

**Acceptance criteria**

- [ ] Scripts, README, CI, and runbooks use the same supported Docker Compose v2 command and service/profile names.
- [ ] The launcher performs version/config/port/secret/data preflight and exits with actionable safe errors.
- [ ] A clean checkout can run the documented local test command successfully.
- [ ] The command uses isolated test data and cannot accidentally mutate a developer/production database without explicit confirmation.
- [ ] Shell behavior is noninteractive in CI, handles signals, returns the underlying failure code, and cleans temporary services.
- [ ] **TASK COMPLETE — CI-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.11 CI-010 — Eliminate accepted warnings and resource leaks

**Depends on:** CI-001 and CI-002.

**Acceptance criteria**

- [ ] Every current warning is classified, assigned, and either fixed or covered by a time-bounded documented upstream exception.
- [ ] Unclosed SQLite/DB/session/file/socket/thread resources are fixed and targeted ResourceWarning tests fail if reintroduced.
- [ ] Deprecated SQLAlchemy Query.get and other APIs are replaced before removal deadlines.
- [ ] CI treats selected deprecation/resource/runtime warnings as errors and has a zero-new-warning gate.
- [ ] Test teardown proves database connections, worker threads, clients, temp files, and app contexts return to baseline.
- [ ] Warning counts are visible and do not differ silently between normal and coverage runs.
- [ ] **TASK COMPLETE — CI-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.12 CI-009 — Add frontend behavior, accessibility, and browser gates

**Depends on:** SEC-007 and CI-001; complete before UX phase closure.

**Acceptance criteria**

- [ ] Frontend source has lint/format rules and template/static syntax validation.
- [ ] Playwright or equivalent runs critical authenticated journeys on supported Chromium plus at least one independent browser engine.
- [ ] Automated axe-core scans cover every primary page, modal/menu/tab state, error state, light/dark mode, and responsive breakpoint.
- [ ] Tests cover keyboard navigation, focus order/return, live status, form errors, polling race, reduced motion, and no-JavaScript fallback where required.
- [ ] Visual/regression checks cover mobile, tablet, desktop, 200% zoom, and representative long/empty/error data.
- [ ] Serious/critical accessibility violations and critical browser journey failures block CI.
- [ ] **TASK COMPLETE — CI-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.13 MAINT-003 — Remove tracked runtime artifacts and prevent recurrence

**Depends on:** Phase 0 backup and secret/data review.

**Acceptance criteria**

- [ ] dump.rdb, Python bytecode/cache, and other runtime state are removed from tracking without deleting required live data.
- [ ] Ignore/build-context rules cover Redis dumps, DBs, backups, logs, env files, caches, coverage, temp exports, and editor/runtime artifacts.
- [ ] Git history is scanned for sensitive/private runtime content; any exposure is handled through approved rotation/history-remediation policy.
- [ ] Sanitized test fixtures live only in explicit fixture paths with provenance and no secrets/private data.
- [ ] CI fails when prohibited runtime artifact patterns are tracked or included in the container build context.
- [ ] **TASK COMPLETE — MAINT-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.14 MAINT-002 — Make documentation state and executable controls agree

**Depends on:** Relevant behavior changes throughout prior phases.

**Acceptance criteria**

- [ ] Every phase document/ADR/control claim is labeled proposed, implemented, verified, deprecated, or superseded.
- [ ] Implemented requirements link to the enforcing code, test, migration, metric, or runbook evidence.
- [ ] Raw payload, security, background jobs, analytics repeatability, scale, OAuth, and production claims match actual behavior.
- [ ] CI or a documentation review check detects broken internal links, duplicate current guidance, and stale commands/configuration.
- [ ] A single operations/setup path is designated current; obsolete paths redirect or are clearly archived.
- [ ] Release review confirms user/operator documentation changed with behavior.
- [ ] **TASK COMPLETE — MAINT-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 7.15 MAINT-001 — Decompose large modules along tested domain boundaries

**Depends on:** Stable behavior/tests from earlier phases; do not perform as speculative rewrite.

**Acceptance criteria**

- [ ] A dependency/ownership map identifies route, validation, application service, transaction, query/repository, serializer/export, and presentation responsibilities.
- [ ] Refactoring is incremental and behavior-preserving with characterization tests before each extraction.
- [ ] Transaction boundaries and authorization remain at explicit application-service boundaries, not scattered helpers.
- [ ] Domain packages have acyclic or intentionally layered dependencies and no import-time side effects.
- [ ] Large export, routes, models, and route-test modules are split by coherent behavior, not arbitrary line count.
- [ ] Full API/export/database compatibility and performance/query budgets pass after each step.
- [ ] ADR/module documentation explains boundaries and where new behavior belongs.
- [ ] **TASK COMPLETE — MAINT-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 8. Phase 6 — Performance, capacity, and scalable delivery

### 8.1 PERF-003 — Make data-viewer requests resource-specific and race-safe

**Depends on:** DATA-005, REL-014, and CI-009.

**Acceptance criteria**

- [ ] The API queries/counts only the requested visible resource rather than videos, channels, and history on every refresh.
- [ ] Each resource has independent validated pagination, filter, and stable sort state with bounded page size.
- [ ] Cursor/keyset pagination is used where offset cost or concurrent changes make offset unreliable.
- [ ] Browser requests use AbortController or monotonic request identity so stale/slow responses cannot overwrite newer state.
- [ ] Auto-refresh pauses when hidden/offline, backs off with jitter on failure, and never creates overlapping polls.
- [ ] ETag/conditional requests or documented cache policy avoids retransmitting unchanged data.
- [ ] Query count, scanned rows, response bytes, and latency budgets pass with production-like data for each tab.
- [ ] Tests cover rapid tab/filter/sort changes, slow response ordering, deleted/inserted rows, last page, empty/error state, and background visibility.
- [ ] **TASK COMPLETE — PERF-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.2 PERF-004 — Replace N+1 metrics and packaging queries with set-based access

**Depends on:** DATA-005; coordinate query keys and result identity with the DS-006 design.

**Acceptance criteria**

- [ ] Instrumented tests establish query counts and plans for metric recomputation, channel summaries, recent peers, snapshots, and packaging changes.
- [ ] Per-row snapshot/peer/change queries are replaced by bounded eager loads, window/set SQL, or precomputed versioned aggregates.
- [ ] Query count remains constant or logarithmically justified as result count grows; explicit budgets fail regression tests.
- [ ] Results are exactly equivalent to approved metric definitions for fixtures covering ties, nulls, missing snapshots, and channel boundaries.
- [ ] EXPLAIN ANALYZE with production-like cardinality meets documented latency/scan/memory budgets.
- [ ] Set-based processing respects transaction, cancellation, algorithm run, and tenant/authorization boundaries.
- [ ] **TASK COMPLETE — PERF-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.3 PERF-005 — Bound every detail, dashboard, selector, and relationship query

**Depends on:** DATA-005 and UX/product selector design.

**Acceptance criteria**

- [ ] Channel detail, thesis dashboard, rights/analytics selectors, evidence lists, and every unbounded collection have server-side bounds.
- [ ] Stable cursor pagination/search defines deterministic ordering and handles concurrent insert/delete without unacceptable duplicates/skips.
- [ ] Relationship loading is batched and protected by query-count budgets.
- [ ] UI preserves filters and provides total/approximate count only where its cost is acceptable.
- [ ] Hard maximum page/query complexity prevents malicious or accidental unbounded requests.
- [ ] Tests use datasets beyond expected near-term scale and cover first/last page, missing cursor, stale cursor, empty results, and unauthorized records.
- [ ] **TASK COMPLETE — PERF-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.4 PERF-001 — Stream or background large exports with bounded resources

**Depends on:** REL-005, REL-007, SEC-006, and PERF-005.

**Acceptance criteria**

- [ ] Export queries use server-side cursors/chunks and never materialize the complete dataset plus serialized copies in process memory.
- [ ] ZIP/CSV writers emit incrementally to controlled temporary/object storage with explicit memory, disk, row, file, and time limits.
- [ ] Export runs as an idempotent cancellable background job for nontrivial sizes and publishes output atomically after validation.
- [ ] Temporary files/partial objects are removed in finally/reaper paths after success, failure, timeout, cancellation, and process kill.
- [ ] Downloads are authorized at request time, expire, use unpredictable identifiers/signed access, and are no-store/audited.
- [ ] Load tests record peak RSS, temp disk, DB impact, runtime, and concurrent-export fairness at maximum supported size.
- [ ] Output row counts, manifest checksums, encoding, formula safety, and source snapshot/run identity are validated before completion.
- [ ] **TASK COMPLETE — PERF-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.5 PERF-002 — Replace heterogeneous concatenated CSV with a valid versioned package

**Depends on:** PERF-001 and SEC-006.

**Acceptance criteria**

- [ ] Each CSV is a single rectangular table with one header/schema and documented encoding, delimiter, newline, null, date, decimal, and escaping semantics.
- [ ] Multi-table export is a ZIP/package containing one file per table plus a versioned manifest with schema versions, row counts, checksums, creation time, and source/run identity.
- [ ] Existing combined-CSV behavior is removed or versioned/deprecated with migration guidance; it is not labeled standard CSV.
- [ ] Generic CSV parsers can read every file without special marker-line logic.
- [ ] Import/round-trip contract tests preserve Unicode, newlines, nulls, decimal/time values, IDs, and formula-neutralized text.
- [ ] Backward compatibility and retention policy for old exports are documented.
- [ ] **TASK COMPLETE — PERF-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.6 PERF-006 — Build a production static-delivery and page-weight strategy

**Depends on:** SEC-007.

**Acceptance criteria**

- [ ] Local assets use content-hashed filenames, correct MIME, immutable caching, and a release manifest.
- [ ] HTML/private dynamic responses use appropriate no-cache/no-store behavior; stale asset references fail visibly in build tests.
- [ ] Ingress serves Brotli/gzip where beneficial and resists compression of already-compressed or secret-reflecting contexts according to threat review.
- [ ] Images have responsive sizes/formats, dimensions/aspect ratio, lazy/eager priority policy, and fallback.
- [ ] Page budgets define compressed JS/CSS/image/font/HTML sizes, request count, and Core Web Vitals targets for representative pages.
- [ ] CI or performance tests block material budget regressions and test cold/slow-network behavior.
- [ ] **TASK COMPLETE — PERF-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 8.7 REL-015 — Establish measurable SLOs and a tested capacity envelope

**Depends on:** REL-009, CI-001, and performance tasks above.

**Acceptance criteria**

- [ ] Service-level indicators define request/job availability, latency, correctness/completeness, queue delay, freshness, and export success from the customer's perspective.
- [ ] Initial SLO targets and error-budget policy are approved for internal, beta, and general-availability stages.
- [ ] Dashboards expose traffic, errors, latency percentiles, saturation, queue oldest age, dependency latency, quota, DB pool/locks, Redis memory, disk, and data-quality counts.
- [ ] Alerts are symptom/SLO based, actionable, deduplicated, routed, and linked to tested runbooks; no alert depends solely on average latency.
- [ ] Load, spike, soak, failover, and recovery tests establish maximum supported users, channels, videos, job concurrency, exports, and database size with headroom.
- [ ] Capacity results include p50/p95/p99, errors, saturation, query counts, memory/disk growth, and limiting component.
- [ ] Release gates fail when SLO or capacity budgets regress beyond approved tolerance.
- [ ] **TASK COMPLETE — REL-015:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 9. Phase 7 — Statistically honest analytics and research methodology

Do not present revised metrics as validated customer decision tools until DS-001 through DS-009 are complete and the validation report has been reviewed by a qualified analyst.

### 9.1 DS-006 — Make metric runs immutable, versioned, and exclusively queryable

**Depends on:** DATA-012 and DATA-016; coordinate query-performance changes with PERF-004.

**Acceptance criteria**

- [ ] Every metric run has immutable run ID, algorithm semantic version, code commit, configuration/threshold hash, input snapshot/run IDs, start/end time, and status.
- [ ] A natural uniqueness rule prevents duplicate metrics for one run/entity/metric identity.
- [ ] Recompute writes to a new staging run and atomically promotes one approved active run; it never mixes partial old/new rows.
- [ ] All dashboard, analysis, packaging, export, and API queries explicitly bind to one run or the promoted active run.
- [ ] Old runs remain reproducible/inspectable or expire through documented retention; changing version cannot silently change historical output.
- [ ] Tests create two algorithm versions and prove no query returns a mixed/duplicated result and failed promotion leaves the old active run intact.
- [ ] **TASK COMPLETE — DS-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.2 DS-002 — Preserve missingness instead of coercing unknown values to zero

**Depends on:** DS-006 and DATA-006.

**Acceptance criteria**

- [ ] Every metric input defines observed zero, missing, hidden, unavailable, not applicable, provider error, and not-yet-observed semantics where relevant.
- [ ] Parsers and persistence retain null plus missingness reason rather than defaulting absent counts to zero.
- [ ] Metric eligibility explicitly handles each missingness class and never silently includes unknown as zero.
- [ ] UI/export displays unknown/hidden/unavailable distinctly from 0 and reports data coverage/sample counts.
- [ ] Existing coerced-zero rows are assessed; repair/recollection is performed where source evidence permits and otherwise marked unknown.
- [ ] Tests prove missing likes/comments/subscribers/views do not bias rates/rankings and true observed zeros remain valid.
- [ ] **TASK COMPLETE — DS-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.3 DS-001 — Compare performance using age- and exposure-appropriate windows

**Depends on:** DS-002 and DS-006.

**Acceptance criteria**

- [ ] A written metric specification defines the question, eligible population, observation window, censoring, numerator/denominator, timezone, and update timing.
- [ ] Lifetime views of materially different video ages are not directly treated as comparable performance.
- [ ] Approved fixed windows such as 24h/7d/28d or an age-conditioned model use snapshots with sufficient observation coverage.
- [ ] Sub-day age is not clipped to one day in a way that materially biases results; not-yet-observable windows are marked incomplete.
- [ ] Cohorts control at minimum for channel and comparable exposure/age; additional content/season effects are documented.
- [ ] Fixtures with known growth curves, newly published videos, old videos, missing snapshots, deleted/private videos, and delayed collection produce expected classifications.
- [ ] UI names the exact window/cohort and displays sample size, coverage, and uncertainty.
- [ ] **TASK COMPLETE — DS-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.4 DS-003 — Prevent confident output from inadequate samples

**Depends on:** DS-001 and DS-002.

**Acceptance criteria**

- [ ] Each metric defines minimum eligible sample, coverage, recency, and variance requirements based on validation rather than arbitrary UI convenience.
- [ ] A one-video/self-comparison cohort returns insufficient_data, not a meaningful 1.0 benchmark.
- [ ] Small/noisy cohorts use an approved robust/shrinkage method or return insufficient_data with explanation.
- [ ] Outputs include sample size, effective sample, uncertainty interval/stability grade, and exclusions.
- [ ] Threshold-boundary and resampling/sensitivity tests show classification stability or explicitly report instability.
- [ ] UI/export cannot sort/display insufficient metrics as equivalent to measured values.
- [ ] **TASK COMPLETE — DS-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.5 DS-004 — Use honest opportunity and under-served terminology

**Depends on:** DS-001 through DS-003.

**Acceptance criteria**

- [ ] Every opportunity/under-served label has an operational definition listing exactly what is and is not measured.
- [ ] If demand and supply are not measured/validated, labels and marketing copy are renamed to descriptive terms such as observed high-performing labeled candidate.
- [ ] If the claim is retained, validated demand, supply, addressable audience, competition, and uncertainty inputs are added with lineage.
- [ ] No causal or market-opportunity language is inferred solely from relative-performance outliers.
- [ ] UI includes a plain-language explanation, coverage, caveats, and link to metric version.
- [ ] User comprehension tests show target users interpret the label consistently with its actual evidence.
- [ ] **TASK COMPLETE — DS-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.6 DS-005 — Validate and backtest every decision metric

**Depends on:** DS-001 through DS-004 and DS-006.

**Acceptance criteria**

- [ ] A versioned evaluation dataset has documented sampling, leakage prevention, temporal split, labels/outcomes, exclusions, and privacy.
- [ ] Each metric has a baseline, primary validation measure, calibration/stability measure, and business error-cost interpretation.
- [ ] Temporal holdout/backtest reports predictive/descriptive performance, confidence intervals, sensitivity, false-positive/negative cases, and subgroup/channel effects.
- [ ] Thresholds are selected using the training/validation policy and are not tuned on final holdout.
- [ ] Drift/coverage monitoring and revalidation triggers are defined.
- [ ] A metric card documents intended use, prohibited use, data, methodology, limitations, uncertainty, version, owner, and results.
- [ ] Independent analyst review approves claims before customer-facing release.
- [ ] **TASK COMPLETE — DS-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.7 DS-007 — Measure and govern manual-label quality

**Depends on:** DATA-009 and DS-005.

**Acceptance criteria**

- [ ] Label definitions/examples/exclusions use a versioned guide linked to every labeling batch.
- [ ] A representative calibration/gold set and blind overlapping sample are assigned to multiple reviewers.
- [ ] Inter-rater agreement uses an appropriate statistic with confidence/interpretation and per-label support, not percentage alone.
- [ ] Disagreements have a blinded adjudication process and corrections preserve original decisions/audit.
- [ ] Reviewer/label drift, skip/missing rates, and low-agreement categories are monitored with retraining/redefinition thresholds.
- [ ] Metrics/downstream decisions include label version and exclude or flag unreviewed/low-quality labels according to policy.
- [ ] **TASK COMPLETE — DS-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.8 DS-008 — Document sampling, selection, survivorship, and collection bias

**Depends on:** DATA-012, REL-001, and DS-002.

**Acceptance criteria**

- [ ] Every research dataset records its sampling frame, selection method, date/window, requested versus collected population, and manual inclusion criteria.
- [ ] Private/deleted/unavailable videos, API/transcript failures, quota truncation, and missing fields are retained as exclusion/missingness counts with reasons.
- [ ] Coverage is reported by channel, time, content category, and other relevant strata.
- [ ] Documentation limits generalization beyond the sampled channels/videos and distinguishes convenience from representative samples.
- [ ] Sensitivity or weighting analysis is performed where claims depend on representativeness.
- [ ] Exports/reports carry dataset version, coverage summary, and sampling caveat.
- [ ] **TASK COMPLETE — DS-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 9.9 DS-009 — Add defensible experiment design and analysis

**Depends on:** DS-005, DATA-006, and DATA-015.

**Acceptance criteria**

- [ ] Before launch, each experiment records hypothesis, treatment/control, unit, eligibility, assignment, primary metric, guardrails, minimum detectable effect/power or practical sample rationale, duration, and stopping rule.
- [ ] Assignment/exposure and analysis populations are immutable/auditable; contamination and concurrent experiment policy are defined.
- [ ] Checkpoints cannot silently change the primary metric/hypothesis; amendments are versioned and visibly post hoc.
- [ ] Analysis handles uncertainty, repeated peeking/stopping, missing outcomes, multiple comparisons, and practical significance.
- [ ] Results report null/negative outcomes and limitations, not only wins.
- [ ] Fixtures/simulations validate assignment balance, metric calculation, stopping behavior, and analysis recovery.
- [ ] **TASK COMPLETE — DS-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 10. Phase 8 — WCAG 2.2 AA accessibility and usable interaction

Accessibility completion requires both automated and manual evidence. Automated scanners cannot prove conformance by themselves.

### 10.1 UX-001 — Make every table action operable with native keyboard semantics

**Depends on:** CI-009 and stable data-viewer API.

**Acceptance criteria**

- [ ] Sortable headers contain real buttons with accessible names, visible focus, and correct aria-sort state; bare clickable TH behavior is removed.
- [ ] Row navigation uses real links in a meaningful cell; no essential action depends on a non-focusable onclick row.
- [ ] All table actions work with Tab/Shift+Tab and native Enter/Space behavior without custom timing.
- [ ] Focus order follows visual/reading order and remains visible when sticky headers/navigation are present.
- [ ] Screen readers announce table name/caption, scoped headers, sort state/change, link purpose, and empty/loading/error status.
- [ ] Keyboard-only end-to-end tests cover sorting, pagination, filters, opening a row, returning, and preserving state.
- [ ] Automated and NVDA/VoiceOver evidence has no unresolved WCAG 2.1.1, 2.4.x, or 4.1.2 failures for these tables.
- [ ] **TASK COMPLETE — UX-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.2 UX-003 — Give every form a persistent label and recoverable validation

**Depends on:** REL-014 and CI-009.

**Acceptance criteria**

- [ ] Every input/select/textarea has a visible programmatically associated label; placeholder is never the only accessible name/instruction.
- [ ] Required/optional state, expected format, units, limits, and examples are provided before input and associated with aria-describedby where needed.
- [ ] Server and client validation agree; invalid controls use aria-invalid and link to specific persistent error text.
- [ ] A focusable error summary lists and links to all invalid fields after submit.
- [ ] Safe entered values remain populated after validation error; secrets/passwords follow a deliberate secure re-entry policy.
- [ ] Errors do not rely on color alone and are announced through an appropriate live region without moving focus unexpectedly.
- [ ] Tests cover empty, invalid, boundary, multiple-error, server-only error, expired session/CSRF, and successful resubmission using keyboard and screen reader.
- [ ] **TASK COMPLETE — UX-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.3 UX-002 — Implement complete accessible tab and menu interaction models

**Depends on:** CI-009.

**Acceptance criteria**

- [ ] Each custom control is reviewed to prefer native disclosure/select/button behavior before adopting ARIA tabs/menu patterns.
- [ ] Tabs implement tablist/tab/tabpanel roles, accessible names, aria-selected/controls, one roving tabindex, arrow/Home/End navigation, and defined activation behavior.
- [ ] Inactive panels are removed from focus/assistive navigation while active content remains reachable.
- [ ] Menus/disclosures expose expanded state, move focus appropriately, support Escape/outside close, and return focus to the invoker.
- [ ] Theme/export controls do not misuse menu roles when their content is ordinary navigation/form controls.
- [ ] Focus remains correct across rerender, validation, responsive layout, and page history.
- [ ] Automated keyboard tests plus NVDA/VoiceOver checks pass every state.
- [ ] **TASK COMPLETE — UX-002:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.4 UX-004 — Make auto-updating content controlled, ordered, and non-disruptive

**Depends on:** PERF-003 and CI-009.

**Acceptance criteria**

- [ ] Users can start, pause/stop, and choose or clearly understand refresh frequency; preference persists appropriately.
- [ ] Refresh pauses when page is hidden/offline and resumes without request storms.
- [ ] Requests cannot overlap or apply out of order; retry uses bounded backoff and visible recovery.
- [ ] Updates do not steal focus, reset controls/scroll, or unexpectedly change the user's active context.
- [ ] A concise polite live-region summary announces meaningful status changes; high-frequency row churn is not read verbatim.
- [ ] Manual refresh remains available and shows last successful refresh/freshness.
- [ ] WCAG 2.2.2 and status-message tests cover long-running updates, errors, background tab, reduced motion, and assistive technology.
- [ ] **TASK COMPLETE — UX-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.5 UX-006 — Correct landmarks, skip navigation, headings, and table semantics

**Depends on:** CI-009.

**Acceptance criteria**

- [ ] Every page has exactly one main landmark and a keyboard-visible skip link whose target receives correct focus/scroll.
- [ ] Navigation, header, footer, complementary, and repeated landmarks have appropriate elements and accessible names.
- [ ] Heading hierarchy communicates page/section structure without skipped levels used solely for styling.
- [ ] Tables have captions or equivalent names, TH scope/headers associations, and no layout-table semantics.
- [ ] Repeated page regions and flash/status areas are discoverable without duplicate IDs or invalid nesting.
- [ ] Automated HTML/accessibility validation and manual landmark/heading navigation pass every template.
- [ ] **TASK COMPLETE — UX-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.6 UX-007 — Respect reduced motion and make transient status perceivable

**Depends on:** CI-009.

**Acceptance criteria**

- [ ] prefers-reduced-motion removes or substantially reduces nonessential transition, pulse, spinner, smooth-scroll, and animation behavior.
- [ ] Essential progress remains understandable without motion and does not flash above accessibility thresholds.
- [ ] Actionable errors/warnings persist until dismissed/resolved; success messages remain long enough and are also represented in durable page/job state when needed.
- [ ] Toasts have appropriate live-region role, pause/dismiss behavior, keyboard accessibility, and never contain the only copy of critical information.
- [ ] Loading indicators expose accessible text/state and do not create indefinite ambiguous waiting.
- [ ] Tests cover normal/reduced motion, slow operation, repeated messages, keyboard dismissal, and screen-reader announcements.
- [ ] **TASK COMPLETE — UX-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.7 UX-009 — Harden images and YouTube embeds for accessibility, privacy, and performance

**Depends on:** SEC-004, SEC-007, and PERF-006.

**Acceptance criteria**

- [ ] Informative images have meaningful contextual alt text; decorative images use empty alt and do not duplicate nearby text.
- [ ] Images/iframes define dimensions/aspect ratio and a deliberate eager/lazy priority to prevent layout shift and unnecessary loads.
- [ ] Every iframe has a descriptive title, minimum allow permissions, referrer policy, and sandbox decision documented.
- [ ] YouTube embeds use privacy-enhanced/click-to-load behavior where compatible with product requirements and disclose unavoidable third-party requests.
- [ ] Thumbnail/embed URL and host validation prevents arbitrary untrusted embeds.
- [ ] Keyboard, screen-reader, blocked-third-party, consent/privacy, slow-network, and missing-image tests pass.
- [ ] **TASK COMPLETE — UX-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.8 UX-005 — Replace flat/overflowing navigation with tested task-based information architecture

**Depends on:** CI-009 and an approved task-based information-architecture decision; coordinate canonical route vocabulary with PROD-001.

**Acceptance criteria**

- [ ] Target-user task inventory and card-sort/navigation testing justify top-level groups and labels.
- [ ] Desktop navigation fits supported tablet/desktop widths without clipping/overlap; mobile uses a discoverable accessible menu rather than hidden horizontal overflow.
- [ ] Current page/group is conveyed programmatically with aria-current and visually by more than color.
- [ ] Menu open/close, focus trap/return where appropriate, Escape, outside click, resize, route change, and back/forward behavior are tested.
- [ ] Footer does not duplicate an overwhelming peer list and provides only justified secondary navigation.
- [ ] Every current route remains reachable, has one canonical location, and obsolete links redirect safely.
- [ ] Usability testing shows target users can find collect, analysis, labeling, rights, analytics, jobs, exports, and settings without instruction.
- [ ] **TASK COMPLETE — UX-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.9 UX-008 — Make dense tables usable and responsive

**Depends on:** UX-001, UX-005, PERF-003, and PERF-005.

**Acceptance criteria**

- [ ] User research identifies primary columns/actions per table and lower-priority detail is progressively disclosed or configurable.
- [ ] Core content reflows at 320 CSS pixels/400% zoom without two-dimensional page scrolling; a data table may scroll in its own labeled region where necessary.
- [ ] Horizontal table scroll preserves header/row context, visible focus, sticky offsets, and keyboard access.
- [ ] Mobile representation retains data relationships, sorting/filtering, and primary actions without hiding essential content.
- [ ] Column choice/density/filter state is accessible, saved appropriately, and resettable.
- [ ] Empty, loading, error, long text, large numbers, RTL/localized text, and maximum-column cases are tested.
- [ ] **TASK COMPLETE — UX-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 10.10 UX-010 — Prove WCAG 2.2 AA across supported states

**Depends on:** UX-001 through UX-009 and CI-009.

**Acceptance criteria**

- [ ] A page/state inventory covers anonymous/authenticated roles, light/dark, desktop/mobile/tablet, empty/loading/error/success, dialogs/menus/tabs, and all core journeys.
- [ ] Automated axe/HTML/contrast checks have no unresolved serious/critical issues and all findings are manually reviewed.
- [ ] Keyboard-only testing covers all functionality, focus order/visibility/not obscured, no traps, skip links, and session/time behavior.
- [ ] NVDA with Firefox/Chrome and VoiceOver with Safari or an approved current support matrix complete critical journeys.
- [ ] Tests at 200% and 400% zoom, 320 CSS pixel reflow, text spacing override, forced colors/high contrast, reduced motion, and orientation pass.
- [ ] Contrast, target size, labels/instructions, error prevention, status messages, and accessible name/role/value meet WCAG 2.2 AA.
- [ ] An accessibility conformance report records scope, versions, tools, manual results, exceptions, owners, and retest date; no unsupported blanket conformance claim is made.
- [ ] A qualified independent reviewer verifies release-critical results.
- [ ] **TASK COMPLETE — UX-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 11. Phase 9 — Coherent customer product and governed workflows

### 11.1 PROD-001 — Unify duplicate collection routes into one customer mental model

**Depends on:** REL-004 and PROD-002; coordinate navigation presentation with UX-005 without making either task depend circularly on the other.

**Acceptance criteria**

- [ ] One canonical Collect workspace supports channel/video modes with shared validation, job status, history, and next steps.
- [ ] Legacy /, /channel, /collect, and process/save paths are mapped to canonical routes with safe method-preserving behavior or versioned deprecation.
- [ ] No workflow returns users to a contradictory legacy interface after completion.
- [ ] Product terms describe user tasks rather than internal implementation phases.
- [ ] Analytics, documentation, navigation, deep links, bookmarks, and tests use canonical routes.
- [ ] Usability testing shows new users can collect one video/channel, understand status, and reach its research record without assistance.
- [ ] **TASK COMPLETE — PROD-001:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.2 PROD-003 — Make every eligible historical record searchable and selectable

**Depends on:** PERF-005 and UX-003.

**Acceptance criteria**

- [ ] Rights, owned analytics, experiments, and related forms use authorized server-side search/autocomplete rather than latest-100 lists.
- [ ] Search supports provider ID, title/channel, and appropriate filters with stable pagination and bounded results.
- [ ] Users can open a workflow with a deep-linked selected record even when it is old.
- [ ] Results show enough disambiguating context and never expose unauthorized private records.
- [ ] Empty/no-match, stale/deleted, duplicate-title, keyboard, screen-reader, slow-network, and thousands-of-records cases pass.
- [ ] Unbounded opposite cases such as all videos/theses are paginated consistently.
- [ ] **TASK COMPLETE — PROD-003:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.3 PROD-004 — Break monolithic forms into recoverable drafts and reviewable steps

**Depends on:** UX-003, DATA-009, and SEC-013.

**Acceptance criteria**

- [ ] User research/task analysis defines logical sections/steps and the minimum data needed at each stage.
- [ ] Users can save an explicit draft, resume safely across sessions/devices according to policy, and see completion/validation state.
- [ ] Autosave, if used, is versioned, visibly confirmed, conflict-safe, and never stores incomplete secrets unexpectedly.
- [ ] Final submission includes a review summary and validates server-side atomically.
- [ ] Navigation away/timeout/session expiry preserves or warns about unsaved work and provides recovery.
- [ ] Error correction retains values and returns focus to actionable errors without losing completed sections.
- [ ] Tests cover long form, partial draft, concurrent edit, stale schema/version, network failure, invalid step, cancel/discard, and successful finalization.
- [ ] **TASK COMPLETE — PROD-004:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.4 PROD-005 — Add governed correction, supersession, archive, and deletion workflows

**Depends on:** DATA-009 and audit/authorization foundation.

**Acceptance criteria**

- [ ] Each entity has a documented policy for editable correction, append-only supersession, archive, soft delete, hard delete, retention, and legal/audit preservation.
- [ ] Users never need direct database editing for supported correction workflows.
- [ ] Corrections require appropriate role, reason, optimistic version, before/after audit, and downstream invalidation/recompute.
- [ ] Deleted/archived records disappear from active decisions but remain/restorable only according to authorization and retention policy.
- [ ] Referential effects are explicit; no orphan, silent cascade, or stale ready/metric state remains.
- [ ] Tests cover unauthorized correction, stale conflict, restore, dependent records, export/history representation, and privacy deletion.
- [ ] **TASK COMPLETE — PROD-005:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.5 PROD-006 — Enforce a thesis state machine and decision-governance gates

**Depends on:** DS-004, DS-005, DS-007, DATA-013, and DATA-009.

**Acceptance criteria**

- [ ] Thesis states and permitted transitions are explicit, versioned, and enforced in one server-side state machine.
- [ ] Each transition defines authorized roles, required evidence/scores/monetization/rights/red-team review/approvals, and reversal rules.
- [ ] Launch-ready cannot be reached through direct form tampering, missing evidence, stale rights, insufficient data, or invalid metric run.
- [ ] Transition creates an immutable audit event with actor, prior/new state, evidence versions, reason, and correlation ID.
- [ ] Concurrent transitions use optimistic locking and return a resolvable conflict.
- [ ] UI explains unmet gates and never presents an aspirational state as approval.
- [ ] Transition-matrix tests cover every allowed and forbidden role/state/evidence combination.
- [ ] **TASK COMPLETE — PROD-006:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.6 PROD-007 — Make credential, ownership, and OAuth capability claims accurate

**Depends on:** DATA-014 and DATA-015.

**Acceptance criteria**

- [ ] UI distinguishes configured metadata, connection tested, authenticated, ownership verified, sync healthy, disabled, revocation pending, and externally revoked.
- [ ] Setup verifies requested scopes, identity/channel ownership, secret-backend reference, provider connectivity, and least privilege without revealing tokens.
- [ ] Last successful/failed sync, error category, consent/scopes, and next action are visible to authorized users.
- [ ] Features that are not implemented are labeled unavailable/planned and cannot create misleading success records.
- [ ] Documentation and exports use the same state terminology.
- [ ] End-to-end staging tests prove connect, ownership verification, sync, scope failure, expiry, reauthorization, disable, and real revoke.
- [ ] **TASK COMPLETE — PROD-007:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.7 PROD-008 — Provide onboarding, global findability, freshness, and contextual guidance

**Depends on:** PROD-001, PROD-002, PROD-003, and validated metric terminology.

**Acceptance criteria**

- [ ] First-run onboarding checks auth, API, database, worker/queue, and required configuration without exposing technical secrets.
- [ ] A guided path leads from empty workspace to first successful collection, reviewed research insight, and appropriate next action.
- [ ] Empty states explain purpose, prerequisites, sample/demo option, action, and where data will come from.
- [ ] Authorized global search or command interface finds channels, videos, theses, jobs, experiments, and relevant settings with clear scope.
- [ ] Decision pages display source, collection freshness, metric version/window, ownership/public status, and definition/caveat links.
- [ ] Onboarding is dismissible/resumable, does not trap experienced users, and is keyboard/screen-reader accessible.
- [ ] Usability tests measure time to first value, errors, abandonment, comprehension, and successful recovery.
- [ ] **TASK COMPLETE — PROD-008:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.8 PROD-009 — Define and implement locale, number, date, and timezone behavior

**Depends on:** DATA-008 and UX-008.

**Acceptance criteria**

- [ ] Supported locale/language and display timezone policy is documented; English-only is explicitly stated if that is the approved scope.
- [ ] User-visible dates/times, durations, integers, decimals, percentages, and currency use locale-aware formatting with unambiguous timezone where relevant.
- [ ] Storage/API remains locale-neutral and parsing does not confuse comma/period separators or localized digits.
- [ ] Text/layout supports long translated strings and RTL direction where a supported language requires it.
- [ ] Sorting/filtering operates on canonical values rather than formatted strings.
- [ ] Tests cover English, an RTL/Arabic representative locale if in scope, Asia/Baghdad, UTC, large numbers, decimals, currency, and DST-zone display.
- [ ] **TASK COMPLETE — PROD-009:** All task criteria and the Global Definition of Done are satisfied and evidenced.

### 11.9 PROD-010 — Measure product quality without invasive tracking

**Depends on:** SEC-016 and defined customer journeys.

**Acceptance criteria**

- [ ] Core journey outcomes define activation, successful collection, insight reviewed, workflow completion, error/recovery, time saved proxy, and retention.
- [ ] Event taxonomy has purpose, owner, schema/version, consent/privacy basis, retention, and excludes secret/private content by default.
- [ ] Metrics distinguish technical completion from meaningful user outcome and are segmented only when privacy/sample size allows.
- [ ] Funnel/error/abandonment dashboards and qualitative support/usability feedback produce actionable review cadence.
- [ ] Customer interviews/usability tests include target users and document findings, severity, decision, and follow-up.
- [ ] Tracking opt-out/deletion/access and telemetry failure do not block core product use where policy requires.
- [ ] A beta exit decision uses predefined evidence rather than vanity usage counts.
- [ ] **TASK COMPLETE — PROD-010:** All task criteria and the Global Definition of Done are satisfied and evidenced.

## 12. Cross-cutting production release gates

These gates cover the audit's cross-cutting observability, recovery, privacy, operational, and customer-readiness improvements. Complete them after all 100 finding tasks are complete.

### 12.1 Security release gate

- [ ] OWASP ASVS 5.0 Level 2 requirements are mapped to implementation/test evidence; every exception has owner, compensating control, approval, and expiry.
- [ ] Independent penetration test covers authenticated roles, IDOR, CSRF, session, stored/reflected injection, exports, queue/Socket.IO, Redis/network, and configuration; Critical/High results are closed and retested.
- [ ] Threat model and data-flow diagram include browser, ingress, web, queue, workers, scheduler, database, secret store, telemetry, providers, exports, and customer/tenant boundaries.
- [ ] Secret, dependency, container, SAST, DAST, IaC, workflow, and license gates are green on the exact release artifact.
- [ ] Security incident response, credential rotation, session invalidation, forensic logging, disclosure, and customer notification procedures are exercised.
- [ ] **SECURITY RELEASE GATE COMPLETE.**

### 12.2 Data and recovery release gate

- [ ] PostgreSQL head, schema drift, constraints, indexes, row-count equations, duplicates, FK integrity, count ranges, finite numerics, and timezone invariants are clean.
- [ ] Every supported historical database upgrades to head through CI and a production-like rehearsal.
- [ ] Backup restore meets documented recovery point and recovery time objectives with checksum/invariant verification.
- [ ] A reconciliation report proves no known overflow/rollback/false-success run remains silently trusted.
- [ ] Metric/export/source lineage can reproduce a sampled result from collection input through output.
- [ ] Retention, deletion, archive, correction, and privacy-request procedures are tested.
- [ ] **DATA AND RECOVERY RELEASE GATE COMPLETE.**

### 12.3 Reliability and operations release gate

- [ ] Defined SLO dashboards and alerts cover latency, traffic, errors, saturation, queue age/runtime, dependency health, quota, freshness, and collection completeness.
- [ ] Load/spike/soak tests meet capacity headroom with no data/accounting/authorization errors.
- [ ] Dependency restart, network partition, worker kill, scheduler failover, deployment drain, credential rotation, retry storm, cancellation, and disk/memory pressure game days pass.
- [ ] Every alert has an owner and tested runbook; on-call/escalation and incident roles are documented.
- [ ] Release/rollback is reproducible from attested artifacts and rollback does not require an unsafe schema downgrade.
- [ ] Redis persistence/memory policy, PostgreSQL backup/PITR where required, temp/export cleanup, and disk monitoring are verified.
- [ ] **RELIABILITY AND OPERATIONS RELEASE GATE COMPLETE.**

### 12.4 Accessibility and product release gate

- [ ] Independent WCAG 2.2 AA review and assistive-technology testing has no unresolved release-blocking issue.
- [ ] Critical journeys pass on supported browsers, mobile/tablet/desktop, keyboard, screen reader, 200%/400% zoom, reflow, reduced motion, and dark/light themes.
- [ ] Five to ten target design partners complete first-value and recurring workflows; observed problems are triaged and release blockers closed.
- [ ] Beta metrics meet predefined activation, successful job, retention, support/error, trust/correction, and time-to-value thresholds.
- [ ] Privacy notice, terms/provider-policy review, data export/deletion, support, status/incident communication, and customer onboarding are ready.
- [ ] Product claims match validated capabilities and analytics evidence; no unsupported opportunity/enterprise/security/accessibility claim remains.
- [ ] **ACCESSIBILITY AND PRODUCT RELEASE GATE COMPLETE.**

### 12.5 Final production decision

- [ ] Every one of the 100 **TASK COMPLETE** checkboxes in this document is checked with a completion record.
- [ ] Every Phase 0 and cross-cutting release-gate checkbox is checked with evidence.
- [ ] No open Critical or High security, data-integrity, availability, accessibility, privacy, dependency, or migration finding exists.
- [ ] Medium/Low residual risks have owner, priority, target date, monitoring/compensating control, and explicit release approval.
- [ ] The exact release commit/image/database head/configuration has passed the full production acceptance suite.
- [ ] Authorized engineering, security, data, product, and operations reviewers approve the release.
- [ ] **FINAL PRODUCTION-READINESS DECISION: APPROVED.**

## 13. Codex task prompt template

Use the following prompt for each task. Replace TASK-ID with the next unchecked task in this file.

    Work only on TASK-ID in
    docs/production-readiness-remediation-execution-checklist-2026-07-15.md.

    First read the source audit finding, the task dependencies, all task-specific
    acceptance criteria, and the Global Definition of Done. Confirm dependencies
    are complete. Inspect the current implementation and reproduce the baseline
    before editing.

    Create a narrow implementation plan. Implement the root-cause fix, migrations,
    automated positive/negative/boundary/concurrency tests, observability, rollback
    or recovery instructions, and documentation required by the checklist.

    Do not change unrelated behavior, do not expose secrets/private data, do not
    mutate real persistent data or external systems without my explicit approval,
    and do not weaken tests.

    Run focused verification and the full applicable repository suite. Review the
    final diff as a senior software, security, database, reliability, accessibility,
    and product engineer as applicable.

    Then update only this task's checklist and completion record. Check a box only
    when you have direct evidence. Leave manual/external criteria unchecked and
    record the blocker if you cannot verify them. Check TASK COMPLETE only when
    every task criterion and every applicable Global Definition of Done item is
    evidenced. Stop after TASK-ID and report the next task, but do not start it.

## 14. Codex completion-report format

After each task, Codex's response should contain:

1. **Outcome:** What behavior changed.
2. **Root cause:** Why the prior behavior failed.
3. **Files and migration:** Exact files and revision.
4. **Acceptance criteria:** Passed, failed, blocked, or N/A with evidence for each.
5. **Tests:** Exact commands, pass/fail/skip/warning counts, and important fault cases.
6. **Security/data review:** Authorization, privacy, secrets, transaction, migration, and rollback effects.
7. **Residual risk:** Anything not proven.
8. **Tracker update:** Which boxes were checked and why.
9. **Next task:** The next dependency-satisfied unchecked task; do not implement it automatically.

## 15. Audit coverage and anti-confusion rules

- The source audit is descriptive evidence; this document is the execution/status source of truth.
- Do not mark findings complete in the source audit.
- Do not add a duplicate task for a discovered subproblem. Add the subproblem as an unchecked criterion under the owning task, or add a new uniquely named finding with rationale and dependency.
- If a completed task regresses, uncheck its **TASK COMPLETE** box, mark it reopened in the completion record, and identify downstream tasks/release gates that must be revalidated.
- A passing full suite does not override a failed task-specific/manual criterion.
- A task is not complete when its code is merged but its migration, deployment, repair, external test, or documentation is unfinished.
- Preserve evidence in version-controlled safe reports or approved CI/artifact systems; never paste secrets or private data into this ledger.

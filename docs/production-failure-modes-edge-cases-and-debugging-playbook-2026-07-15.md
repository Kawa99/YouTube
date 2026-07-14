# Production Failure Modes, Edge Cases, and Debugging Playbook

- **System:** YouTube Research Engine
- **Repository:** /home/kawa/YouTube
- **Created:** 2026-07-15
- **Companion audit:** [Comprehensive Engineering, Product, Security, Data, Networking, and Debugging Audit](comprehensive-engineering-product-security-audit-2026-07-14.md)
- **Execution tracker:** [Production-Readiness Remediation Execution Checklist](production-readiness-remediation-execution-checklist-2026-07-15.md)
- **Purpose:** Anticipate how the web application, its data, its users, and its remediation work can fail; define what to observe, contain, debug, and verify before customer exposure.

## 1. Scope, honesty, and how to use this playbook

This is a production pre-mortem and debugger's field guide. It is deliberately pessimistic. It asks what can fail when configuration is missing, data is extreme, users behave unexpectedly, dependencies become slow, processes race, migrations stop halfway, attackers abuse trust boundaries, algorithms are misinterpreted, and apparently successful fixes are incomplete.

No finite document can literally enumerate every possible failure. The goal is to cover the credible, high-impact, and easily missed classes for this repository, then provide invariants and investigation methods that generalize to failures not named here.

### 1.1 Evidence labels

Every risk should be interpreted using one of these labels:

- **CONFIRMED:** Reproduced in code, runtime, database, logs, tests, or configuration during the 2026-07-14 audit.
- **STRUCTURALLY PRESENT:** The implementation directly permits the failure, although exploitation/production occurrence was not demonstrated.
- **PLAUSIBLE:** A credible edge case inferred from the architecture; it requires a focused reproduction test.
- **CHANGE-INTRODUCED:** A regression that may be created while fixing another issue.
- **EXTERNAL:** Primarily caused by YouTube, transcript providers, DNS, network, browser, identity provider, secret backend, or infrastructure outside this repository.

Do not tell a customer that a plausible risk is a confirmed incident. Do not dismiss a confirmed defect because it has not yet caused a visible customer complaint.

### 1.2 Relationship to the other documents

- The **audit** explains what is currently below standard and why.
- The **execution tracker** decides remediation order and completion criteria.
- This **playbook** explains what may go wrong before, during, and after remediation; how failure propagates; how to recognize it; and how the system must behave under stress.

Before implementing a tracker task, search this playbook for its domain and failure IDs. Add the relevant negative, boundary, concurrency, recovery, accessibility, and fault-injection tests to the task plan. After implementation, retain evidence that the named failure no longer violates the required behavior.

### 1.3 Public standard baseline

This document does not claim access to confidential Google, Amazon, Meta, or other company checklists. It uses their public engineering guidance and current open standards:

- [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/) for application security verification.
- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final) for secure development and supply-chain discipline.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) Level AA for accessible interaction.
- [Google SRE effective troubleshooting](https://sre.google/sre-book/effective-troubleshooting/) for triage, hypothesis-driven debugging, evidence preservation, correlation, and postmortems.
- [Google SRE addressing cascading failures](https://sre.google/sre-book/addressing-cascading-failures/) for overload, retries, load shedding, health separation, and failure testing.
- [Amazon Builders' Library guidance on retries, timeouts, and jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) for bounded distributed calls.
- PostgreSQL, Redis, Flask, Flask-SocketIO, Docker, and GitHub official operational/security guidance cited in the companion audit.

## 2. Risk model and stop-the-bleeding rule

### 2.1 Severity

| Severity | Meaning | Default response |
|---|---|---|
| **SEV-0 / Critical** | Active or imminent unauthorized access, unrecoverable data corruption/loss, arbitrary code path, secret compromise, or results that cannot be trusted | Restrict/freeze affected capability immediately; preserve evidence; invoke incident process |
| **SEV-1 / High** | Major confidentiality, integrity, availability, accessibility, financial, or customer harm with no reliable workaround | Stop rollout; contain; assign incident owner; restore safe service |
| **SEV-2 / Medium** | Material degradation, misleading output, partial workflow failure, or scale risk with a bounded workaround | Mitigate, monitor, and repair on a committed schedule |
| **SEV-3 / Low** | Localized polish, maintainability, or low-frequency defect with small immediate impact | Track and fix without displacing higher risks |

### 2.2 Debugging priority

During an incident:

1. Protect people, customer data, credentials, and durable data.
2. Stop propagation: disable the failing feature, pause jobs, reject unsafe writes, shed optional load, or restrict ingress.
3. Preserve evidence: time, release/config change, correlation IDs, job/run IDs, database state, safe logs, and metrics.
4. Restore the safest useful service; degraded read-only behavior is preferable to corrupt writes.
5. Form falsifiable hypotheses and change one variable at a time.
6. Prove the cause in a safe environment when production reproduction would add harm.
7. Repair the root cause, add regression/fault tests, reconcile affected data, and write a blameless postmortem.

Never continue corrupting data merely to keep a green health indicator. Never restart every component simultaneously before capturing state. Never apply an untested production hotfix because the first symptom looks familiar.

## 3. Architecture and failure-propagation map

    Customer browser
      |
      | DNS, TLS, reverse proxy, cookies, CSRF, CSP, third-party assets
      v
    Flask / Gunicorn / Socket.IO web
      |                 |
      |                 +--> Google Fonts / JS CDNs / YouTube embed
      |
      +--> PostgreSQL <---------- migrations / backup / restore
      |
      +--> Redis / RQ / PubSub
                 |        |
                 |        +--> scheduler
                 |
                 +--> workers
                        |
                        +--> YouTube Data API
                        +--> transcript endpoints/providers
                        +--> telemetry / secret backend

A small fault can propagate across this map:

- Browser polling can overload web, which exhausts database connections, which makes readiness fail, which causes restarts, which increases cold-start traffic.
- A YouTube outage can trigger nested retries, exhaust quota, occupy the only worker, delay exports, and make every job appear stuck.
- A Redis compromise can alter queue jobs, reach a root worker, and then reach shared database credentials.
- A migration mismatch can break health, induce restart loops, and prevent operators from seeing diagnostics.
- An analytics definition error can be technically available and fast while producing confident but invalid customer decisions.

## 4. Non-negotiable system invariants

If any invariant fails, the affected capability is not production-ready.

1. **Identity invariant:** Missing/broken identity configuration denies access or prevents production startup; it never opens the application.
2. **Authorization invariant:** Authentication alone never grants all data/actions; every protected object and job is authorized server-side.
3. **Safe-method invariant:** GET/HEAD do not mutate durable state or enqueue work.
4. **Durability invariant:** A reported saved/completed count equals committed database state.
5. **Failure-truth invariant:** Timeout, quota, auth, malformed response, and dependency outage never become valid empty data.
6. **Idempotency invariant:** Repeated equivalent requests do not create duplicate logical work or durable effects.
7. **Boundedness invariant:** Every request, query, payload, retry, job, queue, export, log, and external call has a justified limit/deadline.
8. **Single-source invariant:** Every semantic fact has one authoritative representation or a verified invariant tying replicas.
9. **Migration invariant:** Every supported stored schema has a non-destructive, rehearsed path to the current schema.
10. **Lineage invariant:** A customer-facing result identifies its source collection, algorithm/configuration version, time window, and missingness.
11. **Privacy invariant:** Public research, private owned analytics, credentials, logs, and exports cannot cross boundaries without explicit authorization.
12. **Accessibility invariant:** Essential functionality remains operable, perceivable, and understandable without a mouse or visual-only cues.
13. **Recovery invariant:** A failed deployment/dependency/job can recover without inventing success, duplicating effects, or requiring unsafe database edits.
14. **Observability invariant:** Operators can correlate browser request, HTTP handler, job, collection run, provider call, database commit, and output without logging secrets.
15. **Release invariant:** The exact artifact/configuration/schema tested is the one deployed, and the release can be halted/rolled back safely.

## 5. Catastrophic and high-impact failure chains

### FC-01 — Configuration omission opens all protected data

- **Evidence:** CONFIRMED in the inspected runtime.
- **Trigger:** ADMIN_PASSWORD/identity variables are absent, misspelled, unavailable at boot, or removed during rotation.
- **Failure chain:** Security initialization interprets missing configuration as authentication disabled; the all-interface web listener continues serving; private analytics, settings, exports, jobs, rights records, and mutations become reachable.
- **Symptoms:** Login redirects to dashboard; anonymous requests return 200; no auth failure metrics; customers may see no obvious warning.
- **Impact:** Full confidentiality/integrity breach and untraceable modification.
- **Bad behavior:** Start successfully and fail open.
- **Required behavior:** Production startup fails nonzero or every non-public request denies access. A safe readiness error names the missing configuration without exposing secrets.
- **Immediate containment:** Remove public/private-network reachability, stop the web service if necessary, preserve access logs, rotate affected credentials/sessions, and assess data/export access.
- **Detection and proof:** Deployment test removes each identity setting; startup must fail. An anonymous route matrix and Socket.IO room test must produce only intended public responses.

### FC-02 — Weak signing secret makes authenticated sessions untrustworthy

- **Evidence:** CONFIRMED four-character inspected secret plus source fallbacks.
- **Trigger:** Weak/default secret remains after authentication is enabled or leaks through code/chat/logs.
- **Failure chain:** Attacker guesses/obtains signing key, forges session state, reaches privileged routes, and actions appear to come from an authenticated user.
- **Symptoms:** Privileged requests without a legitimate login trail; impossible user/session combinations; session cookies validate across environments.
- **Impact:** Authentication bypass, data theft/mutation, audit repudiation.
- **Required behavior:** Production rejects known/default/low-entropy secrets, uses managed random keys, rotates/invalidate sessions, and scopes keys per environment.
- **Immediate containment:** Restrict ingress, rotate key, invalidate all sessions, rotate exposed adjacent credentials, audit privileged events.
- **Detection and proof:** Entropy/default startup tests, old-cookie-after-rotation test, cross-environment cookie rejection, secret-history scan.

### FC-03 — Count overflow erases prior rows but reports them saved

- **Evidence:** CONFIRMED by code path and PostgreSQL integer-overflow logs.
- **Trigger:** A YouTube count exceeds 2,147,483,647 or another mid-batch flush fails.
- **Failure chain:** Earlier rows flush; failing row triggers nested rollback of the caller's transaction; pending result objects remain in memory; outer commit succeeds on an empty transaction; counters count rolled-back rows.
- **Symptoms:** Job says inserted/saved but rows/snapshots are absent; one failed item explains fewer missing rows than reality; count max approaches INTEGER boundary.
- **Impact:** Silent data loss and research outputs that cannot be trusted.
- **Required behavior:** BIGINT for external counts, one explicit transaction owner, savepoints/atomic chunks, and accounting from durable commit outcomes.
- **Immediate containment:** Pause affected collection, preserve run/job/log evidence, query discrepancies, back up, repair code, then recollect/reconcile.
- **Detection and proof:** Mixed-batch boundary test with 2,147,483,648 and a later constraint failure; database durable row count must exactly match reported items_saved.

### FC-04 — Provider outage becomes successful zero data

- **Evidence:** CONFIRMED structurally in YouTube error-to-empty conversion and zero-result completion.
- **Trigger:** Invalid API key, 403 quota, 429, DNS/timeout, 5xx, connection reset, or malformed JSON.
- **Failure chain:** Typed error becomes empty dictionary; caller sees no IDs; collection is marked completed-empty; analytics treat missing channel as a real zero-result sample.
- **Symptoms:** Sudden wave of completed runs with zero items, no matching provider-success evidence, quota/auth errors only in low-level logs.
- **Impact:** Silent research incompleteness, misleading trends, no retry/alert.
- **Required behavior:** Successful-empty is distinct from retryable/permanent/auth/quota failure end to end.
- **Immediate containment:** Pause downstream recomputation/publication, classify affected runs, restore credentials/quota/network, recollect, and invalidate derived outputs.
- **Detection and proof:** Contract tests for every status/transport/parse failure and an alert for completed-empty rate deviation.

### FC-05 — Retry amplification creates a cascading outage

- **Evidence:** STRUCTURALLY PRESENT through nested HTTP/client retries and browser/job polling.
- **Trigger:** YouTube/Redis/PostgreSQL becomes slow or returns retryable errors.
- **Failure chain:** Each logical call causes multiplicative physical attempts; workers remain occupied; queue age grows; UI polling adds web/DB traffic; health slows; processes restart; cold workers retry again.
- **Symptoms:** Provider request count exceeds logical calls, synchronized latency spikes, queue oldest age rises, CPU/threads/connections saturate, repeated health failures.
- **Impact:** Quota/cost exhaustion and total service outage from a partial dependency failure.
- **Required behavior:** One retry owner, total deadline/attempt budget, idempotency classification, exponential backoff with jitter, load shedding, and circuit breaking.
- **Immediate containment:** Disable optional jobs/transcripts/auto-refresh, cap or stop retries, shed new work, restore dependency capacity, keep liveness separate from readiness.
- **Detection and proof:** Fault test holds dependency at 500/timeout; physical attempts and total duration must stay within exact bounds while unrelated health/read traffic remains available.

### FC-06 — Duplicate jobs corrupt time series and waste quota

- **Evidence:** STRUCTURALLY PRESENT.
- **Trigger:** Double click, browser retry, scheduler overlap, two schedulers, worker retry after ambiguous acknowledgement, or two users collect the same channel.
- **Failure chain:** Equivalent jobs enter queue; concurrent upserts race; channel/video snapshots duplicate; quota is spent twice; progress/status disagrees.
- **Symptoms:** Same channel/parameters active twice, near-identical snapshots, unique violations, quota spikes, conflicting job totals.
- **Impact:** Incorrect trends, extra cost, lock contention, confusing UX.
- **Required behavior:** Atomic idempotency key, active-job dedupe, fencing lock, explicit force/replay, and database natural uniqueness.
- **Immediate containment:** Stop duplicate dispatch, cancel safe duplicate, select authoritative run, reconcile snapshots/quota, inspect scheduler leadership.
- **Detection and proof:** Two-process barrier test and repeated request test must return one logical job and one intended durable effect.

### FC-07 — Redis foothold becomes queue manipulation or worker code execution

- **Evidence:** CONFIRMED insecure Redis configuration; code-execution outcome is STRUCTURALLY PRESENT through trusted job serialization.
- **Trigger:** Compromised web container, accidental port publish, neighbor network access, SSRF, leaked Redis URL, or future debug tool.
- **Failure chain:** Unauthenticated unrestricted Redis access permits queue/key changes; malicious/forged job reaches a privileged root worker; shared DB/secrets increase blast radius.
- **Symptoms:** Unknown jobs, altered job payloads, queue deletion, unexpected worker imports/commands, Redis CONFIG/FLUSH activity.
- **Impact:** Data loss, denial of service, credential theft, potential remote code execution.
- **Required behavior:** Network isolation, ACL identities, dangerous-command denial, safe/authorized serialization, non-root workers, least secrets.
- **Immediate containment:** Isolate Redis/network, stop workers before consuming suspect jobs, snapshot evidence safely, rotate Redis/service/database credentials, rebuild trusted images.
- **Detection and proof:** Anonymous/least-role ACL tests, forged payload rejection, audit alert for forbidden commands, compromised-web simulation unable to enqueue arbitrary work.

### FC-08 — Unsupported Socket.IO topology loses or leaks job events

- **Evidence:** CONFIRMED deployment mismatch; event failure/leak is PLAUSIBLE until load-tested.
- **Trigger:** Poll/upgrade/reconnect requests land on different Gunicorn workers or a user guesses another job room.
- **Failure chain:** Transport session state and room membership diverge; wildcard origins/unauthorized room join broaden access; UI stalls or receives wrong events.
- **Symptoms:** Unknown session, failed upgrade, intermittent missing/duplicate progress, polling fallback loops, cross-job event reports.
- **Impact:** Misleading job state, information disclosure, increased load.
- **Required behavior:** Supported one-worker-per-instance topology with sticky load balancing/message queue, origin allowlist, and object-level room authorization; durable job API remains source of truth.
- **Immediate containment:** Disable Socket.IO updates, fall back to bounded authorized polling/SSE, protect rooms, reduce worker topology to supported configuration.
- **Detection and proof:** Multi-instance reconnect/upgrade/authorization load test with zero cross-user events and deterministic recovery.

### FC-09 — Health checks amplify a dependency incident into restart loops

- **Evidence:** CONFIRMED health coupling/stale-schema 500; cascade is PLAUSIBLE.
- **Trigger:** PostgreSQL/Redis is slow/down, schema is stale, or CPU is saturated.
- **Failure chain:** Deep health query times out/fails; orchestrator kills otherwise alive web processes; restarts create connection storms/cold state; remaining capacity collapses.
- **Symptoms:** High restart count, readiness/liveness fail together, connections spike after every restart, no stable operator endpoint.
- **Impact:** Full outage that outlasts the original dependency fault.
- **Required behavior:** Dependency-free liveness, bounded readiness, startup probe, graceful not-ready state, restart thresholds, and protected diagnostics.
- **Immediate containment:** Stop automatic liveness-driven restarts, reduce incoming/optional load, restore dependency, then roll instances gradually.
- **Detection and proof:** Kill/slow each dependency under load; liveness stays correct, readiness changes predictably, and processes do not storm.

### FC-10 — Migration succeeds partially or targets the wrong database

- **Evidence:** CONFIRMED broken legacy path and schema drift; wrong-target/partial cases are CHANGE-INTRODUCED risks.
- **Trigger:** Ambiguous DATABASE_URL, unversioned legacy DB, migration interruption, multiple app instances running DDL, or an edited applied migration.
- **Failure chain:** Some schema/data changes apply; version state lies or remains absent; app starts against incompatible shape; retries encounter table-exists or duplicate transform; data is lost/duplicated.
- **Symptoms:** Alembic head disagrees with columns/indexes, table already exists, health/dashboard 500, different environments have different schemas.
- **Impact:** Outage, data corruption, unrecoverable deployment, misleading test parity.
- **Required behavior:** Explicit target confirmation, backup/restore proof, one migration runner, schema fingerprint, incremental fixture tests, invariant validation, and recovery plan.
- **Immediate containment:** Stop all writers/deploys, snapshot DB and migration state, do not stamp blindly, reproduce on copy, choose roll-forward/recovery with DBA review.
- **Detection and proof:** Fresh and every supported historical PostgreSQL fixture upgrade to head, drift check clean, interruption injected at risky stages, row/invariant comparison.

### FC-11 — Export exhausts resources or executes attacker-controlled formulas

- **Evidence:** CONFIRMED unsafe sink and synchronous materialization.
- **Trigger:** Large dataset, concurrent exports, malicious title/note beginning with formula marker, temp disk pressure, or client disconnect.
- **Failure chain:** Web process holds rows and serialized copies; ZIP/temp file consumes memory/disk; worker times out; partial file remains; spreadsheet later evaluates formula.
- **Symptoms:** RSS/disk spike, 30-second kill, orphan files, malformed download, external spreadsheet requests/prompts.
- **Impact:** Availability failure, local-client compromise/data exfiltration, privacy breach.
- **Required behavior:** Background chunked export, limits, formula neutralization, atomic output, expiry/authorization, finally/reaper cleanup, versioned manifest.
- **Immediate containment:** Disable large export, remove/expire suspect outputs, inspect temp disk, warn recipients of unsafe files, patch sanitizer before regeneration.
- **Detection and proof:** Maximum-size concurrent load test plus formula corpus round-trip in supported spreadsheet clients/parsers.

### FC-12 — A technically correct metric causes a wrong business decision

- **Evidence:** CONFIRMED methodology weaknesses; customer harm is PLAUSIBLE.
- **Trigger:** Lifetime views compare unequal ages, missing becomes zero, sample contains one video, versions mix, or under-served label is treated causally.
- **Failure chain:** Metric produces precise score without coverage/uncertainty; UI ranks it; user selects niche/content/monetization strategy; outcome underperforms and cannot be reproduced.
- **Symptoms:** Dramatic ranks driven by young/old/missing cases, duplicate metric rows, strong claims with tiny sample, version-dependent changes.
- **Impact:** Lost time/money and erosion of customer trust despite no software exception.
- **Required behavior:** Versioned metric specification/run, age-matched windows, missingness, minimum sample, uncertainty, honest terminology, backtest, lineage.
- **Immediate containment:** Remove decision claim/ranking, label affected results experimental/invalid, freeze recompute, identify users/outputs affected, recalculate after validation.
- **Detection and proof:** Temporal holdout, known-growth fixtures, missing/small-cohort tests, version isolation, metric card and independent analyst review.

### FC-13 — Accessibility regression makes essential workflows impossible

- **Evidence:** CONFIRMED keyboard/semantic gaps.
- **Trigger:** Click-only rows/headers, custom menu/tab change, auto-refresh, modal/focus update, sticky layout, or visual redesign.
- **Failure chain:** Keyboard/screen-reader user cannot reach/identify action or loses context; status disappears; form errors are not connected; workflow cannot complete.
- **Symptoms:** No visible focus, Tab skips action, aria state incorrect, screen reader announces unlabeled input, focus jumps after refresh.
- **Impact:** Customer exclusion, task failure, potential legal/compliance exposure.
- **Required behavior:** Native semantics, complete keyboard path, stable focus, labels/errors/live regions, pause controls, WCAG 2.2 AA manual and automated evidence.
- **Immediate containment:** Restore native/link/button path, disable disruptive refresh/control, provide accessible alternate workflow, announce known limitation.
- **Detection and proof:** Keyboard-only and NVDA/VoiceOver critical-journey test at supported responsive states; automated scan alone is insufficient.

### FC-14 — Rights-ready status becomes false after an asset change

- **Evidence:** STRUCTURALLY PRESENT.
- **Trigger:** License, asset link, attribution, disclosure, or policy changes after checklist approval.
- **Failure chain:** Point-in-time ready record remains displayed as current; export/publication proceeds without required rights evidence.
- **Symptoms:** Ready status predates current asset version, required attribution empty, removed asset still referenced.
- **Impact:** Copyright/licensing complaint, takedown, reputational and financial harm.
- **Required behavior:** Readiness derived from exact versioned dependencies; any dependency change invalidates/requires review.
- **Immediate containment:** Block publication/export ready claim, snapshot evidence, re-review all changed dependencies, notify affected owner.
- **Detection and proof:** Mutation tests for every dependency plus periodic query for ready records whose dependency version is newer.

### FC-15 — Credential appears revoked while remaining externally valid

- **Evidence:** CONFIRMED local-only revoke behavior.
- **Trigger:** User clicks revoke; provider call/secret deletion is absent or fails.
- **Failure chain:** Local metadata says revoked; token remains in secret backend/provider; scheduled/concurrent process may continue using it.
- **Symptoms:** Sync/API activity after revoked timestamp, secret reference still resolves, provider account lists active token.
- **Impact:** Unauthorized continued access and false security assurance.
- **Required behavior:** Distinct disable/pending/provider-revoked/verified states with idempotent external revocation and secret removal.
- **Immediate containment:** Disable jobs locally, revoke at provider manually through authorized operator, disable/delete secret, audit uses since request.
- **Detection and proof:** Staging revoke followed by provider access denial; partial-failure/retry/concurrent-sync tests.

### FC-16 — Rollback restores code but not compatible schema/data

- **Evidence:** CHANGE-INTRODUCED.
- **Trigger:** Deployment changes schema/data and a later application fault prompts image rollback.
- **Failure chain:** Old code starts against forward-only schema/data; reads wrong meanings or fails; operator attempts unsafe downgrade; outage/data damage grows.
- **Symptoms:** Rollback image health fails, missing/renamed column errors, incompatible enum/state, data transformation cannot reverse.
- **Impact:** Prolonged outage and permanent data loss.
- **Required behavior:** Expand/migrate/contract deployment, backward-compatible intermediate releases, forward-fix plan, and tested artifact/schema compatibility matrix.
- **Immediate containment:** Stop automated oscillation between releases, keep compatible version, use read-only/degraded mode, consult migration recovery plan.
- **Detection and proof:** Deploy N schema with N-1 compatible app where policy requires, rollback rehearsal on production-like copy, irreversible operations explicitly approved.

### FC-17 — Observability leaks secrets while still failing to explain the incident

- **Evidence:** CONFIRMED raw SQL/content logging risk and 100% trace sampling.
- **Trigger:** Provider/database/form error includes URL, key, email, transcript, description, SQL parameters, or token reference.
- **Failure chain:** Error logger/telemetry captures sensitive payload; separate components lack shared correlation; operators search more logs and widen exposure.
- **Symptoms:** Secret/private strings in logs/Sentry, huge noisy events, no request-job-run link, ambiguous release.
- **Impact:** Secondary privacy/security incident plus slow recovery.
- **Required behavior:** Structured redacted logs, canary scrub tests, release/environment/correlation/causation IDs, targeted sampling, access/retention policy.
- **Immediate containment:** Restrict/delete affected logs according to evidence policy, rotate exposed secrets, preserve sanitized incident metadata, fix scrubber.
- **Detection and proof:** Synthetic secret/PII canaries must never reach sinks; trace one test request across all components without payload leakage.

### FC-18 — One fix silently invalidates another completed checklist item

- **Evidence:** CHANGE-INTRODUCED and especially likely in this coupled repository.
- **Trigger:** Later refactor changes auth route classification, transaction boundary, schema, CSP assets, job state, metric version, or UI semantics.
- **Failure chain:** Earlier task stays checked; full suite misses the cross-domain effect; release assumes all controls remain true.
- **Symptoms:** Tracker complete but old negative test removed/not run, drift returns, new route lacks control, manual accessibility result is stale.
- **Impact:** False production-readiness evidence and regression.
- **Required behavior:** Dependency-aware revalidation; completion can be reopened; invariant tests run continuously; release gate checks exact artifact.
- **Immediate containment:** Uncheck/reopen affected task and downstream gates, stop rollout, bisect change, restore control/test.
- **Detection and proof:** Traceability map from requirements to tests/files; changed-area impact review; mutation/red-team review of completed controls before release.

## 6. Remediation and change-management failure register

These risks exist specifically because a large audit is being implemented incrementally, often with Codex. The safe outcome is not merely code generation; it is verified behavior on the exact target environment and data shape.

| ID | Trigger / what can go wrong | Bad behavior, symptoms, and impact | Required behavior, watch signal, and proof |
|---|---|---|---|
| CHG-001 | Ask Codex to fix many unrelated findings in one task | Huge diff, hidden assumptions, impossible review, coupled rollback, partial checklist completion | One finding/change set at a time; dependency plan; focused and full tests; stop after the task |
| CHG-002 | Codex marks boxes based on implementation rather than evidence | Tracker claims complete while migration/manual/security criteria were never run | Leave unsupported criteria unchecked; completion record must contain exact commands/results and manual blockers |
| CHG-003 | Baseline was never reproduced | Fix may address the wrong path; no proof behavior changed | Capture failing test/query/request/log before edit; new regression test must fail on old behavior and pass on new |
| CHG-004 | Test is weakened/deleted to pass | Green CI hides regression or changed requirement | Replace only with stronger requirement-backed test; review assertion diff; use mutation/fault test on Critical paths |
| CHG-005 | Mock-only tests replace integration evidence | Fake database/Redis/API semantics differ from production; race/transaction defect survives | PostgreSQL/Redis/worker integration lane and fault fixtures; mocks only at controlled external boundary |
| CHG-006 | Change tested only on blank database | Legacy/upgraded live shapes fail; data migration corrupts edge rows | Test blank, prior head, every supported legacy fixture, and a production-like copy with anomaly rows |
| CHG-007 | Existing applied migration is edited | Fresh environments differ from live history; audit trail breaks | Append a new revision; verify multiple paths converge to identical head |
| CHG-008 | Migration is stamped to bypass table-exists | Version table lies while schema/data semantics remain old | Fingerprint/convert/validate; stamp only after proven equivalence |
| CHG-009 | Destructive repair runs on real data before rehearsal | Irrecoverable deletion/truncation/deduplication error | Backup and restore proof; read-only report; copy rehearsal; explicit authorization; reversible change log |
| CHG-010 | Backup exists but restore was never tested | Incident reveals corrupt/incomplete/inaccessible backup | Scheduled restore drill with checksum, row/invariant checks, RPO/RTO measurement |
| CHG-011 | Database URL points to wrong environment | Tests/migration mutate production or deploy uses test DB | Environment identity banner, target allowlist, explicit confirmation for destructive commands, distinct credentials/network |
| CHG-012 | Configuration fallback masks a missing value | New deployment silently runs insecure/wrong mode | Validated settings; production fail-fast; configuration contract tests |
| CHG-013 | Refactor changes transaction ownership | Nested commit/rollback, long locks, partial state | Application service owns transaction; transaction-boundary tests with injected failures |
| CHG-014 | Refactor changes import order/global extension state | Duplicate handlers, stale settings, test pollution | Role factories, init-app extensions, multiple-app isolation tests |
| CHG-015 | New route omits auth/CSRF/limit/error controls | A fixed app reintroduces an unprotected path | Default-deny route metadata and automated route inventory/control tests |
| CHG-016 | New field bypasses validation/export/privacy rules | Oversized/unsafe/private value reaches DB or export | Central schemas/sinks, field inventory, generative boundary tests, export contract update |
| CHG-017 | Dependency upgrade changes defaults | Cookie, proxy, serialization, retry, SQL, template escaping, or async behavior shifts | Read changelog/migration notes; lock; compatibility tests; canary; rollback artifact |
| CHG-018 | Major dependencies upgraded together | Root cause of regression cannot be isolated | Small upgrade batches; bisectable commits; record resolved transitive graph |
| CHG-019 | Framework version supported locally but not in image/CI | Works on developer machine, fails build/runtime | One declared interpreter/platform matrix and clean-image install test |
| CHG-020 | Security hardening breaks required UI/API without fallback | CSP blocks scripts, Secure cookie blocks HTTP dev, ACL blocks worker, auth loop | Staging browser/integration test; environment-aware safe config; never disable control globally as quick fix |
| CHG-021 | Performance optimization changes semantics | Faster query drops nulls, changes tie ordering, crosses tenant/run boundary | Equivalence fixtures, invariant/property tests, authorized scope and version key assertions |
| CHG-022 | Caching introduced without invalidation/authorization key | Stale or cross-user private response served | Cache key includes identity/tenant/version; no-store private; invalidation tests |
| CHG-023 | New index/constraint locks production table | Long outage/blocking writes | Estimate table/rewrite/lock; concurrent/online strategy; lock timeout; abort/runbook |
| CHG-024 | Rollout sends 100% traffic immediately | Latent regression becomes full outage | Canary/percentage rollout, health/SLO guard, automatic/manual halt, capacity slack |
| CHG-025 | Rollback destroys new-format data | Old code writes/reads incompatible semantics | Expand-contract compatibility, forward fix, tested schema/artifact matrix |
| CHG-026 | Manual production fix is not encoded | Drift returns on next deploy; no audit | Emergency action recorded; follow-up migration/IaC/code; drift check |
| CHG-027 | Secrets/private data copied into fixtures or AI prompts | Permanent disclosure in history/logs | Synthetic/sanitized fixtures; scanners; rotate exposed values; minimize evidence |
| CHG-028 | Two Codex tasks edit same files/worktree | Lost changes, conflicting migrations, inconsistent tracker | Separate worktrees and non-overlapping ownership; serialize shared schema/config work |
| CHG-029 | Checklist task remains checked after dependent change | Stale assurance | Impact map and reopen rule; exact-release final verification |
| CHG-030 | Negative or inconclusive experiment is ignored | Team repeats failed approach or overstates readiness | Record negative result, hypothesis, evidence, and decision; do not convert absence of failure into proof |

## 7. Cybersecurity, abuse, privacy, and browser failure register

| ID | Trigger / attack or mistake | Bad behavior and impact | Required behavior, detection, and edge test |
|---|---|---|---|
| SEC-FM-001 | Auth configuration absent | Anonymous full access | Fail closed/startup refusal; anonymous route matrix |
| SEC-FM-002 | Weak/default/reused session secret | Forged/replayed session | Strong managed per-environment key, expiry/rotation; forged/old-cookie tests |
| SEC-FM-003 | Session fixation at login/privilege change | Attacker-chosen session persists | Regenerate/clear session; pre/post-login cookie test |
| SEC-FM-004 | Session has no absolute/idle expiry | Stolen cookie remains useful | Bounded idle/absolute lifetime and revocation; fake-time tests |
| SEC-FM-005 | Logout only changes page state | Cookie/server session remains accepted | Invalidate session and CSRF state; replay-after-logout test |
| SEC-FM-006 | One shared password for all humans | No attribution/revocation/least privilege | Per-user OIDC identity, MFA policy, roles, audit |
| SEC-FM-007 | Object ID changed in URL/form | IDOR reads/edits another job/video/analytics record | Server-side resource authorization; cross-user/role matrix |
| SEC-FM-008 | Socket room ID guessed | Job events disclosed | Authenticate connect and authorize each join; negative room tests |
| SEC-FM-009 | Admin action hidden only in UI | Direct request performs action | Server-side permission on every action; direct/API test |
| SEC-FM-010 | CSRF token absent/invalid not enforced | Cross-site mutation/job/export/logout | Central anti-CSRF plus Origin; form/fetch cross-site tests |
| SEC-FM-011 | State-changing GET prefetched/crawled | Unexpected expensive job/data change | Safe GET/HEAD; crawler test asserts no writes/jobs |
| SEC-FM-012 | Login has no shared rate/abuse control | Brute force/credential stuffing | Identity-aware shared limits, MFA/lock policy, alerts |
| SEC-FM-013 | Proxy address trusted incorrectly | Limits bypassed or all users share one quota | Fixed trusted-hop parsing; spoofed-forwarded-header tests |
| SEC-FM-014 | Host header unvalidated | Poisoned reset/link/cache URLs | Host allowlist and canonical external URL; hostile Host tests |
| SEC-FM-015 | HTTP accepted or Secure cookie absent | MITM/session disclosure | TLS ingress, verified proxy scheme, Secure cookies, HSTS after validation |
| SEC-FM-016 | CSP missing/too broad | XSS/supply-chain script execution | Nonce/hash restrictive CSP, no unsafe-eval; browser violation test |
| SEC-FM-017 | CSP report endpoint logs payload secrets | Privacy leak through reports | Minimize/redact reports; rate/size bounds |
| SEC-FM-018 | CDN asset mutable/no integrity | Compromised dependency executes in customer origin | Self-host locked hashed assets or SRI/allowlist/fallback |
| SEC-FM-019 | Inline script added later | CSP weakened globally to make page work | Nonce/module build; CI CSP/static check |
| SEC-FM-020 | User URL uses javascript/data/encoded scheme | Stored script executes on click | Canonical HTTPS allowlist; browser corpus test |
| SEC-FM-021 | Open redirect normalization differs by browser/proxy | Phishing/token leakage | Fixed-origin path resolution; slash/backslash/encoding tests |
| SEC-FM-022 | Formula marker in exported cell | Spreadsheet formula/exfiltration | Central text-cell neutralizer; client/parser round trip |
| SEC-FM-023 | HTML/Markdown later rendered unsafely | Stored XSS | Contextual output encoding/sanitizer allowlist; payload corpus |
| SEC-FM-024 | Error/health exposes URL, SQL, path, queue, exception | Reconnaissance/secret/private-data leak | Stable safe errors, protected redacted diagnostics; forbidden-string assertions |
| SEC-FM-025 | Export bundles private/public/credential fields | Privacy breach | Dataset-level authorization/minimization/confirmation/audit |
| SEC-FM-026 | Export link predictable or long-lived | Unauthorized download | Random/signed expiring access, reauthorize download, no-store |
| SEC-FM-027 | Oversized body/header/form/list | Memory/DB/log denial of service | Proxy/app/schema/DB bounds; exactly-at/over-limit tests |
| SEC-FM-028 | Compressed or multipart amplification | Limit bypass/resource exhaustion | Ingress decoded/body/part limits and early rejection |
| SEC-FM-029 | Hidden metadata field tampered | False canonical data saved | Server-side result reference/refetch; tamper/replay tests |
| SEC-FM-030 | Log injection via newline/control chars | Forged/misparsed audit trail | Structured logging and escaped/truncated fields |
| SEC-FM-031 | Secret appears in command/process env/debug output | Credential leakage | Secret files/manager, redaction, restricted process access |
| SEC-FM-032 | Broad secret injected to all containers | One compromise reaches all providers/data | Per-role secret inventory and distribution |
| SEC-FM-033 | Redis default user unrestricted | Queue/admin compromise | ACLs, network segmentation, TLS across hosts, command denial |
| SEC-FM-034 | Containers run as root/writable | Larger compromise blast radius | Non-root, read-only, cap drop, no-new-privileges, runtime inspection |
| SEC-FM-035 | DB runtime role owns schema | Web compromise alters/drops schema | Separate migration owner and least runtime grants |
| SEC-FM-036 | Backup/log/env file mode 0644 | Same-host disclosure | Restrictive umask/ownership, encryption, path permission tests |
| SEC-FM-037 | Telemetry sends private content/100% traces | Privacy/cost incident | Scrubbers, targeted sampling, retention/access policy, canaries |
| SEC-FM-038 | OAuth revoke is local only | Token remains active | Provider revoke + secret disable + verified state |
| SEC-FM-039 | OAuth scopes expand silently | Excess provider access | Scope allowlist, consent/review, reauthorization |
| SEC-FM-040 | Dependency/action/image reference mutable | Supply-chain substitution | Hash/digest/SHA pins, provenance, automated reviewed update |
| SEC-FM-041 | Vulnerability suppression never expires | Known exploitable debt persists | Owner/reason/compensating control/expiry/retest |
| SEC-FM-042 | Security scanner green is treated as proof | Design/control flaws missed | ASVS threat model, manual review, DAST/pentest, negative tests |
| SEC-FM-043 | Account/role removed but sessions/jobs persist | Former user retains access/effects | Immediate revocation propagation and job ownership policy |
| SEC-FM-044 | Tenant/customer boundary absent in future SaaS | Cross-customer data/export/cache leak | Tenant key in every resource/query/job/cache/audit; isolation tests |
| SEC-FM-045 | Privacy deletion removes canonical row but not raw/export/log/backup | Incomplete data-subject response | Data map, tombstone/retention-aware deletion, verification report |

## 8. Database, migration, transaction, and data-quality failure register

| ID | Trigger / edge case | Bad behavior and impact | Required behavior, detection, and test |
|---|---|---|---|
| DB-FM-001 | Provider count exceeds INTEGER | Insert/update overflow and batch rollback | BIGINT inventory/migration; boundary values |
| DB-FM-002 | Negative count/rate/percentage | Impossible analytics and ordering | Schema + CheckConstraint; negative/over-100 tests |
| DB-FM-003 | NaN/Infinity float input | Comparisons/JSON/DB aggregation break | Finite validation and exact types |
| DB-FM-004 | Float used for money | Rounding/reconciliation errors | Decimal/NUMERIC, currency/unit, rounding tests |
| DB-FM-005 | Missing value coerced to zero | Biased metrics | Null + reason and eligibility |
| DB-FM-006 | Empty string, null, unknown treated alike | Broken validation/analysis | Explicit semantics and migration |
| DB-FM-007 | Naive timestamp crosses timezone/DST | Wrong day/order/schedule/quota reset | Aware UTC instants + IANA display/schedule |
| DB-FM-008 | Legacy text timestamp unparseable/ambiguous | Silent guessed history | Anomaly report/quarantine, never guess silently |
| DB-FM-009 | Nested helper rolls back caller transaction | Unrelated durable work lost | One transaction owner/savepoints |
| DB-FM-010 | Helper commits inside larger workflow | Partial state cannot roll back atomically | Explicit unit of work |
| DB-FM-011 | Commit acknowledgement lost | Retry duplicates effect | Idempotency key/natural uniqueness and outcome lookup |
| DB-FM-012 | Two workers upsert same provider ID | Unique error/duplicate snapshots | Atomic upsert, isolation, retry/conflict contract |
| DB-FM-013 | Two users edit same row | Last-write-wins data loss | Version/If-Match conflict |
| DB-FM-014 | Bulk update bypasses audit/invalidation | Stale derived/rights state | Domain service plus audit and recompute |
| DB-FM-015 | Foreign keys off in SQLite | Orphan local/test data | PRAGMA on every connection or unsupported mode |
| DB-FM-016 | SQLite concurrent writers | Locked DB/timeouts/partial workflow | PostgreSQL production; bounded WAL single-user mode |
| DB-FM-017 | Missing FK index | Slow join/delete and long locks | Catalog review and EXPLAIN budget |
| DB-FM-018 | Redundant index added | Write/storage cost without benefit | Index equivalence/usage review |
| DB-FM-019 | Unique constraint added with existing duplicates | Migration fails/chooses arbitrary row | Preflight report, deterministic approved repair |
| DB-FM-020 | Check constraint added without validating history | Invalid rows remain or deployment fails | NOT VALID/repair/validate plan where applicable |
| DB-FM-021 | Channel snapshot written per video | Duplicate time-series points | One per run + unique identity |
| DB-FM-022 | Duplicate canonical/history columns diverge | Different screens/exports disagree | One source or enforced semantic invariant |
| DB-FM-023 | Algorithm rows from versions mix | Duplicate/conflicting ranks | Immutable run and one promoted active version |
| DB-FM-024 | Raw payload absent/corrupt | Cannot reproduce parser/result | Checksum/versioned source event and replay |
| DB-FM-025 | Raw payload retains secrets/private data too long | Privacy/storage incident | Redaction, encryption, access, retention/deletion |
| DB-FM-026 | Collection status says complete with failures | Operational truth corrupted | State machine and count equations |
| DB-FM-027 | Run abandoned after worker death | Permanently running/stuck UI | Lease/heartbeat expiry and recovery state |
| DB-FM-028 | Duplicate daily analytics/checkpoint/link | Double-counted business facts | Natural uniqueness/idempotent import |
| DB-FM-029 | Analytics attached without ownership | Private/misleading cross-channel data | Verified ownership and authorization |
| DB-FM-030 | Currency/unit absent | Values aggregated incompatibly | Explicit currency/unit and conversion policy |
| DB-FM-031 | Asset changes after rights approval | Stale readiness | Versioned dependency invalidation |
| DB-FM-032 | Delete cascades unexpectedly | Historical/evidence loss | Explicit referential policy and dry-run |
| DB-FM-033 | Soft-deleted row still participates | Metrics/selectors include invalid data | Active filters/invariants and tests |
| DB-FM-034 | Restore produces old schema against new app | Startup/data errors | Restore + migration runbook and compatibility test |
| DB-FM-035 | Sequence lower than restored max ID | Future inserts collide | Set/validate sequences after restore |
| DB-FM-036 | Migration runs twice | Duplicate transform/index/table conflict | Idempotent guard or safe refusal, one runner |
| DB-FM-037 | Long transaction holds locks during API/export | Latency/deadlock/outage | Short transactions; background snapshot/cursor |
| DB-FM-038 | Deadlock victim retried unsafely | Duplicate side effect or user 500 | Typed bounded transaction retry only when idempotent |
| DB-FM-039 | Read replica/stale cache introduced | User sees stale job/rights/auth state | Consistency requirement per read, version/freshness |
| DB-FM-040 | Retention deletes source before derived/export evidence | Unreproducible result | Retention dependency graph and tombstone/manifest |

## 9. Queue, scheduler, concurrency, real-time, and dependency failure register

| ID | Trigger / edge case | Bad behavior and impact | Required behavior, detection, and test |
|---|---|---|---|
| JOB-FM-001 | Double click/request retry | Duplicate job | Idempotency key; return existing |
| JOB-FM-002 | Two schedulers active | Duplicate dispatch | Leader lease/fencing + dispatch idempotency |
| JOB-FM-003 | Scheduler cancel then crashes before create | Schedule lost | Transactional desired schedule/reconciliation |
| JOB-FM-004 | DST gap/overlap/timezone changed | Missing/double run | IANA timezone and explicit catch-up policy |
| JOB-FM-005 | Worker dies before acknowledgement | Job lost/repeated ambiguously | Durable lease, idempotent replay, recovery |
| JOB-FM-006 | Worker dies after DB commit before status update | Data saved but job appears failed/running | Reconcile durable outcome/status transactionally |
| JOB-FM-007 | Status completes before output publish | 100% with missing file/result | Atomic publish then terminal status |
| JOB-FM-008 | Cancellation during commit | Partial unclear state | Safe cancellation checkpoints; transaction completion policy |
| JOB-FM-009 | Cancellation ignored during long call | User cannot stop quota/cost | Propagated deadline/cancel or bounded call |
| JOB-FM-010 | Poison job retries forever | Queue blocked/cost storm | Max attempts and dead-letter |
| JOB-FM-011 | Large job payload/result stored in Redis | Memory/latency/eviction | Small references, external durable result, limits |
| JOB-FM-012 | One slow transcript monopolizes worker | Head-of-line blocking | Separate queues/concurrency/deadline |
| JOB-FM-013 | High-priority queue starves normal work | Unbounded customer delay | Weighted fairness/quotas |
| JOB-FM-014 | Many jobs from one actor/channel | Noisy-neighbor exhaustion | Per-actor/channel admission and quotas |
| JOB-FM-015 | Redis restart loses transient metadata | UI/status disagreement | DB authoritative state/reconciliation |
| JOB-FM-016 | Redis maxmemory eviction removes queue keys | Lost jobs/state | Noeviction/appropriate policy and memory alerts |
| JOB-FM-017 | Redis RDB persistence window loses recent work | Replay/loss after crash | Define durable source, AOF/DB/reconciliation as required |
| JOB-FM-018 | Redis credentials rotate mid-job | Disconnect/crash loop | Graceful reconnect/dual credential window where safe |
| JOB-FM-019 | DB pool exhausted by workers | Web unavailable | Separate pools/budgets/backpressure |
| JOB-FM-020 | External call lacks deadline | Worker hangs indefinitely | Connect/read/total deadlines and watchdog |
| JOB-FM-021 | Circuit breaker opens globally for one tenant/input | Healthy work blocked | Correct key/scope and half-open policy |
| JOB-FM-022 | Circuit breaker never closes | Persistent degraded service | Tested recovery/visibility/manual override |
| JOB-FM-023 | Retry-After is ignored or exceeds total deadline | Provider abuse/long stall | Honor within capped total deadline |
| JOB-FM-024 | Non-idempotent operation retried | Duplicate mutation | Idempotency token or no automatic retry |
| JOB-FM-025 | All clients retry at same interval | Thundering herd | Full jitter and bounded attempts |
| JOB-FM-026 | Polling continues in hidden tabs | Unnecessary web/DB load | Visibility pause and manual control |
| JOB-FM-027 | Overlapping polls finish out of order | Stale status overwrites fresh | Abort/monotonic request ID |
| JOB-FM-028 | WebSocket event arrives before listener/after reconnect | Missed progress | Durable status resync and sequence number |
| JOB-FM-029 | Event duplicated/reordered | Progress goes backwards/double notification | Idempotent sequenced client reducer |
| JOB-FM-030 | Unauthorized event broadcast | Cross-user leak | Room/object auth and scoped publish |
| JOB-FM-031 | Queue clock skew/TTL expiry | Premature/late lease/retry | Server/monotonic time policy and skew test |
| JOB-FM-032 | Scheduler host down at run time | Missed work | Durable next run/misfire policy and alert |
| JOB-FM-033 | Job code deployed while old payload queued | Deserialization/behavior incompatibility | Versioned payload schema and rolling compatibility |
| JOB-FM-034 | Job references deleted/changed record | Crash or wrong target | Version/ownership validation at execution |
| JOB-FM-035 | Progress denominator changes during work | >100%/backward progress | Snapshot work plan or stage-based semantics |

## 10. External API, transcript, network, proxy, and infrastructure failure register

| ID | Trigger / edge case | Bad behavior and impact | Required behavior, detection, and test |
|---|---|---|---|
| NET-FM-001 | DNS resolution fails/returns stale address | Calls hang/fail inconsistently | Bounded DNS/connect deadline, typed error, resolver metrics |
| NET-FM-002 | IPv4 works but IPv6 path fails | Intermittent connection by address selection | Dual-stack test or deliberate family policy |
| NET-FM-003 | TLS certificate expired/wrong host/untrusted CA | Outbound/inbound outage or insecure bypass | Strict verification, renewal alerts, no verify=false |
| NET-FM-004 | System clock wrong | TLS/session/token/schedule failures | Time synchronization alert and skew-safe diagnostics |
| NET-FM-005 | Reverse proxy forwarded scheme wrong | Redirect loop/insecure cookie/URL | Trusted proxy configuration and external smoke |
| NET-FM-006 | Proxy strips WebSocket upgrade | Realtime polling fallback or failure | Explicit upgrade config and transport test |
| NET-FM-007 | Proxy/LB timeout shorter than app behavior | 502/504 while backend continues side effect | Async jobs/idempotency, aligned deadlines |
| NET-FM-008 | Request body/header limit differs across layers | Valid request rejected or oversized bypass | Documented consistent limits and boundary tests |
| NET-FM-009 | Host port binds all interfaces unexpectedly | Trusted-local app exposed to LAN/public | Private bind/firewall/reachability test |
| NET-FM-010 | Flat container network | Compromised service reaches DB/Redis | Segmentation and service-to-service denial tests |
| NET-FM-011 | Egress unrestricted | Compromise exfiltrates data | Required-destination egress policy and monitoring |
| NET-FM-012 | Provider IP/rate blocks transcript endpoints | Transcript jobs repeatedly fail | Typed unavailable state, alternate compliant provider/exit, circuit breaker |
| NET-FM-013 | Transcript library ignores deadline | Worker/queue stalls | Process/thread isolation or provider with explicit timeout |
| NET-FM-014 | Transcript disabled globally but single-video defaults on | Unexpected latency/privacy/IP block | One configuration source; explicit opt-in |
| NET-FM-015 | Transcript unavailable message stored as transcript | Analytics/search treat error text as content | Separate status/error from nullable text |
| NET-FM-016 | YouTube key invalid/restricted incorrectly | All calls fail and appear empty | Startup/health validation, typed auth failure, pause jobs |
| NET-FM-017 | Daily quota exhausted | Work fails until reset; retries waste more | Durable ledger, hard stop, reset time, priority |
| NET-FM-018 | Search fallback costs 100 units/page | Estimate far below actual | Endpoint-accurate reservation and reconcile |
| NET-FM-019 | Pagination token repeats/cycles | Infinite calls/duplicates | Seen-token guard, page/max-item bound |
| NET-FM-020 | Provider returns duplicate/missing/out-of-order items | Duplicate/missing videos | Provider-ID dedupe and completeness metadata |
| NET-FM-021 | Provider response omits hidden statistics | Zero-biased metrics | Preserve missingness reason |
| NET-FM-022 | Provider changes field/type/enum | Parser crash or silent default | Contract fixture, schema validation, unknown-field telemetry |
| NET-FM-023 | Provider returns successful HTTP with error payload | False success | Semantic validation and typed result |
| NET-FM-024 | 429/5xx body is HTML/invalid JSON | Parser masks real status | Status-first error parsing with bounded body |
| NET-FM-025 | Partial batch response omits some requested IDs | Missing rows counted skipped/success | Reconcile requested/returned IDs with per-item status |
| NET-FM-026 | Channel handle/custom URL resolves wrong channel | Research attached to wrong entity | Canonical channel ID confirmation and UI preview |
| NET-FM-027 | Video changes channel/privacy/deletes | Stale relationship/content | Versioned collection status and unavailable state |
| NET-FM-028 | Thumbnail URL changes/expires/serves huge file | Broken UI/SSRF/resource abuse if fetched server-side | Host/type/size/time limits and fallback |
| NET-FM-029 | External telemetry/secret backend slow | Main request/job blocked | Async/bounded client and graceful telemetry degradation |
| NET-FM-030 | Third-party browser CDN/font/embed blocked | Layout/function breaks | Self-host core assets and tested fallback |
| NET-FM-031 | Service startup races dependency | Crash loop before DB/Redis ready | Health-gated startup with jitter |
| NET-FM-032 | Network partition permits split scheduler/lock holders | Duplicate work | Fencing token and durable idempotency |
| NET-FM-033 | Firewall change blocks backup/monitoring not app | Silent loss of recovery/visibility | Synthetic path checks for every critical flow |
| NET-FM-034 | Certificate renewal reload drops connections | Brief outage/reconnect storm | Graceful reload and client jitter/resync |
| NET-FM-035 | MTU/proxy buffering causes large export failure | Small tests pass, large response stalls | Background object download and representative network test |

## 11. UI, UX, HCI, accessibility, browser, and human-error failure register

| ID | Trigger / edge case | Bad behavior and customer impact | Required behavior, detection, and test |
|---|---|---|---|
| UX-FM-001 | Click-only table header | Keyboard cannot sort | Native button, aria-sort, keyboard test |
| UX-FM-002 | Clickable row has no link | Keyboard/screen reader cannot open item | Real descriptive link |
| UX-FM-003 | Custom tabs omit roles/state/keys | Context/selection inaccessible | Complete APG pattern or simpler native control |
| UX-FM-004 | Menu opens without focus/escape/return | Keyboard user lost/trapped | Deterministic focus model |
| UX-FM-005 | Placeholder is only label | Control purpose disappears/ambiguous | Persistent associated label/instructions |
| UX-FM-006 | Error only flashed then auto-dismissed | User misses cause and loses input | Persistent summary + inline error + retained values |
| UX-FM-007 | Required/format/unit unstated | Preventable validation errors | Pre-input instructions/constraints |
| UX-FM-008 | Focus resets after validation/rerender | User restarts navigation | Focus first error/meaningful stable element |
| UX-FM-009 | Auto-refresh steals focus/scroll/state | Active task interrupted | Non-destructive updates and user control |
| UX-FM-010 | Live region announces every polling row | Screen-reader flood | Concise meaningful status with polite rate |
| UX-FM-011 | Polling hidden/offline | Battery/network/server waste | Visibility/offline pause/backoff |
| UX-FM-012 | Stale response overwrites new filter | Wrong table/data shown | Abort/sequence requests |
| UX-FM-013 | Loading spinner has no text | Unknown progress/status | Accessible status and durable job state |
| UX-FM-014 | Toast is only evidence of save/failure | User cannot verify outcome | Persistent state/history |
| UX-FM-015 | Active navigation shown by color only | Current location unclear | aria-current + non-color styling |
| UX-FM-016 | Flat nav overflows tablet/mobile | Destinations hidden/unfindable | Task groups and accessible responsive menu |
| UX-FM-017 | Nested/multiple main landmarks | Landmark navigation confused | Exactly one main, labeled regions |
| UX-FM-018 | No skip link/sticky header obscures focus | Repetitive navigation/focus hidden | Skip target and focus-not-obscured tests |
| UX-FM-019 | TH scope/caption absent | Table relationships unclear | Caption/name and header association |
| UX-FM-020 | Horizontal table scroll loses identity | User compares wrong row/column | Labeled region, sticky context, responsive alternative |
| UX-FM-021 | 200%/400% zoom clips controls | Essential action impossible | Reflow and responsive tests |
| UX-FM-022 | Dark/light color contrast insufficient | Content/focus unreadable | Contrast/focus checks for all states |
| UX-FM-023 | Forced-colors mode removes state/focus | Windows high-contrast users blocked | Forced-color semantics/test |
| UX-FM-024 | Motion ignores reduced-motion | Vestibular discomfort/distraction | Reduced/removed nonessential animation |
| UX-FM-025 | Tiny target/adjacent destructive action | Accidental activation | WCAG target spacing/size and confirmation/undo |
| UX-FM-026 | Image alt duplicates title or is empty when informative | Noise or lost information | Contextual alt policy |
| UX-FM-027 | Iframe lacks title/minimum permissions/privacy mode | Inaccessible/privacy/capability excess | Titled, constrained, click-to-load/private embed |
| UX-FM-028 | Latest-100 selector omits older record | User cannot complete rights/analytics | Searchable server-side selector |
| UX-FM-029 | Unbounded selector/detail freezes DOM | Slow/crash, especially assistive tech | Pagination/virtualized accessible results |
| UX-FM-030 | Long form times out/navigates away | Work lost | Draft, warning, recoverable session policy |
| UX-FM-031 | Autosave overwrites concurrent edit | Silent loss | Versioned conflict-safe autosave |
| UX-FM-032 | Back button resubmits mutation | Duplicate action | PRG/idempotency and safe history |
| UX-FM-033 | Double click submits twice | Duplicate job/record | Disable with durable idempotency, not UI alone |
| UX-FM-034 | Destructive action lacks context/undo | Wrong record removed | Named confirmation and restore where possible |
| UX-FM-035 | Empty state appears like loading/error | User cannot choose next action | Distinct empty/loading/error/success states |
| UX-FM-036 | Progress reaches 100% before commit | User trusts unavailable output | Terminal only after durable publish |
| UX-FM-037 | Job fails partially but UI says complete | User misses missing data | Explicit partial state and per-item details |
| UX-FM-038 | Localized number/date parsed from display | Wrong stored value | Canonical input/storage and locale-aware display |
| UX-FM-039 | Arabic/RTL/long text breaks layout | Clipped/misordered workflow | Direction/length/responsive test if supported |
| UX-FM-040 | Browser extension/no-JS/CDN outage changes behavior | Core control silently absent | Server enforcement and graceful core fallback |
| UX-FM-041 | Session expires during long form/job | Lost input or unauthorized status leak | Draft/re-auth return and reauthorization |
| UX-FM-042 | Permission changes while page open | Stale UI submits forbidden action | Server denies and UI refreshes state safely |
| UX-FM-043 | Two records share title/thumbnail | User edits wrong entity | Provider ID/channel/date context |
| UX-FM-044 | Copy/export button reports success before clipboard/download | False confirmation | Verify API/result and accessible error |
| UX-FM-045 | Accessibility test only scans initial DOM | Menus/errors/tabs/job states untested | State inventory and manual critical journeys |

## 12. Analytics, data-science, labeling, and experiment failure register

| ID | Trigger / methodological edge | Bad output and decision impact | Required behavior, detection, and validation |
|---|---|---|---|
| DS-FM-001 | Lifetime views compare unequal ages | Older videos dominate | Fixed/age-conditioned observation window |
| DS-FM-002 | Video younger than one day clipped to one-day denominator | Early velocity understated/distorted | Incomplete window or time-aware model |
| DS-FM-003 | Hidden/missing engagement becomes zero | Rates/ranks biased downward | Null + missingness reason |
| DS-FM-004 | One-video channel/self comparison | Meaningless 1.0 looks valid | insufficient_data minimum sample |
| DS-FM-005 | Tiny/high-variance cohort | Unstable confident rank | Shrinkage/robust estimator or insufficient state |
| DS-FM-006 | Channel sizes/niches mixed | Simpson's paradox/confounded comparison | Defined comparable cohort/stratification |
| DS-FM-007 | Season/trend/event not controlled | Temporary spike called durable opportunity | Time controls and caveat/sensitivity |
| DS-FM-008 | Collection time differs across videos | Unequal exposure/freshness | Sampling window/freshness alignment |
| DS-FM-009 | Private/deleted failures excluded silently | Survivorship bias | Exclusion counts/reasons and sensitivity |
| DS-FM-010 | Manually chosen channels treated representative | Selection bias/generalization error | Sampling-frame disclosure and limits |
| DS-FM-011 | Search/quota truncates later pages | Coverage biased to returned order | Coverage/truncation metadata |
| DS-FM-012 | Duplicate snapshots treated independent | False precision/trend frequency | Sampling-event uniqueness |
| DS-FM-013 | Algorithm versions mix | Duplicate/inconsistent ranks | One immutable promoted run |
| DS-FM-014 | Threshold changes without version | Historical result silently changes | Versioned config/hash and run |
| DS-FM-015 | Input data changes after recompute | Output cannot reproduce | Input snapshot lineage |
| DS-FM-016 | Parser behavior changes | Metric shifts mistaken for market shift | Parser version and backfill/replay analysis |
| DS-FM-017 | Under-served label lacks demand/supply evidence | Descriptive outlier becomes market claim | Honest terminology or validated demand/supply |
| DS-FM-018 | Correlation interpreted causally | Wrong intervention/content strategy | Non-causal language and experiment |
| DS-FM-019 | Threshold tuned on final holdout | Optimistic validation | Train/validation/temporal holdout discipline |
| DS-FM-020 | Repeated experiments/metrics cherry-picked | False winner | Primary metric, multiple-testing/stopping policy |
| DS-FM-021 | Experiment peeking/stops on significance | Inflated false positive | Predefined duration/stopping/sequential method |
| DS-FM-022 | Treatment exposure/assignment missing | Invalid comparison | Immutable assignment/exposure log |
| DS-FM-023 | Concurrent packaging changes contaminate test | Cannot attribute outcome | Experiment exclusion/interaction policy |
| DS-FM-024 | Negative/null result hidden | Survivorship/publication bias | Report all registered outcomes |
| DS-FM-025 | Reviewer label definitions drift | Model/analysis changes by reviewer/time | Versioned guide/calibration/overlap |
| DS-FM-026 | One reviewer labels all data | Unmeasured subjective bias | Blind overlap/adjudication/agreement |
| DS-FM-027 | Agreement percentage used on imbalanced labels | Misleading quality | Appropriate statistic with prevalence/support |
| DS-FM-028 | Gold set leaks to reviewers | Artificial agreement | Blinded rotation/holdout |
| DS-FM-029 | Corrections overwrite original label | Audit/quality evidence lost | Append/supersede with before/after |
| DS-FM-030 | Invalid/insufficient result sortable as zero | UI ranking misleads | Separate status, exclude from ranking |
| DS-FM-031 | Confidence interval omitted | False precision | Uncertainty/sample/coverage display |
| DS-FM-032 | Metric optimized but business error cost ignored | High score harms decisions | Cost-sensitive validation and guardrails |
| DS-FM-033 | Drift not monitored | Previously valid model degrades | Coverage/distribution/performance triggers |
| DS-FM-034 | Currency/timezone/window differs across analytics | Invalid aggregation | Explicit units and normalized definitions |
| DS-FM-035 | Customer edits source labels after decision | Old thesis/result appears current | Versioned dependencies and invalidation |
| DS-FM-036 | Data repair/backfill creates artificial jump | Trend interpreted as behavior | Repair event marker and recompute policy |
| DS-FM-037 | Rankings expose exact ties in unstable order | UI flips repeatedly | Deterministic tie and stability rule |
| DS-FM-038 | No baseline | Complex heuristic looks good without comparison | Simple baseline and holdout |
| DS-FM-039 | Metric card/documentation disagrees with code | Misuse and debugging delay | Executable spec/version trace |
| DS-FM-040 | Customer sees internal heuristic as guaranteed forecast | Financial/reputation harm | Intended-use limits and calibrated product copy |

## 13. Product, customer, privacy, rights, and governance failure register

| ID | Trigger / product edge | Bad behavior and impact | Required behavior, detection, and test |
|---|---|---|---|
| PROD-FM-001 | Three collection routes behave differently | Confusion/inconsistent saved state | One canonical journey and redirects |
| PROD-FM-002 | Job has no cancel/retry/partial details | User waits/repeats/abandons | Durable job center/recovery |
| PROD-FM-003 | Old records excluded from selectors | Workflow impossible | Search/pagination/deep link |
| PROD-FM-004 | Dashboard/detail unbounded | Product slows as success grows | Stable pagination and budgets |
| PROD-FM-005 | Form error discards work | Time loss/frustration | Retained safe input/draft |
| PROD-FM-006 | No correction/supersession flow | Direct DB edit or stale bad decision | Governed audited correction |
| PROD-FM-007 | Any thesis state transition allowed | Launch without evidence/review | Role/state/evidence transition matrix |
| PROD-FM-008 | Monetization map alone implies launch ready | Incomplete governance | Rights, data, red-team, approval gates |
| PROD-FM-009 | Capability label says OAuth connected/revoked inaccurately | False trust | Verified state vocabulary |
| PROD-FM-010 | Owned analytics attaches to public/nonowned video | Privacy and data validity failure | Ownership verification |
| PROD-FM-011 | Public and private export combined by default | Accidental disclosure | Explicit scope/role/confirmation |
| PROD-FM-012 | No first-run dependency readiness | New user hits confusing failure | Safe onboarding/preflight |
| PROD-FM-013 | Empty workspace lacks next action | Activation failure | Guided first value |
| PROD-FM-014 | Metric freshness/source invisible | User acts on stale/unknown data | Freshness/lineage at decision |
| PROD-FM-015 | Product copy overclaims enterprise/security/AI insight | Customer/legal trust damage | Claims tied to verified evidence |
| PROD-FM-016 | No tenant model added before customers | Cross-customer design retrofit/leak | Tenant isolation requirements before onboarding multiple customers |
| PROD-FM-017 | Customer deletion/retention promise not executable | Compliance/trust failure | Data map and tested lifecycle |
| PROD-FM-018 | YouTube/provider terms change | Feature becomes noncompliant/unavailable | Policy owner/review/change response |
| PROD-FM-019 | Rights source/license proof link disappears | Cannot defend use | Evidence snapshot/checksum/retention within lawful policy |
| PROD-FM-020 | Attribution required but blank/wrong version | Publication violation | Derived readiness and export attribution |
| PROD-FM-021 | User misunderstands public versus owned analytics | Wrong privacy expectation | Clear labels/boundaries/permissions |
| PROD-FM-022 | Support cannot identify customer job/run | Slow incident and privacy mistakes | Safe support correlation and role |
| PROD-FM-023 | Product telemetry measures clicks, not outcomes | False product-market confidence | Activation/completion/retention/trust metrics |
| PROD-FM-024 | No design partners/manual usability evidence | Technically ready but unusable | Observed target-user journeys |
| PROD-FM-025 | Pricing/limits ignore quota/compute cost | Negative unit economics/noisy neighbor | Cost model, quotas, metering, plan enforcement |
| PROD-FM-026 | Customer assumes transcript always available | Broken promise due IP/provider block | Capability status, fallback, honest SLA |
| PROD-FM-027 | Data export/import contract changes silently | Customer automation breaks | Version/manifest/deprecation |
| PROD-FM-028 | Customer acts on partial collection | Misleading decision | Partial state blocks/labels analysis |
| PROD-FM-029 | Audit events can be edited/deleted by subject role | Accountability lost | Append-only protected audit retention |
| PROD-FM-030 | Staff/operator sees more customer data than needed | Insider/privacy risk | Support/operator least privilege and access audit |

## 14. Performance, observability, release, recovery, CI, and supply-chain failure register

| ID | Trigger / edge case | Bad behavior and impact | Required behavior, detection, and test |
|---|---|---|---|
| OPS-FM-001 | Warm unloaded latency treated as capacity proof | Launch fails under concurrency | Load/spike/soak and percentile/SLO evidence |
| OPS-FM-002 | Average hides p99/tail | Some users/jobs consistently fail | Distribution by route/job/dependency |
| OPS-FM-003 | Browser polls all resources every 5s | DB/web amplification | Resource-specific conditional refresh |
| OPS-FM-004 | N+1 query grows with rows | Nonlinear latency/DB saturation | Query-count budget/set SQL |
| OPS-FM-005 | Large response/DOM grows without bound | Slow network/browser crash | Page/response budgets/pagination |
| OPS-FM-006 | Export holds full data in memory | OOM/timeout | Chunked background export |
| OPS-FM-007 | Temp export orphaned | Disk fills/outage | Finally cleanup + reaper/disk alerts |
| OPS-FM-008 | Logs unbounded | Disk/cost/privacy failure | Structured levels, rotation, retention, rate |
| OPS-FM-009 | Sentry traces 100% | Cost/noise/private data | Risk-aware sampling and budget |
| OPS-FM-010 | DB connection leak/pool exhaustion | Web/jobs stop | Teardown tests/pool metrics/timeouts |
| OPS-FM-011 | File/socket/thread leak | Gradual degradation | Resource baseline/soak test |
| OPS-FM-012 | Redis memory has no bound/policy | OOM/eviction | Capacity/maxmemory policy/alerts |
| OPS-FM-013 | Host vm.overcommit unsuitable for Redis | Fork/persistence failure | Host prerequisite check/runbook |
| OPS-FM-014 | CPU/memory limits absent | One service harms host | Measured resource limits/headroom |
| OPS-FM-015 | Limit too low | OOM kill/throttle under valid load | Load-derived budgets and alerts |
| OPS-FM-016 | Limit too high/no backpressure | Cascading saturation | Admission control/load shedding |
| OPS-FM-017 | Static assets unversioned/no cache | Slow pages/stale mismatch | Content hash/immutable cache |
| OPS-FM-018 | Compression absent/misapplied | Excess transfer or side-channel risk | Ingress policy and page tests |
| OPS-FM-019 | Health returns 200 while workers absent | Jobs accepted but never run | Readiness/operational capacity signal |
| OPS-FM-020 | Health depends on optional provider | Unnecessary outage | Criticality-based readiness |
| OPS-FM-021 | No release/config/change marker | Root cause hard to correlate | Release/config hash in telemetry |
| OPS-FM-022 | Alert on cause/noisy log rather than symptom | Pager noise/missed customer harm | SLO symptom alerts/runbooks |
| OPS-FM-023 | Alert has no owner/action | Long incident | Routed owner, severity, runbook, test |
| OPS-FM-024 | Backup succeeds but restore credentials lost | Recovery impossible | Independent access/restore drill |
| OPS-FM-025 | Backup includes corrupted state only | Restore reproduces incident | PITR/versioned backups/invariant checks |
| OPS-FM-026 | Restore overwrites current data accidentally | Secondary data loss | Isolated restore and explicit cutover |
| OPS-FM-027 | Deployment migration runs per replica | Race/duplicate DDL | One pre-start migration job |
| OPS-FM-028 | Rolling deploy mixes incompatible job/app versions | Failures/corruption | Backward-compatible payload/schema window |
| OPS-FM-029 | Canary not representative | Full rollout reveals hidden DB/tenant path | Traffic/data-shape coverage and staged percentage |
| OPS-FM-030 | Automatic rollback loops between bad states | Extended outage | Halt thresholds/manual ownership/schema compatibility |
| OPS-FM-031 | Mutable image/action/tag changes without code diff | Nonreproducible incident | Digest/SHA pin and provenance |
| OPS-FM-032 | Dependency lock absent | Fresh build differs | Hash lock and clean install |
| OPS-FM-033 | Vulnerability database/scan unavailable | Build passes without security evidence | Explicit fail/controlled exception policy |
| OPS-FM-034 | CI only tests SQLite | PostgreSQL semantics fail in production | Real integration lane |
| OPS-FM-035 | CI migration only tests blank DB | Upgrade path breaks | Historical fixtures and drift gate |
| OPS-FM-036 | Coverage percentage rewards shallow tests | Critical rollback/auth path untested | Branch/critical requirement tests/mutation |
| OPS-FM-037 | Warning budget ignored | Resource/deprecation failure accumulates | Zero-new warning and ownership |
| OPS-FM-038 | Flaky test retried until green | Intermittent race hidden | Quarantine with owner/expiry, root-cause fix |
| OPS-FM-039 | CI secrets available to untrusted PR/action | Supply-chain account compromise | Least permissions, protected context, SHA pins |
| OPS-FM-040 | Cache/artifact crosses trust boundary | Poisoned build/test | Scope/verify artifacts, treat as untrusted |
| OPS-FM-041 | Clock/timezone differs between web/worker/DB | Ordering/lease/schedule errors | UTC synchronization and skew test |
| OPS-FM-042 | No graceful degraded mode | Optional failure takes entire product | Read-only/disable optional jobs/controlled load shedding |
| OPS-FM-043 | Degraded mode serves stale result without label | Wrong decision | Visible freshness/quality state |
| OPS-FM-044 | Capacity grows organically beyond last test | Sudden threshold outage | Forecast/saturation trend and periodic retest |
| OPS-FM-045 | Incident fix not followed by reconciliation | Service restored but data remains wrong | Data impact query/repair and postmortem |

## 15. Symptom-driven senior debugging guides

### 15.1 Anonymous user receives a protected page or event

**Contain first**

1. Restrict ingress or disable the affected route/event.
2. Preserve access/audit logs and current auth configuration without printing secrets.
3. Rotate/invalidate sessions or credentials if compromise is plausible.

**Evidence to collect**

- Exact method/path/status and whether response contains protected fields.
- Release/config hash, auth_enabled/identity-provider readiness state, proxy headers, cookie presence, user/session/role, Socket.IO event/room.
- Route classification and authorization decision with safe reason.

**Hypothesis order**

1. Fail-open missing identity configuration.
2. Route absent from protection/default-allow inventory.
3. Authentication present but object/role authorization missing.
4. Proxy/session cookie scope or environment key reuse.
5. Cached private response.
6. Socket.IO handler bypassing HTTP middleware.

**Never do**

- Do not merely hide the link/button.
- Do not add one route-specific check without a route inventory/default-deny control.
- Do not paste cookies or secrets into the issue.

**Proof of resolution**

- Anonymous/cross-role HTTP, export, API, job, and Socket.IO matrix; cache cleared/new session; startup omission test.

### 15.2 A core route returns 500 after startup or deployment

**Contain first:** Stop rollout; keep compatible instances; use read-only/degraded page if possible; do not restart all replicas.

**Evidence**

- First failure timestamp, last release/config/migration, correlation ID, safe exception class/code, database Alembic version and schema fingerprint, readiness/liveness, dependency latency.

**Hypothesis order**

1. Schema/model drift or wrong database URL.
2. Missing/invalid configuration parsed at import.
3. Dependency not ready/credential rotated.
4. New code assumes non-null/new enum/field not backfilled.
5. template context/asset mismatch.
6. resource exhaustion or connection leak.

**Safe experiments**

- Reproduce exact request on staging/copy with same schema revision.
- Compare release artifact/digest and migration head; run read-only drift/invariant checks.
- Route to previous compatible instance only if schema compatibility is proven.

**Never do:** Blind stamp, edit applied migration, dump private SQL row values, or repeatedly restart without state capture.

### 15.3 Collection reports success but data is missing

**Contain first:** Pause downstream metric/export decisions and affected collection jobs.

**Evidence**

- job_id, collection_run_id, requested/found/saved/failed counts, commit interval, per-item IDs/statuses, DB durable counts/snapshots, provider call results, rollback/deadlock/overflow logs.

**Hypothesis order**

1. Mid-batch rollback/accounting defect.
2. Provider error converted to empty success.
3. omitted IDs in partial batch response.
4. transaction commit acknowledgement ambiguity.
5. duplicate/idempotent job returned another run.
6. wrong database/environment.
7. later cleanup/retention/soft-delete filter.

**Invariant query:** items_saved must equal the documented durable row effects for the run; every requested ID has a terminal per-item classification.

**Proof:** Inject a middle-row failure and ambiguous acknowledgement; reconcile reported versus committed rows exactly.

### 15.4 Collection suddenly finds zero videos

**Contain first:** Do not publish zero as research truth; mark affected runs suspect.

**Evidence:** Provider status/reason/request ID, key/quota state, resolution path, channel canonical ID, response schema, call attempts, network errors, prior normal count.

**Hypothesis order**

1. Invalid/restricted key or exhausted quota.
2. provider/transcript/network outage.
3. channel resolution to wrong/none ID.
4. parser contract change.
5. legitimate empty/private/deleted channel.
6. pagination/token defect.

**Watch signal:** completed-empty rate and channel count change should alert separately from failure rate.

**Proof:** A completed-empty run must retain valid provider evidence; all other cases use typed non-success state.

### 15.5 Jobs remain queued/running or queue age grows

**Contain first:** Stop low-priority admissions/auto-refresh; preserve queue and worker evidence; do not FLUSH Redis.

**Evidence:** queue depth/oldest age by class, worker heartbeat/busy job, job deadlines/attempts, Redis latency/memory/eviction, DB pool, external call spans, recent deploy.

**Hypothesis order**

1. No/live worker mismatch.
2. one slow transcript/API call without deadline.
3. head-of-line large export/metrics job.
4. worker crash/poison retry loop.
5. DB pool/lock exhaustion.
6. Redis connection/ACL/memory/persistence issue.
7. admission rate exceeds capacity.

**Safe response:** cancel/checkpoint only at safe points, scale a proven queue class, trip circuit/degraded mode, dead-letter poison job, restore worker with idempotency.

**Never do:** Start more consumers blindly when DB/provider is saturated; replay all failed jobs without idempotency/quota check.

### 15.6 Duplicate collection runs or snapshots appear

**Evidence:** submission times/actors/idempotency keys, scheduler leader/lease, request retries, lock owner/fencing, provider IDs, uniqueness conflicts.

**Hypothesis order:** double click; proxy/client retry; two schedulers; expired lock with stale worker; ambiguous acknowledgement; missing natural unique constraint; channel snapshot inside video loop.

**Containment:** Stop duplicate dispatch, preserve authoritative/duplicate runs, avoid deleting until downstream impact is understood.

**Proof:** deterministic two-process barrier and scheduler failover creates one logical run; historical dedupe uses an approved rule.

### 15.7 Web/API latency rises or 502/504 appears

**Contain first:** Shed optional exports/metrics/transcripts/auto-refresh; cap queue admission; preserve serving capacity.

**Evidence:** p50/p95/p99 by route, in-flight requests, Gunicorn workers/threads, CPU/RSS/FD, DB pool/locks/query plans, Redis/provider latency, response size, retry attempts, recent change.

**Hypothesis order**

1. Synchronous heavy request or unbounded query/response.
2. N+1/query plan/index regression.
3. DB pool/lock/long transaction.
4. nested retries/slow dependency.
5. browser polling amplification.
6. resource leak/limit/throttling.
7. proxy timeout or unsupported Socket.IO behavior.

**Proof:** reproduce at controlled concurrency and beyond rated capacity; verify recovery after load falls, not only steady-state success.

### 15.8 Redis/RQ connection errors or queue state looks corrupted

**Contain first:** If payload compromise is possible, isolate Redis and stop workers before they deserialize new jobs.

**Evidence:** Redis INFO/config/ACL audit safely, persistence state, memory/evictions, client identities, connection errors, unknown keys/jobs, container/network changes.

**Hypothesis order:** startup race/restart; bad rotated credential/ACL; memory/eviction; persistence loss; network partition; malicious/accidental command; incompatible queued payload.

**Never do:** FLUSHALL, CONFIG changes, restore old dump, or consume suspicious jobs before backup/evidence and impact review.

**Proof:** anonymous/least-role denial, restart/recovery, poison payload rejection, reconciliation from database authority.

### 15.9 Socket.IO progress is intermittent or wrong

**Evidence:** transport, session ID, worker/instance, sticky cookie/address, connect origin/auth user, room/job ID, event sequence, Redis Pub/Sub health.

**Hypothesis order:** unsupported multi-worker Gunicorn; missing sticky session; wildcard/bad origin; unauthorized room; reconnect missed/duplicated events; polling overlap; durable status disagreement.

**Containment:** Disable realtime transport and use bounded authorized durable polling; do not treat event stream as source of truth.

**Proof:** multi-instance load with connect/upgrade/reconnect/deploy drain and cross-user negative tests.

### 15.10 Database is locked, deadlocked, or connections are exhausted

**Evidence:** DB engine/dialect, pool checked-out/wait, active transactions, lock graph, query/transaction age, worker/web split, SQLite journal/foreign-key state.

**Hypothesis order:** SQLite concurrent writers; long export/metric transaction; N+1; leaked session; missing index; deadlock order; too many workers/retries.

**Containment:** Stop new heavy writes, cancel only proven safe long queries, preserve lock graph, reduce admission—not arbitrary DB restart.

**Proof:** targeted concurrency test, transaction duration/query/pool budgets, PostgreSQL integration.

### 15.11 Migration fails or schema drift returns

**Evidence:** exact target DB identity, pre/post Alembic version, applied DDL, transaction status, schema diff, backup/restore proof, running app versions.

**Decision**

- No durable operation applied: fix/retry on copy.
- Transaction rolled back fully: prove state then retry.
- Nontransactional/partial DDL: stop writers and build explicit roll-forward/recovery.
- Version marked but shape wrong: never assume stamp fixes; reconcile semantics.

**Proof:** blank + prior + legacy fixtures converge to same intended schema; interruption test and invariants.

### 15.12 Export fails, is huge, malformed, or unsafe

**Evidence:** dataset/version/filter/row counts, memory/temp disk, stage, checksum/manifest, sanitization version, client disconnect, cleanup state.

**Hypothesis order:** materialization/OOM; disk full; proxy timeout; malformed heterogeneous CSV; unsafe formula; encoding/newline/decimal/time; authorization expired; temp cleanup.

**Containment:** Disable suspect download, expire object, warn recipients if formula/private exposure is possible, clean through controlled reaper.

**Proof:** maximum-size background export and round-trip parser/spreadsheet corpus.

### 15.13 Metrics or rankings change unexpectedly

**Evidence:** active metric run, algorithm/config/code/parser versions, input collection/snapshot IDs, missingness/coverage/sample, repair/backfill events.

**Hypothesis order:** version mix; input freshness/change; parser change; missing-to-zero; age/cohort change; threshold change; duplicate rows; intentional repair.

**Containment:** Freeze promotion and customer claim; retain old run; label affected result unavailable/experimental.

**Proof:** reproduce both versions from immutable input, explain every delta, pass backtest/stability review.

### 15.14 A user cannot complete a workflow but automated tests pass

**Evidence:** user/role/device/browser/viewport/zoom/assistive technology, exact task path, keyboard/focus trace, network/server status, screenshots/video with private data removed.

**Hypothesis order:** pointer-only/custom semantics; unlabeled control/error; responsive clipping; record absent from latest-100 selector; lost form state; stale permission/session; auto-refresh race.

**Response:** Provide safe accessible workaround, reproduce with the user's input method, add state-specific browser/manual test.

**Never do:** Close issue because axe or unit tests pass.

### 15.15 Rights, ownership, or credential state looks contradictory

**Evidence:** exact current and historical versions, dependency timestamps, reviewer/actor, provider/secret state, ownership proof, concurrent jobs.

**Hypothesis order:** stale derived readiness; local-only revoke; missing ownership constraint; last-write-wins; duplicate record; UI terminology overclaim.

**Containment:** Block publication/sync/export claim, disable credential/job where safe, preserve evidence, verify external provider.

**Proof:** dependency mutation/invalidation, external revoke denial, cross-owner authorization and concurrency tests.

## 16. Required fault-injection and boundary-test matrix

Do not run destructive experiments against real customer/production data without an approved safe test plan, isolation, rollback, monitoring, and stop condition.

| Target | Injected fault / boundary | Required safe outcome |
|---|---|---|
| Authentication | Remove/malformed identity config | Production refuses startup or denies all protected access |
| Session | Rotate secret while old cookie exists | Old cookie rejected; user reauthenticates; no open fallback |
| Authorization | Change resource ID/role | 403 without existence/private-field leakage |
| CSRF | Missing/wrong/cross-session token and hostile Origin | 403; no state/job change |
| HTTP methods | Crawl/prefetch every GET | Zero writes and zero enqueued jobs |
| Input | Empty, null, whitespace, Unicode, max, one-over, many fields | Stable validation; no crash/resource amplification |
| URL | javascript/data/backslash/encoded/control/userinfo/protocol-relative | Rejected before storage/render |
| CSV/XLSX | = + - @ tab CR leading whitespace formulas | Text only after export/open |
| Count | 2,147,483,647; +1; >3B; negative; null | BIGINT valid where allowed; invalid domain rejected |
| Float/decimal | NaN, Infinity, rounding halves, max precision | Rejected or exact documented Decimal round trip |
| Batch save | Failure at first/middle/last row | Exact durable successes/failures, no phantom saved count |
| Commit | Kill after commit before status | Reconciled durable terminal state, no duplicate retry effect |
| Concurrency | Two identical collection submissions at barrier | One logical run/effect |
| Optimistic edit | Two users update same version | One success, one resolvable 409; no silent overwrite |
| PostgreSQL | Slow query, lock, deadlock, restart, credential rotate | Bounded error/retry where safe; no duplicate effect |
| SQLite | Concurrent write if supported | Behaves within documented mode or startup refuses topology |
| Migration | Blank/prior/legacy, interrupt every risky stage | Recover/roll forward; invariants preserved |
| Restore | Restore backup to isolated environment | Checksums, schema upgrade, sequences, row/invariants pass |
| Redis | Down/slow/restart/ACL deny/maxmemory/eviction | Readiness/job state honest; bounded reconnect; no lost authority |
| Queue | Poison payload, expired lease, worker kill, duplicate delivery | Reject/dead-letter/recover idempotently |
| Scheduler | Two leaders, clock skew, DST, missed run | One dispatch according to explicit policy |
| YouTube | 400/401/403 key/403 quota/404/429/5xx/timeout/DNS | Distinct typed state; bounded attempts; no empty success |
| YouTube batch | Partial/duplicate/missing IDs, repeated page token | Per-item accounting and bounded pagination |
| Transcript | IP block, unavailable, slow/hang, disabled | Typed optional failure, deadline, no queue starvation/error text as content |
| Retry | Dependency fails for full attempt window | Exact maximum attempts/deadline, jitter, no storm |
| Circuit breaker | Fail then recover | Opens at policy, limited half-open, returns healthy automatically |
| Socket.IO | Multi-instance upgrade/reconnect/deploy and guessed room | Correct durable resync; no unknown/cross-user event |
| Browser polling | Slow out-of-order responses and hidden tab | Newest state only; pause/backoff |
| Export | Maximum data, concurrent jobs, disconnect, disk full, kill | Bounded resources, failed state, cleanup, no partial publish |
| Metrics | Two versions, missing data, one-item cohort, unequal ages | One selected run; honest insufficient/missing/age state |
| Rights | Change license/link/attribution after ready | Ready invalidated with reason |
| OAuth | Provider revoke failure/secret deletion failure/concurrent sync | Pending/failed honest state; sync blocked safely |
| Health | DB/Redis slow/down, stale schema, CPU saturation | Liveness/readiness distinct; no restart cascade |
| Deployment | Canary failure and rollback with migrated schema | Rollout halts; compatible rollback/forward recovery |
| Capacity | Ramp beyond rated load then reduce | Controlled shedding/degradation and autonomous recovery |
| Resources | CPU/RAM/PID/FD/temp disk/DB pool exhaustion | Alerts, bounded failure, core health/control retained |
| Accessibility | Keyboard, screen reader, 400% zoom, forced colors, reduced motion | Core journeys complete and status/errors perceivable |
| Localization | Arabic/RTL, long text, locale decimals, multiple timezones | No layout/data parsing/order corruption |
| Privacy | Export/delete user/customer data | Authorized minimum export; verified lifecycle across stores |
| Telemetry | Synthetic secret/email/token/SQL content | Canary never reaches sink; correlation still works |

## 17. Debugging evidence and incident record template

Use one record per incident or high-risk failed verification:

    Incident or test ID:
    Start/end time and timezone:
    Severity and customer/data scope:
    Reporter and incident owner:
    Exact release commit/image/config hash:
    Alembic/database/Redis schema or state version:
    First bad and last known good time:
    Trigger/recent changes:
    Request/job/collection/metric/export correlation IDs:
    Observable symptoms and SLO impact:
    Containment actions and authorization:
    Evidence preserved and access location:
    Hypotheses considered:
    Experiments and results, including negative results:
    Root/probable cause:
    Durable data impact and reconciliation:
    Security/privacy/rights impact:
    Recovery and customer communication:
    Fix, tests, and tracker tasks reopened/completed:
    Residual risk and follow-up owners/dates:
    Postmortem review:

Evidence must be safe: use IDs, counts, hashes, status codes, timings, redacted structures, and synthetic examples. Do not embed API keys, cookies, tokens, database passwords, private analytics rows, transcripts, emails, or full customer exports.

## 18. Stop-ship and emergency containment conditions

### 18.1 Automatic stop-ship

Do not expose or continue rollout when any of these is unresolved:

- Authentication can fail open or any protected route/event/object is anonymously/cross-role accessible.
- A weak/default/exposed production secret remains valid.
- Any state-changing browser route lacks required CSRF/user-intent protection or a GET mutates state.
- Reported saved/completed counts can differ from committed data.
- An upstream failure can become successful empty data.
- A supported database cannot migrate/recover non-destructively or schema drift is present.
- Redis/queue can be reached anonymously/unrestricted or untrusted payload can reach a worker.
- Critical/High dependency/container/secret/SAST/DAST/pentest finding lacks approved bounded exception.
- Private analytics/credential data can leak through UI, log, cache, event, or export.
- Production topology is known unsupported and causes correctness/security failure.
- Core customer journey fails keyboard/screen-reader/reflow requirements with no accessible equivalent.
- Customer-facing metric mixes versions, treats missing as zero materially, or makes unvalidated opportunity claims.
- Backup restore, release rollback/forward recovery, liveness/readiness, or incident ownership is unproven.

### 18.2 Emergency feature containment

Prefer the narrowest action that stops harm:

- Switch collection/export/metrics/owned analytics/rights publication to disabled or read-only.
- Pause scheduler and new queue admissions while allowing safe status/read access.
- Disable transcript collection independently from metadata collection.
- Fall back from Socket.IO to authorized bounded durable polling.
- Restrict ingress to operator/private network.
- Revoke/rotate one compromised credential and disable dependent jobs.
- Shed optional work and reject excess requests with retry guidance.
- Keep evidence and customer-visible status; do not silently pretend normal service.

## 19. Pre-release, launch, and first-72-hour watchlist

### 19.1 Before release

- [ ] Exact artifact digest, source commit, lock hashes, migration head, configuration hash, and SBOM are recorded.
- [ ] All affected tracker tasks and dependent tasks were revalidated on the release candidate.
- [ ] Fresh/prior/legacy migrations, backup restore, and invariant/reconciliation reports pass.
- [ ] Auth/authorization/CSRF/headers/cache/secret/Redis/network negative suites pass.
- [ ] PostgreSQL/Redis/RQ/scheduler/Socket.IO integration and fault tests pass.
- [ ] Load/spike/soak and recovery-after-overload meet SLO/capacity headroom.
- [ ] Accessibility manual/automated critical journeys pass.
- [ ] Metric version/lineage/backtest and product-claim review pass.
- [ ] Canary, rollback/forward recovery, feature-disable, and incident/runbook owners are ready.
- [ ] No secret/private data is present in diff, image, fixtures, logs, or release artifacts.

### 19.2 Canary

- [ ] Start with a small representative slice and no simultaneous unrelated migration/config/dependency upgrade.
- [ ] Compare error, latency, saturation, queue, DB, Redis, quota, collection completeness, data invariants, and business outcomes with baseline.
- [ ] Verify new and old versions agree where compatibility is required.
- [ ] Exercise a real but controlled collect/job/export/rights/analytics flow and inspect durable state.
- [ ] Halt automatically/manually on SLO burn, invariant mismatch, auth leak, data discrepancy, or unexplained metric shift.

### 19.3 First 72 hours

Watch at minimum:

- Anonymous/403/401 and privileged-action patterns.
- Session/login/CSRF/rate-limit errors.
- Request p95/p99, 5xx/429/502/504, worker utilization, restarts.
- Queue depth/oldest age/runtime/retry/dead-letter/cancel.
- DB pool/locks/slow queries/deadlocks/row-count invariants/storage growth.
- Redis latency/memory/eviction/persistence/reconnect/ACL denial.
- Provider attempts/status/quota/reservations/completed-empty rate.
- Discovered versus returned versus committed per-item counts.
- Duplicate job/snapshot/natural-key conflict rate.
- Export size/runtime/temp disk/formula-sanitizer/version/download denial.
- Metric run version/coverage/insufficient/missing rate and ranking delta.
- Browser CSP violations, JS errors, polling/realtime reconnect failures.
- Accessibility/support reports and lost-form/job confusion.
- Private data/log scrubber canaries.
- Backup success plus a scheduled post-release restore check.

Do not interpret the absence of support tickets as proof. Low adoption can hide defects. Use synthetic checks, invariants, fault signals, and direct design-partner observation.

## 20. Postmortem and prevention standard

Write a blameless postmortem for every SEV-0/SEV-1, durable data discrepancy, security/privacy/rights event, failed migration/restore, repeated incident, or near miss that could have caused major harm.

The postmortem must:

1. State customer/data/security impact without minimizing uncertainty.
2. Provide a time-ordered timeline in one timezone.
3. Separate trigger, contributing conditions, detection gaps, response gaps, and root/probable cause.
4. Explain why existing tests, monitoring, review, and checklist controls did not prevent/detect it.
5. Record what went well, what failed, and negative experiments.
6. Include durable-data reconciliation and customer notification decisions.
7. Assign prevention, detection, mitigation, and process actions with owners/dates.
8. Add regression/fault tests and update this playbook/tracker when a new failure class is learned.
9. Verify actions later; closing the document is not closing the risk.

## 21. Codex pre-mortem prompt for each remediation task

Use this before Codex edits a tracker item:

    Read the selected task in the production-readiness remediation checklist,
    its source audit finding, and every relevant failure mode in this playbook.

    Before editing, produce a concise pre-mortem:
    1. root cause and current reproduction,
    2. trust/data/transaction/dependency boundaries touched,
    3. ways the proposed fix could fail or regress another completed control,
    4. positive, negative, boundary, concurrency, interruption, recovery,
       accessibility, and fault-injection tests required,
    5. migration/data reconciliation and rollback or forward-recovery plan,
    6. observability and safe evidence,
    7. explicit actions that require my authorization.

    Implement only after the plan is consistent with the task dependencies.
    Never mark a risk controlled because code exists; prove the required behavior.
    If proof requires a human, external provider, real credential, penetration test,
    assistive technology, production-like load, or authorized data operation, leave
    the criterion unchecked and state the blocker.

## 22. Final operating principle

The most dangerous failure is not a visible 500. It is a fast, polished, apparently successful workflow that silently opens private data, drops committed work, records dependency failure as valid data, preserves a stale rights approval, or produces an unjustified confident recommendation.

Optimize remediation and operations for truthful state:

- Fail closed for security.
- Fail explicitly for dependencies.
- Commit atomically and count durable outcomes.
- Degrade safely under overload.
- Preserve missingness, lineage, and uncertainty.
- Keep every essential workflow accessible.
- Make changes reversible or safely forward-recoverable.
- Correlate evidence without leaking data.
- Reopen completed work when later evidence disproves it.

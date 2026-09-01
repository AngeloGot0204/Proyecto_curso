# Verify Report: sincronizacion-numero-registro

## Change
sincronizacion-numero-registro (backlog #10). Delivered across 3 merged PRs on main (#29 server idempotency, #30 upload queue, #31 nuevo-reporte.js infra).

## Mode
Full artifact set (proposal, design, both specs, tasks). Full verification performed: completeness, correctness, coherence, plus real test execution.

## Task Completeness

| Phase | Status |
|---|---|
| 1. Server Migration | All checked, verified. Migration applies/reverses cleanly, matches design D1/D2/D8 |
| 2. Server Idempotency (TDD) | All checked, verified. 12 tests in test_idempotencia.py, all pass |
| 3. Upload Queue (Dexie + fetch) | All checked. Code matches design; no automated JS coverage exists (documented project limitation) |
| 4. Manual Verification | 4.2, 4.4, 4.5 checked with production evidence; 4.1, 4.3, 4.6 unchecked, genuinely unverified |
| 5. nuevo-reporte.js | All checked. Matches D7 exactly |
| 6. Cleanup | All checked |

The unchecked state of 4.1/4.3/4.6 is an honest reflection of what was and was not run. tasks.md does not claim verification it does not have. The rationale offered for treating them as effectively covered is weaker than presented (see CRITICAL finding below).

## Test Execution Evidence

- Full suite run in isolation (no concurrent DB contention): 269 passed, 0 failed, exit 0 (604.90s).
- reportes/ subset run: 128 passed, exit 0.
- An earlier run launched concurrently with another test process produced 7 spurious deadlock-detected failures in unrelated tests (tipos_reporte_tipodereporte_codigo_key), caused by two simultaneous pytest invocations hitting the same live Postgres test DB, not a code defect. Re-run in isolation confirmed 269/269 green, matching the previously reported no-regressions claim.

## Spec Compliance Matrix

### reporte-idempotent-creation

| Requirement / Scenario | Status | Evidence |
|---|---|---|
| Client-Generated Local Identifier | PASS, stale text | id_local UUIDField unique=True (models.py); DB rejects duplicates (test_id_local_unico_a_nivel_bd). WARNING: scenario text still says the UUID is generated in paso-offline.js. Design D7 moved this responsibility to nuevo-reporte.js (unreferenced, forward-looking). Spec file was not updated after the design deviation. |
| Sequence-based numero_registro, first creation | PASS | test_create_asigna_numero_registro_sin_refresh proves RETURNING without refresh_from_db() |
| Two distinct drafts get distinct sequential numbers | PASS | test_numero_registro_avanza_por_secuencia (strict greater-than) |
| Idempotent iniciar_reporte, retried POST | PASS | test_post_nuevo_repetido_mismo_id_local_no_duplica, exact match to scenario |
| Concurrent identical retries do not duplicate | WARNING, no dedicated test | No thread/process-level concurrency test exists. Verified only by source inspection: Django 5.2 get_or_create re-runs get(lookup) (same id_local plus creador) on IntegrityError before re-raising, so a genuine same-user race is absorbed inside the ORM and never reaches the views own except IntegrityError block, which therefore only fires for a different creador (design D3 hostile-reuse case, correctly tested). Plausible and framework-consistent, but a passing covering test does not exist for this exact scenario; task 4.6 (double-click under Slow 3G, the nearest manual proxy) is also unchecked. |

### upload-queue

| Requirement / Scenario | Status | Evidence |
|---|---|---|
| Fetch-Based Step Submission, successful step submission | CRITICAL, unverified | Task 4.1 (basic fetch submit path: single fetch POST, then GET of next step, Dexie row cleared) was never run, automated or manual. The apply-progress justification (implicitly covered by 4.2 success branch and Python view tests) does not hold: 4.2 exercises the offline-then-reconnect-then-retry path, not a first-attempt clean success, and the Python tests never execute browser JS at all. This is the single most fundamental scenario of the entire upload-queue rewrite and has zero direct evidence it works as coded. |
| Visible Pending/Failed State, network failure marks pending | PASS | Task 4.2 verified live in production (banner and intentos counter) |
| No silent retry | PASS by code inspection | No setInterval or background-sync code path exists; consistent with ADR-0004 |
| Manual Retry Affordance, retry succeeds/fails | PARTIAL | Retry-while-offline and retry-after-reconnect verified (4.2); retry-after-server-down-then-restart (task 4.3, the fallo state distinct from sesion_expirada) is unverified |
| Draft Survives Session Expiry | PASS | Task 4.4 verified live in production |
| Resubmission after re-login is idempotent | PASS | Server half proven by test_sesion_expirada_no_rompe_idempotencia; client half by task 4.4 |

## Design Coherence (D1-D8)

| Decision | Implemented as designed |
|---|---|
| D1, numero_registro via db_default plus RunSQL sequence | Yes, exact match, migration and model identical |
| D2, id_local UUIDField DB default | Yes, exact match |
| D3, idempotency scope (id_local, creador), global uniqueness | Yes, view code matches Interfaces/Contracts verbatim |
| D4, fetch-based submit | Yes, credentials same-origin, redirect follow as specified |
| D5, shared Dexie schema module | Yes, offline-db.js is the sole .version() owner, loaded before paso-offline.js in paso.html (script order confirmed) |
| D6, per-step retry banner | Yes, insertAdjacentElement beforebegin mirrors the number 9 restore prompt |
| D7, nuevo-reporte.js with no host page | Yes, confirmed no template references data-nuevo-reporte; script no-ops correctly |
| D8, migration ordering | Yes, RunSQL sequence precedes both AddField operations |

No design deviations found beyond the proposal-vs-design divergence noted below. That divergence is normal SDD flow (design supersedes proposal), not a defect.

## Correctness Issues Found (source inspection)

- No functional bugs found in models.py, views.py::iniciar_reporte, offline-db.js, nuevo-reporte.js, or the migration. Field declarations in models.py match the migrations AddField operations exactly, required for Django migration-state consistency, verified.
- paso-offline.js manejarRespuesta hard-codes urlFinal.pathname checked against /login/ to detect session expiry. This works only because the projects LOGIN_URL setting is literally /login/; if that setting ever changes, this check silently stops detecting session expiry (the draft would be marked as a generic HTTP/network failure instead). Not a defect today; SUGGESTION to derive this from a data attribute instead of a hard-coded literal, for future-proofing.
- proposal.md Success Criteria checklist (4 items) remains all-unchecked even though the change is fully delivered and tested. SUGGESTION: check them off before archive for artifact hygiene.

## Issues Summary

CRITICAL
1. Task 4.1 (basic successful fetch-submit path) was never verified, automated or manually, despite being the primary happy-path scenario of the entire upload-queue capability core requirement (Fetch-Based Step Submission). The stated justification for treating it as covered does not actually exercise the same code path.

WARNING
1. Task 4.3 (fallo state via stopped/restarted server, distinct from the sesion_expirada fallo path already verified in 4.4) is unverified.
2. Task 4.6 (double-click race under Slow 3G) and the corresponding spec scenario Concurrent identical retries do not duplicate have no dedicated test; coverage rests on source-level reasoning about Django internal get_or_create retry behavior, not a runtime reproduction.
3. reporte-idempotent-creation specs Client-Generated Local Identifier scenario still says id_local is generated in paso-offline.js; the actual, correctly-implemented owner is nuevo-reporte.js per design D7. Spec text was not updated to reflect the design supersession.

SUGGESTION
1. paso-offline.js session-expiry detection hard-codes /login/; consider deriving it from a template-rendered attribute.
2. Check off proposal.md Success Criteria before archiving.

## Verdict

PASS WITH WARNINGS

All server-side (Python/Postgres) requirements are implemented exactly as designed and are fully proven by 269 passing tests with no regressions. The client-side upload-queue rework is implemented consistently with the design and partially verified in production, but one CRITICAL gap remains: the primary happy-path fetch-submission scenario (task 4.1) has never actually been exercised, automated or manually. It is inferred, not observed. This does not undermine the server-side correctness, but it means the core rewritten submit path of paso-offline.js has no direct evidence of working end-to-end in a browser.

Recommendation: run task 4.1 manual DevTools check before sdd-archive. If it passes, this becomes a clean PASS. If the user prefers to accept the risk and archive now, that is a valid call the user can make explicitly, but it should not be silently absorbed into already verified.

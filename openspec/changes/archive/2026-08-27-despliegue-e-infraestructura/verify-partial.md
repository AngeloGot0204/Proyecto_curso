# Partial Verification Report: Deployment and Production Infrastructure (backlog #2)

> Engram: `sdd/despliegue-e-infraestructura/verify-report-partial` (observation 58)
>
> **This is a partial verification, scoped to the code half only.** The
> infrastructure half is not deployed yet, so a full verify is not possible.
> A distinct, later report will cover the full change once the manual
> phases run.

**Verification Date**: 2026-08-26

## Status
**PARTIAL** -- Code implementation: PASS WITH WARNINGS. Tasks artifact: 1
CRITICAL documentation defect found. Manual/infrastructure scope: NOT
VERIFIED (0/12 scenarios attempted, correctly -- nothing is deployed).

## Why this verification exists

The `sdd-apply` agent was terminated mid-run by an API session limit before
it reported its TDD sequence. The orchestrator finished the remaining work
and committed it. Result: all 35 tests pass, but nobody witnessed a single
one of them fail. This report independently re-derives RED evidence for
every automatable scenario by reasoning against the parent commit `1b9fa85`
(predates the settings change), rather than accepting the green suite as
proof.

## Commands actually run (real output, this session)

| Command | Result | Exit |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | `35 passed` (~31-34s) | 0 |
| `.venv/Scripts/python.exe -m pytest config/tests/ -v` | 18 passed, individually listed | 0 |
| `.venv/Scripts/python.exe manage.py check` | `System check identified no issues (0 silenced).` | 0 |
| `.venv/Scripts/python.exe manage.py check --deploy --fail-level WARNING` under a synthetic PROD_ENV-shaped environment | `System check identified no issues (1 silenced).` -- the 1 silenced is the deliberate W021 | 0 |
| `.venv/Scripts/python.exe manage.py check --deploy` (no `--fail-level`, same env) | Same: 0 issues, 1 silenced | 0 |
| `.venv/Scripts/python.exe manage.py check` with `DJANGO_HTTPS_ONLY=true` (lowercase) injected via shell env | `ImproperlyConfigured: DJANGO_HTTPS_ONLY must be exactly 'True' or 'False', got 'true'` | 1 |
| `git ls-files .env` | empty | -- |
| `git log --all --oneline -- .env` | empty (never committed, any branch) | -- |
| `git log --oneline -- .env.example` | `12ed1a5`, `602afbc` only | -- |
| `git diff 1b9fa85 12ed1a5 -- config/settings.py` | full diff read, used to re-derive RED status | -- |
| `git grep -n "neon.tech" / "postgresql://"` | only placeholder/synthetic strings -- no real hostname or credential | -- |
| Read `.env.example` directly | **blocked** by sandbox dotfile permission (same restriction three prior agents hit -- not worked around) | -- |

## Independent per-test RED classification (the reason this run exists)

Design (#53) predicted: genuine behavioral = A3, A8, A12, A13; weak
name-absence = A1, A2, A4, A5, A10, A11, A14; vacuous regression guards =
A6, A7, A9.

| Design ID | Test function(s) | Design's prediction | Independent finding | Method | Match? |
|---|---|---|---|---|---|
| A1 | `test_a1_static_root_set_no_whitenoise` | Weak name-absence | Confirmed weak -- parent has no `STATIC_ROOT` at all (`AttributeError`) | Analytical (diff) | Yes |
| A2 | `test_a2_conn_max_age_is_zero` | Weak name-absence | Confirmed weak -- parent's `DATABASES["default"]` has no `CONN_MAX_AGE` key (`KeyError`) | Analytical (diff) | Yes |
| A3 | `test_a3_missing_allowed_hosts_fails_loud` | Genuine behavioral | Confirmed genuine -- parent `ALLOWED_HOSTS` always defaults (`os.environ.get(..., "localhost,127.0.0.1")`), never raises; "DID NOT RAISE" against parent | Analytical (diff, verbatim old line read) | Yes |
| A4 | `test_a4_csrf_trusted_origins_from_env_default_empty` | Weak name-absence | Confirmed weak -- no `CSRF_TRUSTED_ORIGINS` attribute in parent (`AttributeError`) | Analytical (diff) | Yes |
| A5 | `test_a5_secure_proxy_ssl_header_exact_tuple` | Weak name-absence | Confirmed weak -- test's own docstring says presence-only, cannot prove behavior | Analytical (diff) | Yes |
| A8 (settings) | `test_a8_debug_is_false_under_prod_env` | Not separately discussed by design | **Divergence -- weaker than labelled.** `DEBUG` default logic is UNCHANGED by this diff (predates the change, from item #1). Under `PROD_ENV`, `DEBUG is False` was already true against the parent commit. This is a **vacuous regression guard**, same category as A6/A7/A9 -- mislabeled in-file as "Weak name-absence RED" | Analytical (diff) | **No** |
| A8 (check --deploy) | `test_a8_check_deploy_clean_at_warning_level` | Genuine behavioral, upgraded by D11 | Confirmed genuine, **and empirically verified this session**: 0 issues / 1 silenced under a synthetic PROD_ENV-shaped environment against current settings.py. Against the parent (analytical, no mutation performed): W004/W008/W012/W016 would all fire at WARNING, making `--fail-level WARNING` nonzero | Empirical (current) + analytical (parent) | Yes |
| A6 | `test_a6_no_build_step_or_code_runs_migrate` | Vacuous, no RED | Confirmed vacuous -- true both before and after | Analytical | Yes |
| A7 | `test_a7_no_code_consumes_blob_token` | Vacuous, no RED | Confirmed vacuous -- no Blob code in either commit | Analytical | Yes |
| A9 | `test_a9_env_ignored_and_example_has_no_real_secrets` | Vacuous, no RED | Confirmed vacuous -- `.gitignore`/placeholder property held before and after | Analytical | Yes |
| A10 | `test_a10_https_only_true_hardens_transport` | Weak name-absence | Confirmed weak -- probe executes settings.py raw (no Django global-settings merge); names simply absent in parent | Analytical (diff + conftest.py mechanism) | Yes |
| A11 | `test_a11_https_only_false_disables_transport_hardening` | Weak name-absence | Confirmed weak, same mechanism as A10 -- correctly the most valuable of the weak group (guards local dev) | Analytical | Yes |
| A12 | `test_a12_missing_https_only_fails_loud` | Genuine behavioral | Confirmed genuine -- parent never references `DJANGO_HTTPS_ONLY`; loads cleanly; "DID NOT RAISE" against parent | Analytical (diff) | Yes |
| A13 | `test_a13_malformed_https_only_is_rejected` (x4: "true","1","yes","") | Genuine behavioral, strongest test | Confirmed genuine, **and independently empirically verified**: live run with `DJANGO_HTTPS_ONLY=true` against current settings.py -> real `ImproperlyConfigured` traceback, exit 1. Parent: no validation exists, "DID NOT RAISE" for every case | Empirical (current) + analytical (parent) | Yes |
| A14 | `test_a14_hsts_preload_refused_and_silenced` | Weak name-absence | Confirmed weak -- neither name exists in parent (`AttributeError`) | Analytical (diff) | Yes |

**Summary**: 13/14 design test IDs match the design's own prediction exactly.
**One divergence**: `test_a8_debug_is_false_under_prod_env` is actually
vacuous (pre-existing behavior, unchanged by this diff), not weak
name-absence RED as its own docstring claims.

## Also checked, per the explicit request list

1. **`SECURE_PROXY_SSL_HEADER` / `CSRF_TRUSTED_ORIGINS` pair** -- implementation
   matches design exactly (settings.py:58-66). Confirmed no test claims to
   prove runtime `is_secure()` behavior; A5's own docstring says
   presence-only. Runtime behavior remains genuinely unverified pending
   ML-4/ML-6 (out of scope here).
2. **A8's tightening to `--fail-level WARNING`** -- run myself this session
   under a production-like environment: **0 issues, 1 silenced (W021,
   deliberate)**. This is the written artifact task 4.1 lacked.
3. **`SILENCED_SYSTEM_CHECKS = ["security.W021"]`** -- confirmed it silences
   only that one check (settings.py:87); `SECURE_HSTS_PRELOAD = False` is
   unconditional (settings.py:81); `test_a14` pins both together, so a
   future contributor cannot "fix" W021 by flipping preload on.
4. **`require_bool_env`** -- confirmed via a live subprocess run this session
   (not just reading source) that it genuinely rejects `"true"` (lowercase)
   with the exact documented message and exit 1. `test_a13`'s 4 parametrized
   cases additionally prove rejection of `"1"`, `"yes"`, `""`.
5. **Tasks 7.2/7.3 discrepancy -- CONFIRMED as a real defect.** Design
   Decision 9's matrix requires `DJANGO_SECRET_KEY` for Preview and
   Development, and `DATABASE_URL` for Development. Task 7.2 omits
   `DJANGO_SECRET_KEY` entirely; task 7.3 omits both `DJANGO_SECRET_KEY` and
   `DATABASE_URL`. Since both are `require_env()`-enforced at import time,
   following tasks.md literally would crash the Preview/Development
   deployment (including the build). **CRITICAL, against the tasks
   artifact.** Not yet executed -- no live damage -- but must be fixed before
   Phase 7 runs.
6. **Secrets** -- `.env` untracked, never committed in any history
   (`git ls-files`/`git log --all` both empty). No real secret or database
   hostname in any tracked file (`git grep` confirms only placeholders and
   synthetic test fixtures). `.env.example` itself could not be read
   directly this session (sandbox dotfile restriction, not worked around).

## TDD Compliance (Strict TDD module)

| Check | Result | Details |
|---|---|---|
| TDD Evidence reported | Partial | apply-progress (#57) is transparent about the interruption; no contemporaneous per-test RED/GREEN table exists. This report is the first RED evidence produced. |
| All tasks have tests | Yes | 14/14 automatable scenarios covered (18 test functions after A8 split + A13 parametrization) |
| RED confirmed (re-derived) | Yes | 14/14 design IDs re-derived; 13/14 match design's classification, 1 labelling divergence |
| GREEN confirmed (tests pass) | Yes | 35/35 pass this session (18 new + 17 pre-existing) |
| Triangulation adequate | Yes | A13 x4 params; A10/A11 true/false pair; A8 split into 2 checks (one mislabeled) |
| Safety Net for modified files | Yes | `config/settings.py` modified; full 17-test `usuarios` suite re-run green in the same session |

**TDD Compliance**: 5/6 fully passed, 1 partial.

## Test Layer Distribution

| Layer | Tests | Files |
|---|---|---|
| Unit (settings-value, fresh-module probe) | 15 | `test_deployment_settings.py` |
| Integration (real subprocess against `manage.py`) | 1 | `test_deployment_settings.py` |
| Static/text-scanning | 3 | `test_deployment_hygiene.py` |
| **Total** | **18** (14 design scenario IDs) | 2 files |

## Assertion Quality

No CRITICAL patterns (no tautologies, no assertions bypassing production
code, no live ghost-loop risk). **0 CRITICAL, 1 WARNING** (A8/debug sub-test
misclassification, a labelling-honesty issue, not a technical defect).

## Item #1 Regression

17 pre-existing `usuarios` tests re-run in this session's 35-passed run, all
green -- the transport-hardening change does not turn any existing request
into a 301, matching design 11.5/A11.

## Findings

### CRITICAL
1. **`05-tasks.md` Phase 7 (7.2, 7.3): missing `DJANGO_SECRET_KEY` for
   Preview, missing `DJANGO_SECRET_KEY`/`DATABASE_URL` for Development.**
   Contradicts design Decision 9's matrix. Would crash Preview/Development
   deployments if followed literally. Not yet executed. Fix before Phase 7.

### WARNING
1. Task 2.4 was left unchecked (apply agent terminated). This run
   independently re-derived RED status for all 14 scenario IDs and confirms
   the design's classification for 13/14. Recommend closing 2.4 citing this
   report.
2. `test_a8_debug_is_false_under_prod_env` is mislabeled -- its docstring
   claims "Weak name-absence RED" but the assertion predates this change
   entirely (item #1, unchanged). It is a vacuous regression guard, same
   category as A6/A7/A9. Functionally harmless; the label is wrong.
3. Runtime HTTPS/proxy behavior (`SECURE_PROXY_SSL_HEADER`) remains entirely
   unverified -- correctly so. This is the single highest-blast-radius line
   in the change (a wrong value now causes a redirect loop, not just a
   403). Only ML-4/ML-6 against a live deployment can prove it.

### SUGGESTION
1. `test_a6`/`test_a7` loop assertions rely on `config/`/`usuarios/` being
   non-empty; true today but not self-documented. An explicit non-empty
   guard would make the safety property structural rather than incidental.
2. Budget: 424 lines against 400, accepted as `size:exception` (Engram #56,
   settled). Both delivered changes in this project now exceed the 400-line
   budget -- worth a standalone convention decision, independent of this run.

## Spec/Design Correctness (code half only)

- All 14 Automatable scenarios have a passing covering test at runtime.
- Design decisions D1-D11 checked line-by-line against the actual diff: all
  match.
- No non-goal leaked into the diff (no settings split, no HSTS preload, no
  year-long HSTS, no `require_bool_env` retrofit onto `DJANGO_DEBUG`).
- Manual scenarios (12 total: ML-1..6, MC-1..6): **0/12 verified**, correctly
  reported as NOT VERIFIED, not compliant, not assumed.

## Budget statement (not re-opened, restated for completeness)

424 insertions against a 400-line review budget, accepted as `size:exception`
under the settled `exception-ok` delivery strategy (Engram #56). **Not**
reported as delivered within budget.

## Next steps

1. Fix `05-tasks.md` Phase 7 (7.2, 7.3) -- missing env vars -- before the user
   runs it.
2. Correct `test_a8_debug_is_false_under_prod_env`'s docstring classification
   (cosmetic).
3. Close task 2.4 citing this report, or leave open with a cross-reference --
   orchestrator/user decision.
4. A full verify can only run after Phases 1, 7, 8, 9, 10 are executed live
   by the user. Do not archive the infrastructure half until then.

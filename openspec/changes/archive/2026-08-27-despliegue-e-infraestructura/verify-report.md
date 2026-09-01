# Verification Report: Deployment and Production Infrastructure (backlog #2)

> Engram: `sdd/despliegue-e-infraestructura/verify-report`
>
> Supersedes the code-half-only [06-verify-partial.md](06-verify-partial.md)
> (Engram #58). This is the FULL verify: Phases 1, 7, 8, 9, 10 of
> [05-tasks.md](05-tasks.md) are now complete (manual infrastructure
> provisioning, env var matrix, migration, and the 12-point acceptance
> checklist), in addition to the code half verified previously.

## Scope

All 12 requirements / 26 scenarios of spec revision 2 (Engram #52):
Automatable 14, Manual (live) 6, Manual (console) 6.

## Verdict

PASS WITH WARNINGS -- 1 CRITICAL open, blocking a clean archive.

- Code half: PASS (re-confirmed, 35/35 tests, manage.py check clean).
- Manual/live half: PASS, with 2 scenarios PASS-with-note (partial manual
  coverage, backed by an existing automated test) and 1 CRITICAL -- the spec
  text itself is now stale/contradicted by a legitimate, evidence-driven
  design pivot that was never fed back into 03-spec.md.
- The tasks 7.2/7.3 CRITICAL from the partial verify (Engram #58) is
  confirmed resolved in the current 05-tasks.md.
- Do not archive until the CRITICAL below (spec text vs. WhiteNoise
  implementation) is either amended in 03-spec.md or explicitly accepted
  as a documented exception, the same way the 424-line budget overrun was
  accepted (Engram #56).

## Commands re-run this session (real output, real exit codes)

| Command | Result | Exit |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `35 passed, 6 warnings in 31.96s` | 0 |
| `.venv\Scripts\python.exe manage.py check` | `System check identified no issues (0 silenced).` | 0 |
| `git log --oneline -8` | confirms all 6 session commits present in order (see below) | -- |
| `curl` to `https://proyecto-curso-seven.vercel.app/login` | `200 https://proyecto-curso-seven.vercel.app/login/` (301->200 normalization, no loop) | -- |
| `curl -sI https://proyecto-curso-seven.vercel.app/static/admin/css/base.css` | `200`, `Content-Type: text/css; charset="utf-8"` | -- |
| `curl -sI https://proyecto-curso-seven.vercel.app/login/` | `Strict-Transport-Security: max-age=3600; includeSubDomains` (no preload); `Set-Cookie: csrftoken=...; Secure` | -- |
| `curl` to `https://proyecto-curso-seven.vercel.app/admin/` | `302 -> /admin/login/?next=/admin/` (see note under ML-5) | -- |

These four curl checks are independently re-run by this verify pass
against the live Production URL, not merely re-stated from the session
narrative -- ML-1, ML-2, and part of ML-6 now carry fresh, first-party
evidence, not only user-reported evidence.

## Session commits verified present (git log)

| Commit | Purpose |
|---|---|
| `12ed1a5` | Settings + deployment test suite (verified in the partial verify) |
| `0b89864` | TDD classification label fix (verified in the partial verify) |
| `c291fe1` | Declare Vercel Python entrypoint (pyproject.toml [tool.vercel]) |
| `6a62efd` | Declare project dependencies for Vercel uv build ([project] table) |
| `976f8bc` | vercel.json attempt 1 -- outputDirectory (failed empirically) |
| `26f3505` | vercel.json attempt 2 -- path fix (failed empirically) |
| `356f8e6` | WhiteNoise -- supersedes design Decision 5 |
| `9c5bf85` | Trivial commit on prueba-preview to trigger the MC-4 Preview check |

## A. Tasks 7.2/7.3 CRITICAL (Engram #58) -- CONFIRMED RESOLVED

Read `docs/sdd/despliegue-e-infraestructura/05-tasks.md` directly, lines
276-311. Task 7.2 (Preview) now lists DJANGO_SECRET_KEY, DATABASE_URL,
DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, DJANGO_HTTPS_ONLY. Task
7.3 (Development) now lists DJANGO_SECRET_KEY, DATABASE_URL,
DJANGO_ALLOWED_HOSTS, DJANGO_HTTPS_ONLY, DJANGO_DEBUG. An explicit
correction note (lines 305-311) documents the fix and attributes it to
Engram #58. Closed, no further action.

## B. Design divergence #1 -- Vercel auto-entrypoint detection: FALSE (empirically)

Design Decision 5 assumed Vercel would auto-detect the WSGI entrypoint from
WSGI_APPLICATION. Empirically false: build failed with "No python
entrypoint found." Fix: pyproject.toml `[tool.vercel] entrypoint =
"config.wsgi:application"` (commit `c291fe1`). This activated Vercel's uv
build flow, which additionally requires an explicit [project] table with
dependencies -- without it the build "succeeds" but never installs Django
(commit `6a62efd`). [project].dependencies now duplicates
requirements.txt verbatim (5 packages, including whitenoise).

Classification: WARNING (design deviation, does not contradict spec
text). No spec requirement asserts anything about entrypoint
auto-detection; this is a design-level implementation detail. The drift
risk is real and worth a SUGGESTION (below) but not spec-breaking.

## C. Design divergence #2 -- Vercel auto-collectstatic/static hosting: FALSE (empirically), and this ONE breaks spec text -- CRITICAL

Design Decision 5 also assumed that setting STATIC_ROOT would let Vercel's
build-time collectstatic be served automatically by Vercel's static
hosting/CDN, with no WhiteNoise, no vercel.json. Two attempts to make
this work as designed both failed empirically, with build/runtime log
evidence:

- Attempt 1 (`976f8bc`, vercel.json with outputDirectory): collectstatic
  ran, 127 files collected, but every /static/... request still hit the
  Django WSGI function and returned Django's own 404 -- never intercepted by
  Vercel's static hosting.
- Attempt 2 (`26f3505`, path fix): same empirical failure.

Both were abandoned. The real fix (`356f8e6`) adds
whitenoise.middleware.WhiteNoiseMiddleware (after SecurityMiddleware),
STORAGES["staticfiles"]["BACKEND"] =
"whitenoise.storage.CompressedStaticFilesStorage", and
whitenoise>=6.7,<7 in both requirements.txt and pyproject.toml.
vercel.json was simplified to only `{"buildCommand": "python manage.py
collectstatic --noinput"}`.

This directly contradicts the literal spec text. 03-spec.md /
Engram #52 currently states, under "Requirement: Static file serving
without WhiteNoise": STATIC_ROOT MUST be set so Vercel's build-time
collectstatic serves static assets; no WhiteNoise or static storage
backend. Its Automatable scenario says no WhiteNoise middleware/STORAGES
override present. Its Manual (live) scenario says 200 with expected
content type, served by Vercel CDN not a 404.

Both scenarios are now literally false as written:
- `config/tests/test_deployment_settings.py::test_a1_static_root_set_whitenoise_serves_it`
  (renamed from test_a1_static_root_set_no_whitenoise) now asserts
  whitenoise IS present in MIDDLEWARE and STORAGES["staticfiles"] IS
  the WhiteNoise backend -- the exact opposite of the requirement text. It
  passes (verified: 35/35 green), but it proves the requirement wrong, not
  right.
- The live curl re-check this session (`curl -sI
  .../static/admin/css/base.css` -> 200, content-type: text/css) is
  correct on the observable (200, right content type) but the causal
  claim "served by Vercel CDN not a 404" is false -- it is served by
  WhiteNoise from inside the WSGI function, which the design/spec
  explicitly ruled out.

Per this skill's own decision gate ("Design deviation exists -> WARNING
unless it breaks a spec"), this is not a WARNING -- the spec text is
directly falsified by the implementation. The premise cited when Decision 5
was written (Vercel documentation as of 2026-07-24) did not hold up against
real build/runtime behavior; the two failed vercel.json attempts are
concrete negative evidence, not a shortcut.

Classification: CRITICAL. 03-spec.md (Engram #52) needs a revision 3
amendment before this change can be honestly archived: replace the "Static
file serving without WhiteNoise" requirement and its two scenarios with a
requirement matching the implemented (and now live-verified) reality --
WhiteNoise serving collected static files from inside the WSGI function,
STATIC_ROOT still set, collectstatic still a build step, no Blob/CDN
static hosting. This is a spec-correctness gap, not an implementation bug --
the code, tests, and live behavior are internally consistent with each
other; only the spec document lags behind.

Recommendation: run sdd-spec for a revision-3 amendment (mirroring
how revision 2 absorbed Decision 11), or, if the user prefers not to reopen
spec, archive with an explicit, permanent exception note comparable to the
budget exception (Engram #56) -- but do not archive silently as if the spec
were satisfied as written.

## D. Regression test narrowing -- confirmed intentional and honest

- test_a1_static_root_set_no_whitenoise -> test_a1_static_root_set_whitenoise_serves_it:
  docstring explicitly says "Superseded from 'no WhiteNoise' after empirical
  deployment evidence" and names the exact Decision 5 failure mode. Read in
  full; accurate, not misleading.
- test_a7_no_code_consumes_blob_token: narrowed to assert specifically
  STORAGES["default"]["BACKEND"] ==
  "django.core.files.storage.FileSystemStorage" (the Blob-relevant key),
  rather than asserting STORAGES doesn't exist at all -- correct, since
  STORAGES["staticfiles"] now legitimately exists for WhiteNoise. Read in
  full; the in-file comment explains exactly why the narrowing is
  necessary and correct. No drift into "Blob is now safe to ignore" -- the
  test still fails if any Blob-consuming code or a default-storage
  override appears.

Both narrowings are precise, not blanket weakenings, and are documented
in-file. No finding here.

## E. Full spec compliance matrix

### Automatable (14/14 covering tests pass at runtime; 35/35 total green)

| ID | Requirement | Status |
|---|---|---|
| A1 | Static file serving | PASS (test), but proves the opposite of the current spec text -- see Finding C (CRITICAL) |
| A2 | Neon CONN_MAX_AGE=0 | PASS |
| A3 | ALLOWED_HOSTS fails loud | PASS |
| A4 | CSRF trusted origins shape | PASS |
| A5 | SECURE_PROXY_SSL_HEADER presence | PASS (presence-only, by design) |
| A6 | No auto-migrate in build/code | PASS |
| A7 | No code consumes Blob token | PASS (narrowed correctly, see D) |
| A8 | check --deploy --fail-level WARNING clean; DEBUG False | PASS (both sub-tests green; DEBUG sub-test docstring already corrected per commit 0b89864) |
| A9 | .env ignored, .env.example no real secrets | PASS |
| A10 | HTTPS_ONLY=True hardens transport | PASS |
| A11 | HTTPS_ONLY=False disables hardening | PASS |
| A12 | Missing HTTPS_ONLY fails loud | PASS |
| A13 | Malformed HTTPS_ONLY rejected (x4) | PASS |
| A14 | HSTS preload refused + silenced | PASS |

### Manual, console (6/6 -- MC-1..MC-6)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| MC-1 | Neon pooled endpoint (Production) | PASS | User-attested: DATABASE_URL Production uses -pooler host on the production branch. Not independently re-checkable (private dashboard) by this verify pass. |
| MC-2 | Migrations applied to Neon production | PASS | Covered under Phase 9: showmigrations against production direct endpoint (ep-icy-firefly-ax9w17zr, no -pooler) showed all [X]. Branch was pre-migrated (it was the original dev/default branch); makemigrations produced no new changes. User-attested. |
| MC-3 | Blob store connected | PASS | User-attested: store proyecto-curso-blob (Private, iad1), BLOB_READ_WRITE_TOKEN present. |
| MC-4 | Preview deployment uses dev-branch DB | PASS | User-attested + independently corroborated by this session's commit history: branch prueba-preview, commit 9c5bf85 present, deployment reached Ready, /login/ returned 200 on the Preview URL after fixing 3 blank env vars (see Finding F). |
| MC-5 | Production lists all 6 vars; no secret leak in repo | PASS | Independently re-checked this session: git grep -n "neon.tech" in the current tree returns only placeholders (.env.example, conftest.py, test comments) -- no real hostname. |
| MC-6 | DJANGO_HTTPS_ONLY per environment | PASS | User-attested: True/True/False for Production/Preview/Development. |

### Manual, live (6/6 -- ML-1..ML-6)

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| ML-1 | HTTPS reachability, no redirect loop | PASS | Independently re-run this session: curl to /login -> 301 (Django's own trailing-slash normalization, not a loop) -> /login/ -> 200. |
| ML-2 | Static asset served, correct content-type | PASS, with the causal-mechanism caveat in Finding C | Independently re-run this session: curl -I .../static/admin/css/base.css -> 200, content-type: text/css. Served by WhiteNoise, not Vercel CDN as the current spec text (falsely) requires -- see Finding C. |
| ML-3/ML-4 | CSRF accepted on live origin; secure-cookie/session behavior | PASS | User-attested: login with admin + reset password succeeded live (screenshot confirmed "Sesion iniciada como admin"); cookies persisted across reload. |
| ML-5 | Item #1 auth behavior holds live | PASS-with-note | Administrador reaching /admin/ styled and authenticated: user-attested and independently re-checked this session (/admin/ unauthenticated request returns 302 -> /admin/login/?next=/admin/, i.e., correctly gated). Not independently re-verified live: a usuario-role account rejected at /admin/, and an unauthenticated visitor's redirect target landing on the app's custom /login specifically (the live redirect observed goes to Django admin's own /admin/login/, not the app's /login/ -- this is expected default django.contrib.admin behavior given LOGIN_URL = "login" is not wired into the admin site, and predates this deployment change; it is not a defect introduced by backlog #2). Both of the two live-unconfirmed sub-cases are covered by the automated, currently-passing usuarios/tests/test_login.py::test_usuario_role_is_denied_django_admin and the visitor-redirect tests in the same 35-passed suite. Recorded honestly as partial manual coverage, not invented. |
| ML-6 | HSTS + Secure cookies, no redirect loop | PASS-with-note | Independently re-run this session: curl -I .../login/ -> Strict-Transport-Security: max-age=3600; includeSubDomains (no preload), csrftoken cookie carries Secure, single 200 with no redirect chain -- all confirmed fresh, not just user-reported. Not independently confirmed: sessionid cookie's Secure flag (requires an authenticated session; no live login was performed by this verify pass to avoid mutating production state). Covered by automated test A10 (SESSION_COOKIE_SECURE = HTTPS_ONLY = True in Production) and the settings-level guarantee is structurally identical to the independently-confirmed csrftoken cookie (same HTTPS_ONLY flag drives both). |

Manual scope total: 12/12 attempted, 12/12 PASS or PASS-with-note. 0
FAIL. Two items (ML-5, ML-6) carry an honestly-recorded partial-coverage
note rather than a fabricated full manual re-verification.

## F. Operational incidents this session (documented, not spec-relevant, informative)

1. Env var overwrite incident (Production). While loading Preview's 5
   variables, the user edited the existing Production entries by mistake
   (same Key, different Environment tab, but the UI let an edit happen
   instead of creating a new entry) -- detected because all 5 showed
   "Updated" instead of "Added." Corrected by recreating the 5 Production
   entries as separate entries. Lesson: Vercel's environment-variable UI
   permits the same Key across different Environments, but does not warn
   against accidentally editing an existing Environment's value while
   intending to add a new Environment's value. Worth a callout in any future
   env-var-matrix task text (5.1/7.1-7.3 style tasks), not a code fix.
2. Blank Preview env vars incident. DJANGO_ALLOWED_HOSTS,
   DJANGO_CSRF_TRUSTED_ORIGINS, and DJANGO_HTTPS_ONLY for Preview were
   found empty after a save (exact cause unconfirmed -- possibly a blank
   save), causing a real DisallowedHost on the first Preview deploy
   attempt for MC-4. Resolved by re-entering the 3 values. This is exactly
   the fail-loud behavior the design intended (require_env/
   require_bool_env), working as designed -- the failure was caught before
   traffic was silently mis-served, not a defect in the settings logic.

Neither incident indicates a code or spec defect; both are operational
observations about the Vercel console UX. Recorded for completeness per the
task's request, not scored against the verdict.

## G. Findings

### CRITICAL

1. 03-spec.md / Engram #52's "Static file serving without WhiteNoise"
   requirement is falsified by the implementation (Finding C). The
   implementation, its test (test_a1_static_root_set_whitenoise_serves_it),
   and the independently re-run live curl check are all internally
   consistent and correct -- the spec document is the one out of date. This
   must be resolved (spec revision 3, or an explicit accepted-exception
   note) before archive; archiving with the spec unchanged would misrepresent
   the shipped behavior as matching a requirement it does not match.

### WARNING

1. 05-tasks.md checkboxes for Phases 1, 7, 8, 9, 10 are still all
   unchecked ("- [ ]"), even though this session's narrative and the git
   history (commits c291fe1 through 9c5bf85, plus the user's
   MC-1..MC-6/ML-1..ML-6 attestations) show the underlying work was done.
   Per this skill's hard rules, this verify pass reports rather than edits
   the tasks artifact -- the orchestrator/user should update
   05-tasks.md's checkboxes (and its "Apply status"/"Not attempted"
   framing at the top of the file, which is now stale) to reflect Phases 1,
   7, 8, 9, 10 as complete before archive, so the archived tasks document
   matches reality.
2. Design Decision 5's entrypoint-detection assumption was also false
   (Finding B) -- pyproject.toml's [tool.vercel] entrypoint and its
   [project].dependencies table are required, undocumented (at design
   time) additions. No spec text contradicts this, so it stays a WARNING,
   not a CRITICAL, but it belongs in the design's own record for future
   readers, not only in commit messages.
3. pyproject.toml [project].dependencies duplicates requirements.txt
   verbatim (5 packages) -- a real drift risk flagged by the session itself
   in commit 356f8e6's message. Two files must now be kept in sync by
   hand; nothing enforces it. Not spec-breaking, but worth a follow-up
   (e.g., a task or a small script) in a future backlog item.
4. ML-5 and ML-6 each carry one live sub-case that was not independently
   re-verified against the deployed app (usuario-role admin rejection,
   visitor-redirect-to-/login-specifically for ML-5; sessionid cookie's
   Secure flag for ML-6). Both are covered by passing automated tests, so
   this is not reported as a gap in actual protection -- only as a gap in
   live manual re-confirmation, exactly as the task requested (no invented
   verification).
5. 424-line budget overrun remains an open, accepted exception
   (Engram #56, restated from #58, not reopened here).

### SUGGESTION

1. Consider recording the Vercel env-var UI incidents (Finding F) as a
   short operational note in the design or a runbook, so a future
   redeploy/rotation doesn't repeat the same accidental-overwrite mistake.
2. test_a6_no_build_step_or_code_runs_migrate /
   test_a7_no_code_consumes_blob_token still iterate Path.rglob("*.py")
   without an explicit non-empty guard (carried over from #58, unchanged,
   still low-risk today).

## H. TDD / regression status (unchanged from partial verify, restated)

35/35 tests green, including all 17 pre-existing usuarios tests and all 18
deployment tests. The per-test RED classification independently re-derived
in the partial verify (#58) stands; nothing in this session's additional
commits (c291fe1, 6a62efd, 976f8bc, 26f3505, 356f8e6) reopened any
RED/GREEN question -- 356f8e6 modified two existing tests
(test_a1, test_a7) in place rather than adding new scenario IDs, and both
modifications are covered under Finding D.

## Next steps

1. Before archive: resolve the CRITICAL in Finding C -- either run
   sdd-spec for a revision-3 amendment to 03-spec.md (recommended, keeps
   the spec honest and matching shipped behavior), or have the user
   explicitly accept the divergence as a permanent documented exception
   (same pattern as the budget exception, Engram #56).
2. Update 05-tasks.md checkboxes for Phases 1, 7, 8, 9, 10 (WARNING #1) so
   the archived tasks document matches the real state.
3. Once (1) and (2) are resolved, this change is otherwise ready for
   sdd-archive -- no other CRITICAL is open, and every WARNING here is
   either informational or already-accepted.

Related: [[sdd/despliegue-e-infraestructura/apply-progress]],
[[sdd/despliegue-e-infraestructura/tasks]],
[[sdd/despliegue-e-infraestructura/design]],
[[sdd/despliegue-e-infraestructura/spec]],
[[sdd/despliegue-e-infraestructura/verify-report-partial]].

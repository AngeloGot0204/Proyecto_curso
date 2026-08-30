# Apply Progress: Sincronización y asignación de número de registro

**PR scope**: PR 1 of 3 — `tasks.md` Phase 1 (migration) + Phase 2 (server idempotency). Chain strategy: `stacked-to-main`. Client upload-queue rework (Phase 3/4) and `nuevo-reporte.js` (Phase 5) are explicitly OUT of scope for this apply batch (PR 2/3).

## Completed Tasks

### Phase 1: Server Migration (Foundation) — all complete
- [x] 1.1 `RunSQL` sequence `reportes_numero_registro_seq` (forward + reverse SQL)
- [x] 1.2 `AddField id_local` — `UUIDField(unique=True, editable=False, db_default=Func(function="gen_random_uuid"))`
- [x] 1.3 `AddField numero_registro` — `BigIntegerField(unique=True, editable=False, db_default=Func(Value("reportes_numero_registro_seq"), function="nextval"))`, ordered after `id_local`
- [x] 1.4 `reportes/models.py::Reporte` updated with matching field declarations
- [x] 1.5 `migrate reportes` (forward) and `migrate reportes 0004` (reverse) both confirmed clean against the real Postgres 18.6 (Neon) database, then re-applied forward to leave the DB in final state

### Phase 2: Server-Side Idempotency (TDD) — all complete
- [x] 2.1-2.5 RED: model-level tests for `numero_registro`/`id_local` DB-default behavior
- [x] 2.6 GREEN: confirmed passing against Phase 1 migration/model (DB-level, no Python code needed)
- [x] 2.7-2.8 RED: view-level idempotency/validation tests (`iniciar_reporte`)
- [x] 2.9 GREEN: rewrote `reportes/views.py::iniciar_reporte` — `id_local` parsed from POST (fallback `uuid.uuid4()`), `get_or_create(id_local=..., creador=request.user, defaults={...})` inside `transaction.atomic()`, `IntegrityError` → 400, `tipo_id` mismatch → 400
- [x] 2.10 GREEN: all Phase 2 tests pass
- [x] 2.11-2.12 RED/GREEN: `test_paso_post_redirect_es_seguible` added to `test_views.py`, passes unchanged (documents existing redirect contract)
- [x] 2.13-2.14 RED/GREEN: `test_sesion_expirada_no_rompe_idempotencia` passes against 2.9's implementation; no further refactor needed — code is already clear

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/migrations/0005_id_local_numero_registro.py` | Created | `RunSQL` sequence + two `AddField` ops, in design-mandated order |
| `reportes/models.py` | Modified | Added `id_local` (UUIDField) and `numero_registro` (BigIntegerField) to `Reporte`, both with `db_default` |
| `reportes/views.py` | Modified | `iniciar_reporte` rewritten to idempotent `get_or_create` per design's Interfaces/Contracts |
| `reportes/tests/test_idempotencia.py` | Created | 12 tests: scenarios 1-10, 12 (model + view level) |
| `reportes/tests/test_views.py` | Modified | Added `test_paso_post_redirect_es_seguible` (scenario 11) |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.4 | N/A (migration/model) | — | N/A (new fields) | N/A | ✅ Verified via `migrate` + full suite | N/A | N/A |
| 2.1 | `test_idempotencia.py::test_create_asigna_numero_registro_sin_refresh` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.2 | `test_idempotencia.py::test_numero_registro_avanza_por_secuencia` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.3 | `test_idempotencia.py::test_numero_registro_es_unico` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.4 | `test_idempotencia.py::test_id_local_unico_a_nivel_bd` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.5 | `test_idempotencia.py::test_id_local_por_defecto_es_distinto_por_fila` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.7 | `test_idempotencia.py::test_post_nuevo_repetido_mismo_id_local_no_duplica` | Integration | ✅ 115/115 (baseline before view rewrite) | ✅ Written | ✅ Passed | ✅ Covered by 2.8's four companion scenarios | ➖ None needed |
| 2.8 | `test_idempotencia.py::{test_post_nuevo_sin_id_local_sigue_funcionando, test_id_local_invalido_devuelve_400, test_id_local_de_otro_usuario_devuelve_400, test_id_local_de_otro_tipo_devuelve_400}` | Integration | ✅ (same baseline) | ✅ Written | ✅ Passed | ✅ 4 distinct code paths (no-id_local, invalid, other-user, other-tipo) | ➖ None needed |
| 2.11 | `test_views.py::test_paso_post_redirect_es_seguible` | Integration | ✅ (existing `paso` tests unaffected) | ✅ Written | ✅ Passed | ➖ Single scenario (documents existing contract) | ➖ None needed |
| 2.13 | `test_idempotencia.py::test_sesion_expirada_no_rompe_idempotencia` | Integration | ✅ (same baseline) | ✅ Written | ✅ Passed | ➖ Single end-to-end scenario (3-phase: create, expired retry, re-login retry) | ✅ Reviewed `iniciar_reporte` — already minimal/clear, no refactor needed |

### Test Summary
- **Total tests written**: 13 (12 in `test_idempotencia.py` + 1 in `test_views.py`)
- **Total tests passing**: 13/13 (this batch); 128/128 full `reportes/` suite
- **Layers used**: Integration (13, Django test client + real Postgres test DB via `--reuse-db`)
- **Approval tests** (refactoring): None — `iniciar_reporte` was rewritten, not behavior-preserving-refactored (design explicitly changes create → get_or_create semantics; the 4 backwards-compatibility scenarios in 2.8/2.11 serve the same protective purpose as approval tests would)
- **Pure functions created**: 0 (view logic; `get_or_create` + `IntegrityError` handling requires DB access by nature)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_idempotencia.py reportes/tests/test_views.py -k "id_local or numero_registro or redirect_es_seguible"` — all new/targeted tests pass (verified as part of full-suite run below; the full suite is the authoritative confirmation since Neon DB round-trips make isolated re-runs redundant with the just-completed full run) |
| Runtime harness command/scenario and exact result | `./.venv/Scripts/python.exe -m pytest reportes/ -q` against real Postgres 18.6 (Neon, `test_reportes_dev`) — **128 passed in 466.45s (0:07:46)**, 0 failed. Also ran `manage.py migrate reportes --skip-checks` (forward, OK) then `manage.py migrate reportes 0004 --skip-checks` (reverse, OK) then re-applied forward — both directions clean against the real dev DB. |
| Rollback boundary | `git checkout -- reportes/models.py reportes/views.py reportes/tests/test_views.py`, `rm reportes/migrations/0005_id_local_numero_registro.py reportes/tests/test_idempotencia.py`, then `manage.py migrate reportes 0004` if the migration was applied to a shared DB. No other file in this PR depends on `id_local`/`numero_registro` yet (Phase 3-5 client work is out of scope for this PR). |

## Deviations from Design

None — implementation matches design.md exactly, including field types, `db_default` expressions, migration operation ordering, and the `iniciar_reporte` interface contract pseudocode (design's "Interfaces / Contracts" section maps almost verbatim to the final `views.py` code).

One clarification made during implementation: design's Testing Strategy leaves scenario 12 (`test_sesion_expirada_no_rompe_idempotencia`)'s file unspecified beyond "unless noted" (only scenario 11 explicitly names `test_views.py`). Placed it in `test_idempotencia.py`, consistent with the default rule and with tasks.md 2.13 grouping it under the same file as the rest of Phase 2's idempotency tests.

## Issues Found

- **Pre-existing, unrelated environment issue**: `manage.py` (any subcommand, including plain `migrate`) currently fails Django's system checks with `4_0.E001: CSRF_TRUSTED_ORIGINS setting must start with a scheme`, due to a misconfigured `.env`/`.env.local` value unrelated to this change. Worked around locally with `--skip-checks` to verify the migration; `pytest-django` is unaffected because it does not run Django's full system-check suite. This is out of scope for this PR but should be flagged to the user/maintainer — worth a follow-up fix (correct `CSRF_TRUSTED_ORIGINS` to include a scheme, e.g. `https://...`).
- Two early full-suite test runs produced spurious `psycopg.errors.DeadlockDetected` failures on `tipos_reporte_tipodereporte_codigo_key` — root-caused to two concurrent `pytest` invocations (my own background-command overlap while diagnosing a slow first run against the remote Neon DB) racing on the same reused test database. Not a code defect. A clean, single, non-concurrent full-suite run confirmed **128/128 passing** with zero failures — this is the run recorded above and in this file's Work Unit Evidence.

## Remaining Tasks (out of scope for this PR — PR 2/3)

- [ ] Phase 3: Upload Queue — `offline-db.js`, fetch-based `paso-offline.js` rewrite, retry banner (PR 2)
- [ ] Phase 4: Manual Verification (DevTools scripts) (PR 2)
- [ ] Phase 5: `nuevo-reporte.js` forward-looking infra (PR 3)
- [ ] Phase 6: Cleanup/Documentation (6.1 design.md Open Question resolution, 6.2 offline-db.js README note, 6.3 final full-suite confirmation) — 6.3 is effectively already satisfied by this PR's 128/128 run, but formally belongs to whichever PR lands last per the original task grouping.

## Workload / PR Boundary

- Mode: stacked PR slice (chain strategy: `stacked-to-main`)
- Current work unit: Unit 1 — "Sequence-backed `id_local`/`numero_registro` + idempotent `iniciar_reporte`" (PR 1 of 3)
- Boundary: starts from the pre-existing `Reporte` model (no `id_local`/`numero_registro`) and `iniciar_reporte`'s bare `.create()`; ends with the full migration + idempotent view + 13 passing tests, fully independent of any client-side (JS) changes in PR 2/3
- Estimated review budget impact: migration (~48 lines) + models.py (+18 lines) + views.py (+~35 net lines changed) + 2 test files (~230 lines, mostly new tests) ≈ 330 changed lines — within the 400-line budget for this slice alone (the original ~550-650 estimate covered all 3 PRs combined)

## Status

18/18 assigned tasks (Phase 1 + Phase 2) complete. Ready for `sdd-verify`, or for `sdd-apply` to continue with PR 2 (Phase 3/4) in a later batch.

---

## PR 2 of 3 — `tasks.md` Phase 3 (Upload Queue) — 2026-08-30

**Scope**: tasks 3.1-3.8 only (client-side upload queue: `offline-db.js`, fetch-based `paso-offline.js` rewrite, retry banner). Phase 4 (manual DevTools verification) is explicitly deferred to the user, live. Phase 5 (`nuevo-reporte.js`) and Phase 6 (cleanup) are out of scope for this batch. No server-side files touched (already merged to `main` in PR 1).

### Completed Tasks

- [x] 3.1 Created `reportes/static/reportes/offline-db.js` — single `Dexie("reportes-offline").version(2).stores({ borradores: "[reporteId+seccionId], reporteId, estado", nuevos: "codigoTipo" })`, exposed as `window.reportesOfflineDB`.
- [x] 3.2 Added `<script src="{% static 'reportes/offline-db.js' %}"></script>` in `reportes/templates/reportes/paso.html`, between the Dexie CDN tag and the (deferred) `paso.js`/`paso-offline.js` tags.
- [x] 3.3 Rewrote `paso-offline.js`'s submit handler (`intentarEnvio()`) to use `fetch(form.action, {method:"POST", body:new FormData(form), credentials:"same-origin", redirect:"follow"})` instead of `form.submit()`.
- [x] 3.4 Implemented outcome branching in `manejarRespuesta()`: final URL `/login/` checked first → `fallo`/`sesion_expirada`, then navigates to login (draft preserved); else `response.ok`/`response.redirected` → delete Dexie row, `location.assign(response.url)`; else HTTP >= 400 → `fallo` with `intentos++`; fetch rejection (network error) or `!navigator.onLine` (checked before the fetch call, to skip a doomed request) → `pendiente` with `intentos++`.
- [x] 3.5 Added `intentos` (number) and `ultimoError` (string|null) fields to every `borradores` row write (`escribirBorrador` now defaults them to `0`/`null`; `marcarComo()` increments `intentos` from the previously-stored value).
- [x] 3.6 Added `mostrarBanner()`/`limpiarBanner()` (new "Retry banner UI" section), rendering via `form.insertAdjacentElement("beforebegin", …)` exactly like the existing `crearPrompt()`/`mostrarPrompt()` restore-prompt pattern, with a `data-borrador-banner` container (distinct attribute from `data-borrador-prompt` so the two UIs never collide) and a `data-borrador-reintentar` button.
- [x] 3.7 Reintentar button's click handler calls `intentarEnvio()` directly — since `intentarEnvio()` always re-reads `new FormData(form)` at call time, this naturally re-serializes whatever the user has currently typed and transitions back through `escribirBorrador("enviando")`.
- [x] 3.8 `reconciliar()` gained a new branch, checked before the existing `enviando`/`borrador` branches: `estado === "pendiente" || estado === "fallo"` → `mostrarBanner(fila)` with the stored row (existing `intentos`/`ultimoError`), no automatic retry.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/static/reportes/offline-db.js` | Created | Single shared Dexie schema owner (v2), exposes `window.reportesOfflineDB` |
| `reportes/static/reportes/paso-offline.js` | Modified | Consumes `window.reportesOfflineDB` instead of opening its own `Dexie(...)`/`.version(1)`; fetch-based submit pipeline (`intentarEnvio`, `manejarRespuesta`, `marcarComo`, `obtenerIntentosPrevios`); retry banner UI (`mostrarBanner`, `limpiarBanner`, `mensajeBanner`); `reconciliar()` restores `pendiente`/`fallo` |
| `reportes/templates/reportes/paso.html` | Modified | Added non-deferred `<script>` for `offline-db.js`, positioned after the Dexie CDN tag and before the deferred `paso.js`/`paso-offline.js` tags so the shared schema is guaranteed ready first |

### Key Implementation Decisions

1. **`offline-db.js` script tag is intentionally NOT `defer`**: it's placed immediately after the (also non-deferred) Dexie CDN `<script>` tag, so it executes synchronously in document order — right after Dexie loads, before the parser reaches the deferred `paso.js`/`paso-offline.js` tags. This guarantees `window.reportesOfflineDB` exists before any deferred consumer script runs, without needing a `DOMContentLoaded`/event-based handshake between the two files.
2. **Login-redirect check ordered before the success check** in `manejarRespuesta()`: a `fetch` that follows a redirect to `/login/` still resolves with `response.ok === true` (the login page itself renders 200) and `response.redirected === true`, so checking `new URL(response.url).pathname === "/login/"` first is required — otherwise a session-expired submission would be misclassified as success and the row would be deleted, contradicting the "Draft Survives Session Expiry" requirement.
3. **`!navigator.onLine` short-circuits before calling `fetch`** rather than relying solely on the `fetch` rejection path, per design's explicit "network error/`!navigator.onLine`" wording — avoids an unnecessary request attempt when the browser already knows it's offline, matching the manual DevTools script's "Network ▸ Offline, submit → no navigation" expectation more directly (both paths still land on the same `marcarComo("pendiente", …)` outcome).
4. **`ultimoError` uses internal string codes** (`"sesion_expirada"`, `"http_" + status`, `"error_de_red"`, `"sin_conexion"`, `"respuesta_inesperada"`) rather than free-form/localized text — matches the spec's literal `ultimoError:"sesion_expirada"` example and keeps the field machine-inspectable for the Phase 4 manual DevTools verification.
5. **Reintentar re-uses `intentarEnvio()` verbatim** (no separate "retry" function) — since it always reads live `FormData(form)`, this is simpler than design's phrasing ("re-serialize the current form and re-run the fetch submit") suggested as two steps, and guarantees the retry path and the original submit path can never drift apart.
6. **Distinct DOM markers** (`data-borrador-banner`/`data-borrador-reintentar` vs. the pre-existing `data-borrador-prompt`/`data-borrador-restaurar`/`data-borrador-descartar`) so the retry banner (pendiente/fallo) and the stale-draft restore prompt (`#9`) can never be confused with each other or accidentally styled/queried together.

### Deviations from Design

None identified. `manejarRespuesta`'s branch ordering (login-check before ok-check) is a necessary clarification of the design's prose ordering, not a deviation — the design's own D4 rationale explicitly describes `response.redirected` following through to a 200, which is exactly the condition requiring the login check to run first.

### Test Coverage / TDD Note

Per the task brief and this project's documented limitation (no JS test runner), Phase 3 has no automated coverage. TDD RED/GREEN was skipped for this phase as instructed; Phase 4 (manual DevTools script, tasks 4.1-4.6) is deferred to the user, to be run live against a dev server.

### Runtime Harness — Full Python Suite

`./.venv/Scripts/python.exe -m pytest -q` run from the project root (full suite, all apps, not just `reportes/`) — **269 passed in 611.14s (0:10:11), 0 failed**. Confirms the `paso.html` template change (covered by Django view tests) introduced no regressions.

### Rollback Boundary

`git checkout -- reportes/templates/reportes/paso.html reportes/static/reportes/paso-offline.js`, `rm reportes/static/reportes/offline-db.js`. No other file in this PR depends on `offline-db.js` yet (Phase 5's `nuevo-reporte.js` is out of scope and does not exist in this batch).

## Remaining Tasks (out of scope for this PR — PR 3, plus user-run Phase 4)

- [ ] Phase 4: Manual Verification (DevTools scripts, tasks 4.1-4.6) — to be run live by the user against a dev server, per task brief
- [ ] Phase 5: `nuevo-reporte.js` forward-looking infra (PR 3)
- [ ] Phase 6: Cleanup/Documentation (6.1 design.md Open Question resolution, 6.2 offline-db.js README note, 6.3 final full-suite confirmation)

---

## PR 3 of 3 — `tasks.md` Phase 5 (`nuevo-reporte.js`) — 2026-08-30

**Scope**: tasks 5.1-5.5 only — new, currently-unreferenced client infra for backlog #12 (forward-looking, per design's D7). No host page/template exists yet; this file ships unused until #12 builds a page that includes it. Phase 6 (cleanup/docs) and any other file are explicitly out of scope for this batch. `paso-offline.js`, `offline-db.js`, and all Python files were left untouched.

### Completed Tasks

- [x] 5.1 Created `reportes/static/reportes/nuevo-reporte.js`. On `DOMContentLoaded`, queries `form[data-nuevo-reporte][data-codigo-tipo]`; no-ops (`if (!form) return;`) when absent, mirroring `paso-offline.js`'s defensive opening (also guards `typeof Dexie === "undefined"` and a missing `window.reportesOfflineDB`, same degrade-to-server-default contract as `paso-offline.js`).
- [x] 5.2 `obtenerOCrearIdLocal()` reads `db.nuevos.get(codigoTipo)`; reuses the stored `idLocal` if the row already exists, otherwise generates one via `crypto.randomUUID()` and persists it with `db.nuevos.put({codigoTipo, idLocal})` — all **before** the first `fetch` POST, so a reload or a failed submit's retry reuses the same value.
- [x] 5.3 `inyectarCampoOculto(idLocal)` creates (or reuses, if already present) a `<input type="hidden" name="id_local">` appended to the form and sets its `value` to the persisted UUID, resolved through the `idLocalListo` promise chain before every submit.
- [x] 5.4 On submit, `fetch(form.action, {...})` with the same D4 options as `paso-offline.js` (`credentials:"same-origin"`, `redirect:"follow"`); on `respuesta.redirected` (success — the report now exists idempotently per D3), deletes the `db.nuevos` row for `codigoTipo` and calls `location.assign(respuesta.url)`. Non-redirected/network-error branches intentionally **keep** the row so a retry reuses the same `id_local` rather than orphaning a server-side row under a discarded UUID (no retry UI is implemented — out of scope for this PR; #12 owns the host page's error handling).
- [x] 5.5 File-header comment documents D7 explicitly: "no template in this codebase yet renders a `form[data-nuevo-reporte][data-codigo-tipo]`" and that verification is manual only, via an injected test form (tasks.md 4.5), until #12 lands.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/static/reportes/nuevo-reporte.js` | Created | `id_local` generation/persistence/injection + fetch submit + Dexie `nuevos` row lifecycle, per design's D7/D5/D4/D3, Data Flow diagram, and state contract |

### Key Implementation Decisions

1. **`DOMContentLoaded` listener, not top-level `document.querySelector` at parse time**: unlike `paso-offline.js` (which runs as a deferred script after the DOM is already parsed, so it queries synchronously at the top of its IIFE), the task brief explicitly specifies "on `DOMContentLoaded`" for this file — since #12's future template loading order is unknown, wrapping the query in a `DOMContentLoaded` handler is more robust regardless of whether the script tag ends up deferred or not.
2. **Hidden input lookup is idempotent** (`form.querySelector('input[name="id_local"]')` before creating one): guards against the handler somehow running twice or the template already declaring the hidden input itself — avoids duplicate `id_local` fields being submitted.
3. **`respuesta.redirected` is the sole success signal** (not `respuesta.ok`, unlike `paso-offline.js`'s `manejarRespuesta`): task 5.4 explicitly names `response.redirected` as the trigger; `iniciar_reporte` always redirects (302) on success and never returns a 200 body directly, so this is a safe, narrower match — no login-redirect edge case exists here yet since there's no analogous "next step redirects to login" ambiguity for this brand-new-report entry point (that concern is specific to `paso-offline.js`'s multi-step wizard).
4. **Failure/network-error branches keep the `nuevos` row instead of clearing or marking it `fallo`**: task 5.4 only specifies the success-path deletion; Phase 5 has no state-machine/banner requirement (that's `paso-offline.js`'s Phase 3 concern), so on any non-success outcome the simplest and safest behavior consistent with D7's "reused... on subsequent loads/retries" contract is to leave the row untouched — a future #12 page reload will naturally pick up and reuse the same `id_local` via `obtenerOCrearIdLocal()`.
5. **No automated test coverage** (per task brief): this project has no JS test runner; Phase 5 has no RED/GREEN cycle. Verification is deferred to task 4.5 (already in tasks.md, unchanged by this PR), to be done live with the user via an injected `data-nuevo-reporte` test form in DevTools.

### Deviations from Design

None. Implementation follows design's D2/D3/D4/D5/D7, the Data Flow diagram's "Nuevo reporte page (future, #12)" swimlane, and tasks.md 5.1-5.5 verbatim.

### Runtime Harness — Full Python Suite

`./.venv/Scripts/python.exe -m pytest -q` run from the project root — **269 passed in 613.46s (0:10:13), 0 failed**. Confirms zero regressions; expected, since this PR touches only one new, currently-unreferenced JS file and no Python code.

### Rollback Boundary

`rm reportes/static/reportes/nuevo-reporte.js`. No other file in the repository references or depends on this file yet (D7) — deleting it is a no-op for every existing page.

### Status

5/5 assigned tasks (Phase 5) complete. Combined with PR 1 (Phase 1-2) and PR 2 (Phase 3), all of tasks.md is now implemented except Phase 4 (manual DevTools verification, partially done live by the user — 4.2 and 4.4 already checked off; 4.1, 4.3, 4.5, 4.6 remain) and Phase 6 (cleanup/docs). Ready for `sdd-verify`, or for a follow-up `sdd-apply` pass to close out Phase 6.

## Remaining Tasks (after PR 3)

- [ ] Phase 4: 4.1, 4.3, 4.5, 4.6 — remaining manual DevTools verification steps (user-run)
- [ ] Phase 6: Cleanup/Documentation (6.1 design.md Open Question resolution, 6.2 offline-db.js README note, 6.3 final full-suite confirmation — already satisfied by this PR's 269/269 run)

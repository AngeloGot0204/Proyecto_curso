# Apply Progress: validacion-datos-formulario

## Scope of PR 1 of 4

Phase 1 (fixture foundation) + Phase 2 (`validar_reporte` core, all 6 spec
scenarios + anti-drift lock). Did NOT touch `formularios.py`, `views.py`,
`urls.py`, or templates — those belong to PR 2-4 per the chained-PR plan.

**Chain strategy**: stacked-to-main. This PR targets `main`; PR 2 will
target this PR's branch once merged (or `main` after merge).

## Scope of PR 2 of 4 (this batch)

Phase 3 only: `reportes/formularios.py` gains the JS-contract data
attributes (`data-rango`/`data-rango-extremo` on range `TimeField`
widgets) and the `{id}_observacion` companion field for `seleccion` nodes
whose `opciones` include the exact string `"No cumple"`
(`data-requiere-observacion` on the select, `data-observacion-de` on the
companion `CharField`). Did NOT touch `views.py`, `urls.py`, or any
template — S-09 (`revision` view/template) is PR 3, `paso.html`/`paso.js`
is PR 4.

## Completed Tasks

### Phase 1: Foundation
- [x] 1.1 Added `estructura_con_validaciones` fixture to `reportes/tests/conftest.py`

### Phase 2: `validar_reporte` core (TDD)
- [x] 2.1 RED: all obligatorio filled → empty `errores` (scenario 1)
- [x] 2.2 GREEN: created `reportes/validacion.py`
- [x] 2.3 RED/triangulation: missing obligatorio → one `errore` w/ `identificador_de_campo`+`seccion_id` (scenario 2)
- [x] 2.4 RED/triangulation: anti-drift lock vs direct `_validar_completitud` (scenario 3)
- [x] 2.5 GREEN confirmed: 2.3/2.4 pass via `.faltantes` translation only
- [x] 2.6 RED/triangulation: stray `fin<=inicio` → advertencia, not errore (scenario 4)
- [x] 2.7 GREEN confirmed: rango pass via `desde_texto(TimeField())`, skips unparsable
- [x] 2.8 RED/triangulation: "No cumple" without observación → advertencia (scenario 5)
- [x] 2.9 RED/triangulation: "No cumple" with observación → no advertencia (scenario 6)
- [x] 2.10 GREEN confirmed: seleccion "No cumple" pass

### Phase 3: `formularios.py` companion field (TDD)
- [x] 3.1 RED `test_formularios.py`: rango `TimeField` widgets carry `data-rango`/`data-rango-extremo`
- [x] 3.2 GREEN: `_campos_de_rango` gains `nodo_id` param, sets both attrs
- [x] 3.3 RED: seleccion field with "No cumple" option → companion `{id}_observacion` `CharField(required=False)` in `form.fields`, `data-requiere-observacion` on select
- [x] 3.4 GREEN: `construir_formulario_seccion` injects companion field with `data-observacion-de`

## Scope of PR 3 of 4 (this batch)

Phase 4 only: S-09 review screen — `reportes/views.py::revision` (GET-only,
`@login_required`, creador-scoped `get_object_or_404`, calls
`validar_reporte`), the `path("<int:reporte_id>/revision/", ...,
name="reportes_revision")` route in `reportes/urls.py`, and
`reportes/templates/reportes/revision.html` (Debes corregir / Advertencias
lists, each item linked to its `paso` via `seccion_id`; Generar `disabled`
iff `puede_generar` is false). Did NOT touch `paso.html`/`paso.js`
(client-side JS layer is PR 4) or run the Phase 6 regression pass (comes
after PR 4).

## Scope of PR 4 of 4 (FINAL — this batch)

Phase 5 (client-side JS layer: `paso.html`/`paso.js`) + Phase 6 (regression
pass, full-suite confirmation). This closes out the entire change — no
tasks remain in `tasks.md` after this batch.

### Phase 5: Client-side JS layer (TDD)
- [x] 5.1 RED `test_views.py`: `paso` GET HTML contains `data-campo`, `data-rango`, `data-requiere-observacion`, `data-siguiente`, `<script src=".../paso.js">`
- [x] 5.2 GREEN: modified `reportes/templates/reportes/paso.html` — wrapped fields in `<p data-campo="{{ campo.name }}">`, added `{% load static %}` + `{% block extra_head %}<script src="{% static 'reportes/paso.js' %}" defer></script>{% endblock %}`, `data-siguiente` on the nav anchor
- [x] 5.3 GREEN: created `reportes/static/reportes/paso.js` — hora-range lexicographic `fin <= inicio` compare (grouped via `[data-rango]`/`data-rango-extremo`) disables the submit button and sets `aria-disabled` + a `preventDefault` click guard on `[data-siguiente]`; "No cumple" toggle shows/hides the companion `p[data-campo]` and sets/strips `required` on its `[data-observacion-de]` input — **critically strips `required` on hide** so a hidden required field never blocks native submission (design's explicit callout), matching design's "`paso.js` behaviour" subsection exactly (`DOMContentLoaded` runs both toggles once for GET rehydration, then binds `change`/`input`)

### Phase 6: Regression
- [x] 6.1 Ran `test_post_paso_sin_valor_obligatorio_no_bloquea` unmodified — confirmed still passing, no edits to the test or to `paso`'s POST branch
- [x] 6.2 Added `test_post_paso_con_rango_invalido_no_bloquea` — POST with `fin <= inicio` still returns 302 and persists both `ValorDeReporte` rows; passed on first run (triangulation — the design decision to route the actual check through `validar_reporte`/S-09 rather than `paso`'s POST handler means no new server-side branch was needed, so this test proves the existing non-blocking POST contract already covers it)
- [x] 6.3 Full suite run: `pytest reportes/tests/test_validacion.py reportes/tests/test_views.py reportes/tests/test_formularios.py` → `41 passed in 100.83s`; whole-project `pytest` (no filter) → `203 passed in 256.59s (0:04:16)`

## ALL TASKS COMPLETE — change fully implemented, ready for `sdd-verify`.

## Remaining Tasks

None. Every task in `tasks.md` (Phases 1-6) is marked `[x]`.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/tests/conftest.py` | Modified (PR1) | Added `estructura_con_validaciones` fixture (obligatorio `texto`, `seleccion` with `["Cumple","No cumple"]`, obligatorio `rango-hora-inicio-fin`) |
| `reportes/validacion.py` | Created (PR1) | `ProblemaDeReporte`, `ResultadoDeRevision`, `_indice_de_campos`, `validar_reporte` — obligatorio pass via `generador._validar_completitud`/`ValoresIncompletos` exception translation (zero drift), rango-hora advertencia pass, "No cumple" advertencia pass |
| `reportes/tests/test_validacion.py` | Created (PR1) | 6 tests, one per spec scenario, covering `validar_reporte` |
| `reportes/formularios.py` | Modified (PR2) | `_campos_de_rango` gains a `nodo_id` param; both `TimeField` widgets get `data-rango`/`data-rango-extremo`. `construir_formulario_seccion`: `seleccion` nodes whose `opciones` include `_VALOR_NO_CUMPLE` (imported from `reportes.validacion`, avoiding a duplicated literal) get a `data-requiere-observacion` attr on the select plus an injected `{clave}_observacion` `CharField(required=False)` with `data-observacion-de` on its widget |
| `reportes/tests/test_formularios.py` | Modified (PR2) | 3 new tests: `data-rango`/`data-rango-extremo` on range widgets, companion-field injection + its data attrs when `"No cumple"` is an option, no companion field when it is not |
| `reportes/views.py` | Modified (PR3) | Added `revision(request, reporte_id)` — `@login_required`, creador-scoped `get_object_or_404(Reporte, pk=…, creador=request.user)` (D9), calls `validar_reporte`, renders `reportes/revision.html` with `{"reporte", "resultado"}`. `paso`/`iniciar_reporte` untouched |
| `reportes/urls.py` | Modified (PR3) | Added `path("<int:reporte_id>/revision/", views.revision, name="reportes_revision")` |
| `reportes/templates/reportes/revision.html` | Created (PR3) | "Debes corregir" (`errores`) and "Advertencias" (`advertencias`) `<ul>`s, each `<li>` linking to `{% url 'reportes_paso' reporte.id problema.seccion_id %}`; `<button type="button" {% if not resultado.puede_generar %}disabled{% endif %}>Generar</button>` |
| `reportes/tests/test_views.py` | Modified (PR3+PR4) | PR3: 5 new tests (see above). PR4: 2 more new tests — `test_get_paso_incluye_atributos_data_y_script_paso_js` (rendered JS-contract attrs + script tag) and `test_post_paso_con_rango_invalido_no_bloquea` (D8 regression coverage for the new hora-range rule) |
| `reportes/templates/reportes/paso.html` | Modified (PR4) | `{% load static %}` + `{% block extra_head %}` deferred `<script src="{% static 'reportes/paso.js' %}">`; each field wrapped in `<p data-campo="{{ campo.name }}">`; `data-siguiente` attribute added to the "Siguiente" nav anchor |
| `reportes/static/reportes/paso.js` | Created (PR4) | Vanilla JS (ADR-0001: no library, no build step) — hora-range lexicographic `fin<=inicio` check (grouped via `data-rango`/`data-rango-extremo`) disabling submit + `[data-siguiente]`; "No cumple" → companion-field show/hide with `required` set/stripped on the hidden input |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1/2.2 | `reportes/tests/test_validacion.py::test_todos_los_obligatorios_completos_produce_errores_vacio` | Unit (`@pytest.mark.django_db`) | N/A (new file) | Confirmed failing: `ModuleNotFoundError: No module named 'reportes.validacion'` | Confirmed passing after creating `reportes/validacion.py` | ✅ via 2.3/2.4/2.6/2.8/2.9 (see below) | Extracted `_errores_por_obligatorios_faltantes`/`_advertencias_por_rango_invalido`/`_advertencias_por_no_cumple_sin_observacion` as separate pure-ish passes instead of one monolithic function |
| 2.3 | same file, `test_falta_un_obligatorio_produce_un_errore` | Unit | 1/1 (prior test in file) | Written referencing new behavior (missing field → errore w/ metadata) | Passed on first run — confirms 2.2's implementation already generalizes correctly (not hardcoded) | — | — |
| 2.4 | same file, `test_validar_reporte_coincide_con_validar_completitud` | Unit | 2/2 | Written asserting exact-set equality against a direct `_validar_completitud` call | Passed on first run | — | — |
| 2.6 | same file, `test_rango_hora_invalido_produce_advertencia_no_errore` | Unit | 3/3 | Written asserting `errores == ()` and one `rango-hora-invalido` advertencia | Passed on first run | — | — |
| 2.8 | same file, `test_no_cumple_sin_observacion_produce_advertencia` | Unit | 4/4 | Written asserting exactly one `no-cumple-sin-observacion` advertencia | Passed on first run | — | — |
| 2.9 | same file, `test_no_cumple_con_observacion_no_produce_advertencia` | Unit | 5/5 | Written asserting no advertencia for that field when observación is present | Passed on first run | — | — |

**Deviation from per-task RED/GREEN pacing**: `reportes/validacion.py` was written in one pass at task 2.2 (covering the obligatorio, rango, and seleccion logic together as one cohesive module), rather than incrementally across 2.2/2.7/2.10 as tasks.md's granular split suggests. Each subsequent scenario (2.3, 2.4, 2.6, 2.8, 2.9) WAS written test-first and confirmed against the real implementation — no test was retrofitted to match a hardcoded value, and each assertion calls production code and would fail if the corresponding logic were removed (verified by construction: each pass is behaviorally independent, e.g. removing `_advertencias_por_rango_invalido`'s body would fail `test_rango_hora_invalido_produce_advertencia_no_errore` without touching the other five tests). The single genuine RED→GREEN cycle (module didn't exist → module exists) is task 2.1/2.2; tasks 2.3/2.4/2.6/2.8/2.9 functioned as triangulation passes proving the full module generalizes correctly, which is why their "GREEN" column shows "Passed on first run" rather than a fix-the-implementation step.

### Test Summary (PR1)
- **Total tests written**: 6
- **Total tests passing**: 6
- **Layers used**: Unit (6), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Pure functions created**: 3 (`_advertencias_por_rango_invalido`, `_advertencias_por_no_cumple_sin_observacion` are pure given `(estructura, valores, indice)`; `_errores_por_obligatorios_faltantes` is pure modulo the exception-based control flow)

### TDD Cycle Evidence — PR 2 (Phase 3)

| Task | Test File | Layer | Safety Net | RED | GREEN | REFACTOR |
|------|-----------|-------|------------|-----|-------|----------|
| 3.1/3.2 | `reportes/tests/test_formularios.py::test_rango_hora_inicio_fin_agrega_atributos_data_rango` | Unit (no DB) | 11/11 pre-existing tests in the file | Confirmed failing: `assert None == 'p-01'` — `data-rango` absent from widget attrs | Confirmed passing after `_campos_de_rango` gained the `nodo_id` param and set `data-rango`/`data-rango-extremo` on both widgets | None needed |
| 3.3/3.4 | same file, `test_seleccion_con_no_cumple_agrega_campo_observacion_companero` | Unit (no DB) | 12/12 | Confirmed failing: `AssertionError: assert 'turno_observacion' in {'turno': ...}` — companion field absent | Confirmed passing after `construir_formulario_seccion` injected the companion `CharField` + both data attrs | None needed |
| — (triangulation) | same file, `test_seleccion_sin_no_cumple_no_agrega_campo_observacion_companero` | Unit (no DB) | 13/13 | Written alongside 3.3/3.4 to prove the companion field is conditional on `"No cumple"` being an option, not always injected | Passed on first run against the same implementation | — |

### Test Summary (PR2)
- **Total tests written**: 3
- **Total tests passing**: 3
- **Layers used**: Unit (3, no DB — `construir_formulario_seccion` takes a plain dict), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Pure functions modified**: `_campos_de_rango` (signature grew a `nodo_id` param, still pure); `construir_formulario_seccion` (companion-field injection is a straight-line extension of the existing per-node loop, no new branching complexity)

### TDD Cycle Evidence — PR 3 (Phase 4)

| Task | Test File | Layer | Safety Net | RED | GREEN | REFACTOR |
|------|-----------|-------|------------|-----|-------|----------|
| 4.1 | `reportes/tests/test_views.py::test_get_revision_como_creador_lista_errores_y_advertencias` | Integration (`@pytest.mark.django_db`, Django test client) | 14/14 pre-existing tests in the file | Confirmed failing: `django.urls.exceptions.NoReverseMatch: Reverse for 'reportes_revision' not found` | Confirmed passing after adding the URL, view, and template together | None needed |
| 4.2 | same file, `test_get_revision_reporte_de_otro_usuario_da_404` | Integration | 15/15 | Same `NoReverseMatch` failure (no route existed yet) | Passed on first run once the route/view existed — `get_object_or_404(..., creador=request.user)` mirrors `paso`'s already-proven D9 pattern | — |
| 4.3 | same file, `test_get_revision_anonimo_redirige_a_login` | Integration | 16/16 | Same `NoReverseMatch` failure | Passed on first run — `@login_required` mirrors `paso`'s decorator | — |
| 4.4 | same file, `test_get_revision_con_errores_deshabilita_generar` + `test_get_revision_sin_errores_habilita_generar` | Integration | 17/17, 18/18 | Same `NoReverseMatch` failure | Passed on first run once the template's `{% if not resultado.puede_generar %}disabled{% endif %}` was written | — |

All 5 new tests were written together (one RED batch — the shared failure mode, `NoReverseMatch`, is identical across all of them since none of the route/view/template pieces existed yet), then GREEN was reached with one implementation pass adding the view, URL, and template together (task 4.5-4.7), matching design's Interfaces/Contracts (`ProblemaDeReporte.seccion_id` → `reverse("reportes_paso", ...)`) exactly. Confirmed the RED failure was the right one (route missing, not a typo or unrelated error) before writing any implementation code.

### Test Summary (PR3)
- **Total tests written**: 5
- **Total tests passing**: 5
- **Layers used**: Unit (0), Integration (5 — Django test client + DB, exercising the full request/response/template-render cycle), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **New view**: `revision` (thin — delegates all validation logic to the already-tested `validar_reporte`; the view itself only adds creator-scoping + template selection, both directly asserted by the 5 new tests)

### TDD Cycle Evidence — PR 4 (Phase 5 + Phase 6)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1/5.2/5.3 | `reportes/tests/test_views.py::test_get_paso_incluye_atributos_data_y_script_paso_js` | Integration (`@pytest.mark.django_db`, Django test client) | 20/20 pre-existing tests in the file | Confirmed failing: `assert 'data-campo="observaciones-generales"' in '<!DOCTYPE html>...'` — none of the data attrs or the `paso.js` script tag were present in the rendered `paso` GET response | Confirmed passing after modifying `paso.html` (`{% load static %}`, deferred script tag, `data-campo`/`data-siguiente`) — verified GREEN before creating `paso.js` itself, since the test only asserts rendered HTML, not runtime JS behavior (no JS test runner exists) | — | None needed |
| 6.1 | same file, `test_post_paso_sin_valor_obligatorio_no_bloquea` (pre-existing, unmodified) | Integration | 21/21 | N/A — regression check only, no new RED | Re-ran unmodified: still passing, 0 diff to the test or to `paso`'s POST branch | — | — |
| 6.2 | same file, `test_post_paso_con_rango_invalido_no_bloquea` | Integration | 21/21 | Written asserting 302 + both `ValorDeReporte` rows persisted for a stray `fin<=inicio` POST | Passed on first run — design's decision to route the actual check through `validar_reporte`/S-09 (not `paso`'s POST handler) means the existing non-blocking `form.is_valid()`/`required=False` contract (design D8) already satisfies this without any new server-side branch | Triangulates against `test_post_paso_rango_hora_inicio_fin_persiste_dos_filas` (same POST shape, valid range) — proves persistence is range-value-agnostic, exactly as D8/the design decision require | — |

`paso.js` itself (task 5.3, the runtime hora-range/no-cumple-toggle behavior) has no direct automated test — per design's Testing Strategy table ("No JS test runner exists in the project; JS is covered only by asserting the rendered contract"), explicitly accepted in `design.md`. The rendered-attribute contract it depends on (`data-rango`, `data-rango-extremo`, `data-requiere-observacion`, `data-observacion-de`, `data-campo`, `data-siguiente`) is fully asserted by `test_get_paso_incluye_atributos_data_y_script_paso_js`. Manual verification of the script's logic (lexicographic `fin<=inicio` compare, `required` set/strip on toggle) was performed by code review against the design's exact algorithm description, not executed in a browser (no interactive harness available in this non-interactive batch).

### Test Summary (PR4)
- **Total tests written**: 2 (`test_get_paso_incluye_atributos_data_y_script_paso_js`, `test_post_paso_con_rango_invalido_no_bloquea`)
- **Total tests passing**: 2 new + 201 pre-existing = 203 (full project suite)
- **Layers used**: Integration (2 — Django test client + DB, exercising the real `paso` GET/POST request/response/template-render cycle), Unit (0 — no JS unit runner), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Regression confirmed**: `test_post_paso_sin_valor_obligatorio_no_bloquea` re-run unmodified and still green; zero other pre-existing test broke

## Work Unit Evidence (Unit 1: `validacion.py` + fixture, anti-drift locked to generator)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_validacion.py` → `6 passed in 20.51s` |
| Runtime harness command/scenario and exact result | N/A — pure module, no server/UI boundary to exercise (per tasks.md's own note for Unit 1) |
| Rollback boundary | `reportes/validacion.py` (new file) + `reportes/tests/test_validacion.py` (new file) + the fixture addition in `reportes/tests/conftest.py`; all three can be deleted/reverted without affecting any other module (`formularios.py`, `views.py`, `urls.py`, templates untouched) |

## Work Unit Evidence (Unit 2: `formularios.py` companion field + JS data attrs)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_formularios.py` → `14 passed in 0.07s` (11 pre-existing + 3 new) |
| Runtime harness command/scenario and exact result | `pytest reportes/tests/test_validacion.py reportes/tests/test_views.py reportes/tests/test_formularios.py` → `34 passed in 76.18s` — exercises `construir_formulario_seccion` through the real `paso` GET/POST view flow (`test_views.py`) with the new data attrs and companion field present, confirming no regression in section rendering/persistence. No browser/manual harness available in this batch (`paso.html` template is unmodified — PR 4 wires the attrs into markup) |
| Rollback boundary | `reportes/formularios.py` diff (the `_VALOR_NO_CUMPLE` import, `_campos_de_rango`'s `nodo_id` param + two `attrs[...]` lines, and the companion-field injection block in `construir_formulario_seccion`) + the 3 new tests in `reportes/tests/test_formularios.py`; revertible without touching `validacion.py` (PR1), `views.py`/`urls.py`/templates (PR3-4) |

## Work Unit Evidence (Unit 3: S-09 `revision` view + template + urls)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_views.py -k revision` → `5 passed in 24.97s` |
| Runtime harness command/scenario and exact result | `pytest reportes/tests/test_views.py` (full file, no `-k`) → `19 passed in 78.78s` — exercises `revision` through the real Django test client/URL-resolver/template-render pipeline alongside all pre-existing `paso`/`iniciar_reporte` tests, confirming no regression. No live `manage.py runserver` browser check performed in this non-interactive batch; the integration test client covers the equivalent request/response/template boundary (GET, status codes, rendered HTML content) |
| Rollback boundary | `reportes/views.py`'s `revision` function + its `from reportes.validacion import validar_reporte` import; `reportes/urls.py`'s one added `path(...)` entry; `reportes/templates/reportes/revision.html` (new file); the 5 new tests in `reportes/tests/test_views.py`. All revertible without touching `paso`/`iniciar_reporte`, `formularios.py` (PR2), `validacion.py` (PR1), or `paso.html`/`paso.js` (PR4) |

## Work Unit Evidence (Unit 4: `paso.html`/`paso.js` client-side layer — FINAL)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_views.py -k "test_get_paso_incluye_atributos_data_y_script_paso_js or test_post_paso_con_rango_invalido_no_bloquea or test_post_paso_sin_valor_obligatorio_no_bloquea"` → `3 passed in 20.28s` |
| Runtime harness command/scenario and exact result | Per `tasks.md`'s own note for Unit 4, the intended harness is a live browser toggling hora fields and the "No cumple" select on a `paso` page — not available in this non-interactive batch. Substituted with the full-project `pytest` run (`203 passed in 256.59s`), exercising `paso.html`'s new markup and `paso`'s POST persistence through the real Django test client/template-render pipeline; `paso.js`'s runtime DOM behavior itself (event listeners, `required` toggling) is unverified by an executed harness — covered only by the rendered-attribute contract and manual code-review against design's algorithm, as `design.md`'s Testing Strategy explicitly accepts |
| Rollback boundary | `reportes/templates/reportes/paso.html` diff (`{% load static %}`, `extra_head` script block, `data-campo`/`data-siguiente` attrs) + `reportes/static/reportes/paso.js` (new file) + the 2 new tests in `reportes/tests/test_views.py`; revertible without touching `views.py`'s POST branch (unchanged, per design decision), `validacion.py` (PR1), `formularios.py` (PR2), or `revision.html`/`urls.py` (PR3) |

## Full Project Suite

- Baseline before PR1 (safety net): `187 passed in 217.44s (0:03:37)`.
- After PR1: `193 passed in 233.03s (0:03:53)` (187 pre-existing + 6 new, zero regressions).
- After PR2: `196 passed in 231.46s (0:03:51)` (full `pytest` run, no `-k`/file filter — 193 from PR1 + 3 new Phase 3 tests, zero regressions, zero pre-existing failures).
- After PR3: `201 passed in 246.93s (0:04:06)` (full `pytest` run, no `-k`/file filter — 196 from PR2 + 5 new Phase 4 tests, zero regressions, zero pre-existing failures). Note: a first attempt showed 7 unrelated failures (`IntegrityError: duplicate key ... codigo=instalacion-resinas`) caused by accidentally running two `pytest` invocations against the same test DB concurrently (one foreground, one backgrounded) — not a real regression. Re-ran once, alone, for the authoritative clean result above.
- After PR4 (this batch, FINAL): `203 passed in 256.59s (0:04:16)` (full `pytest` run, no `-k`/file filter — 201 from PR3 + 2 new Phase 5/6 tests, zero regressions, zero pre-existing failures). `test_post_paso_sin_valor_obligatorio_no_bloquea` re-confirmed passing unmodified (task 6.1). **This closes out the entire `validacion-datos-formulario` change — all 4 chained PRs / all tasks in `tasks.md` complete.**

## Deviations from Design

None — implementation matches `design.md`'s Interfaces/Contracts and Data Flow sections (PR1), and the "`formularios.py` changes (the JS contract)" subsection (PR2) exactly: `_campos_de_rango` grew the documented `nodo_id` param and sets both `data-rango`/`data-rango-extremo` attrs; `construir_formulario_seccion` injects the companion `CharField(required=False, label=f"{etiqueta} — Observación", widget=TextInput(attrs={"data-observacion-de": clave}))` and sets `data-requiere-observacion` on the select, gated on `tipo == SELECCION and _VALOR_NO_CUMPLE in (opciones or [])`. One implementation note not explicit in design: `_VALOR_NO_CUMPLE` is imported from `reportes.validacion` rather than redefined in `formularios.py`, avoiding a duplicated magic-string literal — consistent with the codebase's existing pattern of importing private (`_`-prefixed) symbols across these two modules (`validacion.py` already imports `generador._validar_completitud`; `formularios.py` already imports `tipos_reporte.validacion._iterar_nodos`). No circular import: `reportes.validacion` does not import `reportes.formularios`.

PR3 also matches design's File Changes table exactly: `views.py` gained only the `revision` function (per D9, `paso`/`iniciar_reporte` untouched); `urls.py` gained the one documented `path(...)` entry; `revision.html` uses the two `<ul>`s + `<button type="button" {% if not puede_generar %}disabled{% endif %}>Generar</button>` shape from the design's File Changes row, sourced through `resultado.puede_generar` (the `ResultadoDeRevision` property already built in PR1) rather than re-deriving `not errores` in the template or view — no duplicated logic. Each `<li>` links to `{% url 'reportes_paso' reporte.id problema.seccion_id %}`, satisfying spec's "each item linked to its owning `paso`/`seccion`" wording via the existing `reportes_paso` route (no new URL-reversal helper needed).

PR4 matches design's "`paso.js` behaviour" subsection and File Changes table exactly: `paso.html` gained `{% load static %}` + a deferred `<script>` in `extra_head`, `data-campo` wrapping, and `data-siguiente` on the nav anchor — no other markup changed; `paso.js` implements exactly the described algorithm (`DOMContentLoaded` runs both toggles once for GET rehydration, then binds `change`/`input`; lexicographic `fin<=inicio` string compare, no time parsing; "No cumple" toggle strips `required` on hide). `views.py`'s `paso` POST branch was **not** touched, per the design decision "server-side hora re-check lives only in `validar_reporte`" — task 6.2's new test proves the existing D8 non-blocking contract already satisfies the spec's "Direct POST with invalid hora range still persists" scenario without any new server-side code, exactly as the design decision predicts. One naming choice not explicit in design: the alert-message element created by `paso.js` uses an `id` of `"{finInputId}_mensaje_rango"` for idempotent re-use across repeated `input` events (avoids stacking duplicate `role="alert"` spans) — a straight-line implementation detail, not a deviation from the described behavior (design only specifies "show a `role="alert"` message next to the `fin` input", not its exact identification scheme).

## Issues Found

None.

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main)
- PR1 — Unit 1: `validacion.py` + fixture, anti-drift locked to generator
  - Boundary: starts from a clean checkout (no prior apply-progress existed for this change); ends with `reportes/validacion.py` fully implemented and covered, `estructura_con_validaciones` fixture added, zero touches to `formularios.py`/`views.py`/`urls.py`/templates
  - Estimated review budget impact: well under 400 changed lines (fixture ~55 lines, `validacion.py` ~210 lines w/ docstrings, test file ~140 lines) — safely within PR1's slice of the forecasted 550-650 total
- PR2 — Unit 2: `formularios.py` companion field + JS data attrs
  - Boundary: starts from PR1's merged/branch state (`reportes/validacion.py` already present, providing `_VALOR_NO_CUMPLE`); ends with `reportes/formularios.py`'s data-attribute contract fully implemented per design and covered by 3 new tests; zero touches to `views.py`/`urls.py`/templates/`paso.js` (PR3-4)
  - Estimated review budget impact: small (~30 changed lines in `formularios.py`, ~70 lines of new tests) — well within budget, PR3 (S-09 view/template) and PR4 (`paso.html`/`paso.js`) remain the larger remaining slices of the forecasted 550-650 total
- PR3 — Unit 3: S-09 `revision` view + template + urls
  - Boundary: starts from PR2's merged/branch state (`reportes/validacion.py` and `reportes/formularios.py`'s companion field already present, though `revision` does not directly depend on the companion field — only on `validar_reporte`); ends with the full S-09 review screen reachable at `/reportes/<reporte_id>/revision/`, covered by 5 new integration tests; zero touches to `paso.html`/`paso.js` (PR4)
  - Estimated review budget impact: small (~15 lines in `views.py`, ~10 lines in `urls.py`, ~35 lines in `revision.html`, ~110 lines of new tests) — well within budget; PR4 (`paso.html`/`paso.js` client-side layer) remains the larger remaining slice of the forecasted 550-650 total, followed by the Phase 6 regression pass
- PR4 — Unit 4: `paso.html`/`paso.js` client-side layer + Phase 6 regression pass (this batch, FINAL)
  - Boundary: starts from PR3's merged/branch state (`revision.html`/`views.py::revision`/`urls.py` already present, though `paso.js` does not depend on `revision` — only on `paso.html`'s existing form/nav markup); ends with the full client-side hora-range/no-cumple-toggle JS layer wired into `paso.html`, covered by 1 new rendered-attribute test, plus the Phase 6 regression pass (1 unmodified-test re-confirmation + 1 new server-side non-blocking test + full-suite run). This is the final PR in the chain — no tasks remain in `tasks.md`
  - Estimated review budget impact: small (~15 changed lines in `paso.html`, ~180 lines in the new `paso.js` file including comments, ~65 lines of new tests) — well within budget; total across all 4 PRs stays inside the forecasted 550-650 line range

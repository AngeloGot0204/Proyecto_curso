# Apply Progress: validacion-datos-formulario

## Scope of this batch (PR 1 of 4)

Phase 1 (fixture foundation) + Phase 2 (`validar_reporte` core, all 6 spec
scenarios + anti-drift lock). Did NOT touch `formularios.py`, `views.py`,
`urls.py`, or templates — those belong to PR 2-4 per the chained-PR plan.

**Chain strategy**: stacked-to-main. This PR targets `main`; PR 2 will
target this PR's branch once merged (or `main` after merge).

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

## Remaining Tasks (out of scope for this batch — PR 2-4)

- [ ] Phase 3: `formularios.py` companion field (3.1-3.4)
- [ ] Phase 4: S-09 review screen (4.1-4.7)
- [ ] Phase 5: Client-side JS layer (5.1-5.3)
- [ ] Phase 6: Regression (6.1-6.3, full-project run already exceeded by this batch's own full-suite check — repeat once PR2-4 land)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/tests/conftest.py` | Modified | Added `estructura_con_validaciones` fixture (obligatorio `texto`, `seleccion` with `["Cumple","No cumple"]`, obligatorio `rango-hora-inicio-fin`) |
| `reportes/validacion.py` | Created | `ProblemaDeReporte`, `ResultadoDeRevision`, `_indice_de_campos`, `validar_reporte` — obligatorio pass via `generador._validar_completitud`/`ValoresIncompletos` exception translation (zero drift), rango-hora advertencia pass, "No cumple" advertencia pass |
| `reportes/tests/test_validacion.py` | Created | 6 tests, one per spec scenario, covering `validar_reporte` |

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

### Test Summary
- **Total tests written**: 6
- **Total tests passing**: 6
- **Layers used**: Unit (6), Integration (0), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Pure functions created**: 3 (`_advertencias_por_rango_invalido`, `_advertencias_por_no_cumple_sin_observacion` are pure given `(estructura, valores, indice)`; `_errores_por_obligatorios_faltantes` is pure modulo the exception-based control flow)

## Work Unit Evidence (Unit 1: `validacion.py` + fixture, anti-drift locked to generator)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_validacion.py` → `6 passed in 20.51s` |
| Runtime harness command/scenario and exact result | N/A — pure module, no server/UI boundary to exercise (per tasks.md's own note for Unit 1) |
| Rollback boundary | `reportes/validacion.py` (new file) + `reportes/tests/test_validacion.py` (new file) + the fixture addition in `reportes/tests/conftest.py`; all three can be deleted/reverted without affecting any other module (`formularios.py`, `views.py`, `urls.py`, templates untouched) |

## Full Project Suite

- Baseline (before this batch's changes, safety net): `187 passed in 217.44s (0:03:37)`.
- After this batch: `193 passed in 233.03s (0:03:53)` (full `pytest` run, no `-k`/file filter — 187 pre-existing + 6 new, zero regressions, zero pre-existing failures).

## Deviations from Design

None — implementation matches `design.md`'s Interfaces/Contracts and Data Flow sections exactly: `ProblemaDeReporte`/`ResultadoDeRevision` dataclass shapes, `_VALOR_NO_CUMPLE`/`_SUFIJO_DE_ETIQUETA` module constants, the `try/except ValoresIncompletos` exception-translation pattern, and the documented algorithm order (obligatorio pass → rango pass → seleccion pass).

## Issues Found

None.

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main)
- Current work unit: Unit 1 — `validacion.py` + fixture, anti-drift locked to generator
- Boundary: starts from a clean checkout (no prior apply-progress existed for this change); ends with `reportes/validacion.py` fully implemented and covered, `estructura_con_validaciones` fixture added, zero touches to `formularios.py`/`views.py`/`urls.py`/templates
- Estimated review budget impact: well under 400 changed lines (fixture ~55 lines, `validacion.py` ~210 lines w/ docstrings, test file ~140 lines) — safely within PR1's slice of the forecasted 550-650 total

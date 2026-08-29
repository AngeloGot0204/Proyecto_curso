# Apply Progress: Cierre manual (visto bueno) y generación del documento

## Batch 1 (this run) — Work Unit 1 / PR 1

**Scope**: Phase 1 (Models & Migrations), Phase 2 (Shared Valores Helper refactor), Phase 3 task 3.1 only (`plantilla_xlsx` fixture). `cerrar_reporte`, `generar`, and template wiring (Phases 4-6, task 3.2) are explicitly deferred to PR 2/PR 3 per the assigned work-unit boundary.

### Completed Tasks

- [x] 1.1 RED: `test_estado_de_reporte_admite_terminado`
- [x] 1.2 GREEN: `EstadoDeReporte.TERMINADO`
- [x] 1.3 `reportes/migrations/0002_estado_terminado.py`
- [x] 1.4 RED: `test_visto_bueno_defaults_y_auto_now_add`, `test_segundo_visto_bueno_lanza_integrity_error`, `test_generacion_permite_multiples_filas`
- [x] 1.5 GREEN: `VistoBueno`, `Generacion` models
- [x] 1.6 `reportes/migrations/0003_vistobueno_generacion.py`
- [x] 1.7 `pytest reportes/tests/test_models.py -q` → 8 passed
- [x] 2.1 RED: `test_valores_de_reporte_construye_dict_desde_filas`, `test_valores_de_reporte_reporte_vacio_retorna_dict_vacio`
- [x] 2.2 GREEN: `reportes/valores.py::valores_de_reporte`
- [x] 2.3 REFACTOR: `reportes/validacion.py::validar_reporte` uses `valores_de_reporte`
- [x] 2.4 REFACTOR: `reportes/views.py::paso` uses `valores_de_reporte`; dropped now-unused `ValorDeReporte` import
- [x] 2.5 `pytest reportes/tests/ -k "validar_reporte_coincide_con_validar_completitud or paso" -q` → 14 passed
- [x] 3.1 `plantilla_xlsx(tmp_path)` fixture added to `reportes/tests/conftest.py`, with a dedicated RED→GREEN test (`test_conftest_plantilla_xlsx.py`) since it did not exist as a task-3.1 assertion in tasks.md but is required by strict TDD for any new fixture behavior
- [x] 3.3 (scoped) `pytest reportes/tests/ -q` smoke check → no regressions

### Deferred (out of scope for this PR 1 batch)

- [ ] 3.2 `reporte_listo_para_cerrar` fixture — deferred to PR 2 (`cerrar_reporte` work unit)
- [ ] Phase 4 — `cerrar_reporte` view (PR 2)
- [ ] Phase 5 — `generar` view (PR 3)
- [ ] Phase 6 — Template & Messages wiring (PR 3)
- [ ] Phase 7 — Full regression & cleanup (final PR, after PR 2/PR 3 land)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/models.py` | Modified | Added `EstadoDeReporte.TERMINADO`; added `VistoBueno` (`OneToOneField(Reporte)`); added `Generacion` (`ForeignKey(Reporte)`, unbounded) |
| `reportes/migrations/0002_estado_terminado.py` | Created | `AlterField` on `Reporte.estado` — choices-only, no DDL |
| `reportes/migrations/0003_vistobueno_generacion.py` | Created | `CreateModel` × 2 (`Generacion`, `VistoBueno`) |
| `reportes/valores.py` | Modified | Added `valores_de_reporte(reporte) -> dict[str, str]` |
| `reportes/validacion.py` | Modified | `validar_reporte` now calls `valores_de_reporte(reporte)` instead of the inline comprehension |
| `reportes/views.py` | Modified | `paso`'s GET rehydration now calls `valores_de_reporte(reporte)`; dropped unused `ValorDeReporte` import |
| `reportes/tests/conftest.py` | Modified | Added `plantilla_xlsx(tmp_path)` factory fixture (mirrors `tipos_reporte/tests/conftest.py`) |
| `reportes/tests/test_models.py` | Modified | Added TERMINADO/VistoBueno/Generacion tests; updated import to include `Generacion`, `VistoBueno` |
| `reportes/tests/test_valores.py` | Modified | Added `valores_de_reporte` tests; updated import |
| `reportes/tests/test_conftest_plantilla_xlsx.py` | Created | RED→GREEN test proving `plantilla_xlsx` builds a real, loadable workbook with the requested sheet/merged ranges |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1/1.2 | `reportes/tests/test_models.py` | Unit | ✅ 62/62 (project baseline, `reportes/` suite) | ✅ Written — `AttributeError: type object 'EstadoDeReporte' has no attribute 'TERMINADO'` | ✅ Passed | ➖ Single (structural TextChoices member; no branching) | ➖ None needed |
| 1.4/1.5 | `reportes/tests/test_models.py` | Unit (DB) | ✅ (same baseline) | ✅ Written — `ImportError: cannot import name 'Generacion'` | ✅ Passed (8/8 in file) | ✅ 3 cases (defaults/auto_now_add, IntegrityError on second VistoBueno, N Generacion rows) | ➖ None needed — models are declarative |
| 2.1/2.2 | `reportes/tests/test_valores.py` | Unit (DB) | ✅ (existing 17 tests in file) | ✅ Written — `ImportError: cannot import name 'valores_de_reporte'` | ✅ Passed (19/19 in file) | ✅ 2 cases (non-empty dict from rows, empty dict from empty report) | ➖ None needed — single dict comprehension |
| 2.3/2.4 | `reportes/tests/test_validacion.py`, `reportes/tests/test_views.py` | Approval (refactor) | ✅ Existing tests ARE the approval tests — ran before touching `validacion.py`/`views.py` | N/A — refactor task, behavior-preserving by design D5 | ✅ 14/14 passed after refactor (`validar_reporte_coincide_con_validar_completitud` + all `paso` tests) | N/A (refactor, no new behavior) | ✅ Extracted duplication into shared `valores_de_reporte` |
| 3.1 | `reportes/tests/test_conftest_plantilla_xlsx.py` | Unit | ✅ (new file) | ✅ Written — `fixture 'plantilla_xlsx' not found` | ✅ Passed | ➖ Single (fixture mirrors an already-tested upstream pattern in `tipos_reporte`) | ➖ None needed |

### Test Summary

- **Total tests written this batch**: 7 (1 model/estado + 3 model/visto-bueno-generacion + 2 valores + 1 fixture)
- **Total tests passing (`reportes/` full suite)**: 69 (baseline 62 + 7 new — confirmed via `pytest reportes/ -q`)
- **Layers used**: Unit (all — Django ORM model/queryset tests run against the test DB, consistent with this repo's existing pattern)
- **Approval tests**: 2 files reused as approval tests for the Phase 2 refactor (`test_validacion.py`, relevant `test_views.py` `paso` tests) — 14 passed unchanged
- **Pure functions created**: 1 (`valores_de_reporte`)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_models.py reportes/tests/test_valores.py -q` → all passing (8 + 19 = 27 passed in those two files alone) |
| Runtime harness command/scenario and exact result | `pytest`'s `--reuse-db` (pytest-django) ran `migrate` against the real test Postgres/SQLite DB to apply `0002_estado_terminado` and `0003_vistobueno_generacion` before any test executed — this IS the "migrate on a scratch DB" harness the tasks artifact specifies; migrations applied cleanly with no errors. Confirmed additionally via `manage.py makemigrations --check --dry-run --skip-checks` → "No changes detected" (models and migrations are in sync). |
| Rollback boundary | Revert `reportes/migrations/0002_estado_terminado.py`, `reportes/migrations/0003_vistobueno_generacion.py`, the `models.py` additions (`TERMINADO`, `VistoBueno`, `Generacion`), `valores.py::valores_de_reporte`, the `validacion.py`/`views.py` call-site swaps, and the new/modified test files. No data migration or backfill exists — existing `Reporte` rows keep `estado="en_progreso"`; `VistoBueno`/`Generacion` tables are empty and unreferenced by any other code path in this batch. |

## Full Suite Confirmation

- `pytest reportes/ -q` (baseline, before this batch): **62 passed**
- `pytest reportes/ -q` (after this batch): **69 passed** in 131.84s
- `pytest -q` (full project suite, after this batch): **210 passed** in 266.92s
- `test_validar_reporte_coincide_con_validar_completitud` confirmed passing unchanged after the `valores_de_reporte` refactor (part of the 14/14 run above).

## Deviations from Design

None — implementation matches design.md exactly:
- `EstadoDeReporte.TERMINADO = "terminado", "Terminado"` (Interfaces/Contracts)
- `VistoBueno`/`Generacion` field shapes, `on_delete` choices, and `related_name`s match the design's Interfaces/Contracts block verbatim
- Migration 0002 is `AlterField` (choices-only); migration 0003 is `CreateModel` × 2 (Migration/Rollout section)
- `valores_de_reporte(reporte) -> dict[str, str]` signature and body match design D5 exactly

One addition beyond the literal task list: task 3.1 in tasks.md did not itself specify a test, but strict TDD requires a failing test before any new production/test-infrastructure behavior, so `test_conftest_plantilla_xlsx.py` was added to prove the fixture's construction is real (not asserted elsewhere yet, since `reporte_listo_para_cerrar` — the fixture that will consume it in PR 2 — is deferred).

## Issues Found

None.

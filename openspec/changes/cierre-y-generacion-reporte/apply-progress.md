# Apply Progress: Cierre manual (visto bueno) y generación del documento

## Batch 1 — Work Unit 1 / PR 1 (merged)

**Scope**: Phase 1 (Models & Migrations), Phase 2 (Shared Valores Helper refactor), Phase 3 task 3.1 only (`plantilla_xlsx` fixture).

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
- [x] 3.1 `plantilla_xlsx(tmp_path)` fixture added to `reportes/tests/conftest.py`, with a dedicated RED→GREEN test (`test_conftest_plantilla_xlsx.py`)
- [x] 3.3 (scoped) `pytest reportes/tests/ -q` smoke check → no regressions

## Batch 2 (this run) — Work Unit 2 / PR 2

**Scope**: task 3.2 (`reporte_listo_para_cerrar` fixture, deferred from PR 1) + Phase 4 (`cerrar_reporte` view). `generar`, its template wiring, and Phases 5-7 remain deferred to PR 3.

### Completed Tasks

- [x] 3.2 `reporte_listo_para_cerrar` fixture added to `reportes/tests/conftest.py`: `(client, reporte)` built on `estructura_con_validaciones` with a real `plantilla_xlsx` (`rangos=("M10:P10", "M12:P12", "M25:P25")`), the creador logged in, and all four obligatorio `ValorDeReporte` rows persisted (`observaciones-generales="Todo en orden."`, `estado-general="Cumple"`, `p-01_inicio="08:00"`, `p-01_fin="09:00"`) so `puede_generar` is true.
- [x] 4.1 RED: `test_cerrar_reporte_no_creador_devuelve_404`
- [x] 4.2 RED: `test_cerrar_reporte_rechazado_si_no_puede_generar`
- [x] 4.3 RED: `test_cerrar_reporte_creador_exitoso` (uses `reporte_listo_para_cerrar`)
- [x] 4.4 RED: `test_cerrar_reporte_doble_post_es_idempotente`
- [x] 4.5 GREEN: `reportes/urls.py` — `path("<int:reporte_id>/cerrar/", views.cerrar_reporte, name="reportes_cerrar")`
- [x] 4.6 GREEN: `reportes/views.py` — module-level `logger = logging.getLogger(__name__)`; `cerrar_reporte` implemented per design (creator-scoped `get_object_or_404`, server-side `puede_generar` re-check, `get_or_create(VistoBueno)` + `estado=TERMINADO` inside `transaction.atomic()`, redirect to `reportes_revision` with flash message on both paths)
- [x] 4.7 `pytest reportes/tests/test_views.py -k cerrar -q` → 4 passed

### Deferred (out of scope for this PR 2 batch)

- [ ] Phase 5 — `generar` view (PR 3)
- [ ] Phase 6 — Template & Messages wiring (PR 3)
- [ ] Phase 7 — Full regression & cleanup (final PR, after PR 3 lands)

## Files Changed (cumulative)

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/models.py` | Modified (PR 1) | Added `EstadoDeReporte.TERMINADO`; added `VistoBueno` (`OneToOneField(Reporte)`); added `Generacion` (`ForeignKey(Reporte)`, unbounded) |
| `reportes/migrations/0002_estado_terminado.py` | Created (PR 1) | `AlterField` on `Reporte.estado` — choices-only, no DDL |
| `reportes/migrations/0003_vistobueno_generacion.py` | Created (PR 1) | `CreateModel` × 2 (`Generacion`, `VistoBueno`) |
| `reportes/valores.py` | Modified (PR 1) | Added `valores_de_reporte(reporte) -> dict[str, str]` |
| `reportes/validacion.py` | Modified (PR 1) | `validar_reporte` now calls `valores_de_reporte(reporte)` instead of the inline comprehension |
| `reportes/tests/conftest.py` | Modified (PR 1: `plantilla_xlsx`; PR 2: `reporte_listo_para_cerrar`) | Added both fixtures |
| `reportes/tests/test_models.py` | Modified (PR 1) | Added TERMINADO/VistoBueno/Generacion tests |
| `reportes/tests/test_valores.py` | Modified (PR 1) | Added `valores_de_reporte` tests |
| `reportes/tests/test_conftest_plantilla_xlsx.py` | Created (PR 1) | RED→GREEN test for `plantilla_xlsx` |
| `reportes/tests/test_conftest_reporte_listo_para_cerrar.py` | Created (PR 2) | RED→GREEN test proving the fixture builds an eligible-to-close `Reporte` and logs its creador in |
| `reportes/urls.py` | Modified (PR 2) | Added `reportes_cerrar` route |
| `reportes/views.py` | Modified (PR 2) | Added `logging` import, module `logger`, `messages`/`transaction` imports; `paso`'s GET rehydration already used `valores_de_reporte` (PR 1); implemented `cerrar_reporte` |
| `reportes/tests/test_views.py` | Modified (PR 2) | Added `EstadoDeReporte`, `VistoBueno`, `get_messages` imports; added 4 `cerrar_reporte` tests |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1/1.2 | `reportes/tests/test_models.py` | Unit | ✅ 62/62 (project baseline) | ✅ Written | ✅ Passed | ➖ Single (structural) | ➖ None needed |
| 1.4/1.5 | `reportes/tests/test_models.py` | Unit (DB) | ✅ (same baseline) | ✅ Written | ✅ Passed (8/8) | ✅ 3 cases | ➖ None needed |
| 2.1/2.2 | `reportes/tests/test_valores.py` | Unit (DB) | ✅ (existing 17 in file) | ✅ Written | ✅ Passed (19/19) | ✅ 2 cases | ➖ None needed |
| 2.3/2.4 | `test_validacion.py`, `test_views.py` | Approval (refactor) | ✅ Existing tests ARE approval tests | N/A — refactor, behavior-preserving | ✅ 14/14 passed after refactor | N/A (refactor) | ✅ Extracted `valores_de_reporte` |
| 3.1 | `test_conftest_plantilla_xlsx.py` | Unit | ✅ (new file) | ✅ Written — fixture not found | ✅ Passed | ➖ Single | ➖ None needed |
| 3.2 | `test_conftest_reporte_listo_para_cerrar.py` | Integration (DB) | ✅ 69/69 (`reportes/` before this batch) | ✅ Written — `fixture 'reporte_listo_para_cerrar' not found` | ✅ Passed (1/1) | ➖ Single (fixture is a single deterministic build, mirrors the already-triangulated `plantilla_xlsx` pattern) | ➖ None needed — declarative fixture assembly |
| 4.1-4.4 | `reportes/tests/test_views.py` | Integration (DB) | ✅ 70/70 (`reportes/` after 3.2, before Phase 4) | ✅ Written — all 4 failed with `NoReverseMatch: Reverse for 'reportes_cerrar' not found` (route did not exist) | ✅ Passed (4/4) after 4.5/4.6 | ✅ 4 cases (non-creator 404, ineligible rejection, happy path, idempotent double-POST) covering every `cierre-reporte` spec scenario | ➖ None needed — view matches design's exact contract verbatim, no duplication to extract |

### Test Summary (Batch 2)

- **Total tests written this batch**: 5 (1 fixture-proof + 4 `cerrar_reporte` view tests)
- **Total tests passing (`reportes/` full suite)**: 74 (baseline 69 + 5 new — confirmed via `pytest reportes/ -q`)
- **Layers used**: Integration (all 5 — Django test client against real DB-backed views/fixtures, consistent with this repo's existing pattern)
- **Approval tests**: None — no refactoring in this batch
- **Pure functions created**: 0 (view function `cerrar_reporte` has one side-effecting DB write path, matches `paso`'s existing shape)

## Work Unit Evidence (Batch 2 / PR 2)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_views.py -k cerrar -q` → `4 passed, 21 deselected` |
| Runtime harness command/scenario and exact result | Manual POST via Django test client (per the tasks artifact's designated runtime harness for this unit) — exercised directly by all 4 `cerrar_reporte` integration tests, including the real idempotent double-POST scenario (`test_cerrar_reporte_doble_post_es_idempotente`) which sends two real sequential `client.post()` calls and asserts exactly one `VistoBueno` row plus no 500/`IntegrityError` |
| Rollback boundary | Revert `reportes/views.py::cerrar_reporte` (and its new imports: `logging`, `messages`, `transaction`, `EstadoDeReporte`, `VistoBueno`), the `reportes_cerrar` entry in `reportes/urls.py`, the `reporte_listo_para_cerrar` fixture in `reportes/tests/conftest.py`, `reportes/tests/test_conftest_reporte_listo_para_cerrar.py`, and the 4 new tests + `EstadoDeReporte`/`VistoBueno`/`get_messages` imports in `reportes/tests/test_views.py`. `VistoBueno` rows created by manual testing (if any) remain valid but unused; no data loss. PR 1's models/migrations/valores refactor stay functional standalone. |

## Full Suite Confirmation

- `pytest reportes/ -q` (baseline, before Batch 2): **69 passed**
- `pytest reportes/ -q` (after Batch 2): **74 passed** in 158.71s
- `pytest -q` (full project suite, after Batch 2, first run): **214 passed, 1 failed** — the 1 failure (`usuarios/tests/test_models.py::test_create_superuser_forces_rol_administrador`) was a transient Postgres connection drop (`OperationalError: server closed the connection unexpectedly`), unrelated to any file touched in this batch.
- `pytest -q --reuse-db` (full project suite, re-run to confirm flake): **215 passed** in 294.15s — confirms the earlier failure was infrastructure flake, not a regression.
- `manage.py makemigrations --check --dry-run --skip-checks` → "No changes detected" (no model changes in this batch; models/migrations still in sync from PR 1).

## Deviations from Design

None — implementation matches design.md exactly:
- `cerrar_reporte` body matches the Interfaces/Contracts code block verbatim (creator-scoped `get_object_or_404`, `puede_generar` re-check with `messages.error` + redirect, `transaction.atomic()` with `get_or_create` + `estado=TERMINADO` + `save(update_fields=["estado"])`, `messages.success` + redirect)
- `reporte_listo_para_cerrar` fixture matches the design's Testing Strategy "Fixtures" paragraph exactly (same field values, same template `rangos`)
- Route added exactly as specified: `path("<int:reporte_id>/cerrar/", views.cerrar_reporte, name="reportes_cerrar")`

## Issues Found

None.

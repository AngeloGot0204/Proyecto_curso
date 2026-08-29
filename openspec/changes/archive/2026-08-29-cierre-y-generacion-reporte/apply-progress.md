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

## Batch 3 (this run) — Work Unit 3 / PR 3 (FINAL)

**Scope**: Phase 5 (`generar` view), Phase 6 (template & messages wiring), Phase 7 (full regression & cleanup). This completes ALL remaining tasks in `tasks.md` — the change is now fully implemented.

### Completed Tasks

- [x] 5.1 RED: `test_generar_sin_visto_bueno_redirige_con_error`
- [x] 5.2 RED: `test_generar_rechazado_si_no_puede_generar_pese_a_visto_bueno`
- [x] 5.3 RED: `test_generar_no_creador_tambien_puede_generar`
- [x] 5.4 RED: `test_generar_captura_problema_de_generacion_y_redirige`
- [x] 5.5 RED: `test_generar_exitoso_streamea_xlsx_con_headers_correctos`
- [x] 5.6 RED: `test_generar_repetido_crea_multiples_filas_generacion`
- [x] 5.7 GREEN: `reportes/urls.py` — `path("<int:reporte_id>/generar/", views.generar, name="reportes_generar")`
- [x] 5.8 GREEN: `reportes/views.py::generar` implemented per design's exact contract (non-creator-scoped `get_object_or_404`, `VistoBueno`-exists check, `puede_generar` re-check, `try/except ProblemaDeGeneracion` with `logger.exception` + flash + redirect, `Generacion.objects.create`, `HttpResponse` with correct `Content-Type`/`Content-Disposition`)
- [x] 5.9 `pytest reportes/tests/test_views.py -k generar -q` → 6 passed
- [x] 6.1 `templates/base.html` — added the `{% if messages %}` block (previously absent entirely, confirmed by design's finding)
- [x] 6.2 RED/confirmed: `test_get_revision_sin_errores_habilita_generar` still asserts `"disabled" not in response.content` and still passes under the new template (Generar rendered conditionally, not via `disabled`, per design D4)
- [x] 6.3 RED→GREEN: `test_get_revision_con_visto_bueno_muestra_form_generar`
- [x] 6.4 RED→GREEN: `test_get_revision_no_creador_no_ve_boton_cerrar` (tested via `render_to_string` + `rf` `RequestFactory` with a non-creator `request.user`, since `revision` itself stays creator-scoped at the view level per design's "Non-creator caveat" — a non-creator can never reach `revision` through the view, so this proves the template's own defensive guard independent of that 404)
- [x] 6.5 GREEN: `reportes/views.py::revision` — added `tiene_visto_bueno` to context via `VistoBueno.objects.filter(reporte=reporte).exists()`
- [x] 6.6 GREEN: `reportes/templates/reportes/revision.html` — Generar rendered only when `tiene_visto_bueno` (real POST + `{% csrf_token %}`); Cerrar reporte rendered only when `reporte.creador_id == request.user.id`, carrying `{% if not resultado.puede_generar %}disabled{% endif %}`
- [x] 6.7 `pytest reportes/tests/test_views.py -k revision -q` → 8 passed (including both pre-existing `disabled`-assertion tests, unchanged)
- [x] 7.1 `pytest reportes/ -q` → 83 passed; `pytest -q --reuse-db` (full project, isolated run) → 224 passed
- [x] 7.2 RED→GREEN: `test_edicion_post_cierre_sigue_funcionando` — `paso` POST after `estado=TERMINADO` succeeds, no restriction
- [x] 7.3 Confirmed: `logger.exception` path in `generar`'s `except ProblemaDeGeneracion` block is exercised by `test_generar_captura_problema_de_generacion_y_redirige` (mocks `reportes.views.generador.generar_reporte` to raise `PlantillaIlegible`) and never raises; no Sentry wiring added (D6, out of scope)
- [x] 7.4 Diff size reviewed: `git diff --stat` for this batch ≈ 312 insertions / 31 deletions across 6 non-tasks.md files — within the ~400-line budget for this final work unit

### Deviation from design (fixture bug fix, not a design/spec change)

`design.md`'s Testing Strategy directs `reporte_listo_para_cerrar` to build its template with `rangos=("M10:P10", "M12:P12", "M25:P25")`. Running the actual `generar_reporte` call (first exercised in this batch — PR 2's `cerrar_reporte` tests never called it) surfaced a latent bug in that exact fixture: `estructura_con_validaciones`'s `p-01` item declares TWO independent anchor cells on the same row — `celda_inicio="M25"` and `celda_fin="P25"` — but merging `"M25:P25"` as ONE range turns `P25` into a read-only `MergedCell` (openpyxl only allows writes to a merged range's top-left/anchor cell), so `generador.generar_reporte` raised `AttributeError: 'MergedCell' object attribute 'value' is read-only` on every successful-path test. Fixed by changing `reporte_listo_para_cerrar`'s `plantilla_xlsx(...)` call to `rangos=("M10:P10", "M12:P12")` only, leaving `M25`/`P25` as two ordinary, independently-writable, unmerged cells — no change to `reportes/models.py`, `reportes/views.py`, or any production code; the fix is scoped entirely to the test fixture in `reportes/tests/conftest.py`. `design.md`'s own download-assertion example only ever asserted `M25`, never `P25`, consistent with this fix.

### Files Changed (Batch 3)

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/views.py` | Modified | Added `generar` view; `revision` now passes `tiene_visto_bueno`; new imports (`HttpResponse`, `timezone`, `Generacion`, `tipos_reporte.generador`, `ProblemaDeGeneracion`) |
| `reportes/urls.py` | Modified | Added `reportes_generar` route |
| `templates/base.html` | Modified | Added the `{% if messages %}` block |
| `reportes/templates/reportes/revision.html` | Modified | Real POST forms for Generar (conditional on `tiene_visto_bueno`) and creator-only Cerrar reporte (with `disabled` per `puede_generar`) |
| `reportes/tests/conftest.py` | Modified | Fixed `reporte_listo_para_cerrar`'s merge ranges (dropped the `M25:P25` merge that made `P25` a read-only `MergedCell`) |
| `reportes/tests/test_views.py` | Modified | Added 6 `generar` tests, 2 template-wiring tests, 1 post-closure-edit regression test; new imports |
| `openspec/changes/cierre-y-generacion-reporte/tasks.md` | Modified | Marked Phases 5-7 `[x]` |

## TDD Cycle Evidence (Batch 3)

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| 5.1-5.6 | `reportes/tests/test_views.py` | Integration (DB) | ✅ Written — all 6 failed with `NoReverseMatch: Reverse for 'reportes_generar' not found` | ✅ Passed (6/6) after 5.7/5.8 | ✅ 6 cases: no-VistoBueno, ineligible-despite-VistoBueno, non-creator success, `ProblemaDeGeneracion` capture, success headers/round-trip, repeated generation | ➖ None needed — view matches design's exact contract |
| 6.2-6.4 | `reportes/tests/test_views.py` | Integration (DB) + isolated template render | ✅ 6.3/6.4 written first — `NoReverseMatch`/missing context before 6.5/6.6; 6.2 confirmed against the already-passing pre-existing test | ✅ Passed (3/3) after 6.5/6.6 | ✅ 3 cases (Generar-present-after-closure, Cerrar-absent-for-non-creator, existing `disabled` assertions preserved) | ➖ None needed |
| 7.2 | `reportes/tests/test_views.py` | Integration (DB) | ✅ Written against `paso`, which was never touched this batch — passed immediately (approval test proving no regression), consistent with design D7 ("no task should touch `paso`'s write path") | ✅ Passed (1/1) | N/A (approval test) | ➖ None needed |

### Test Summary (Batch 3)

- **Total tests written this batch**: 10 (6 `generar` + 2 template-wiring + 1 post-closure-edit regression + 1 already-existing assertion re-confirmed)
- **Total tests passing (`reportes/` full suite)**: 83 (baseline 74 + ~9 net new — confirmed via `pytest reportes/ -q`)
- **Total tests passing (full project, isolated single-process run)**: 224 (`pytest -q --reuse-db`)
- **Layers used**: Integration (Django test client + real Postgres DB), one isolated template-render test via `RequestFactory`/`render_to_string` for the non-creator Cerrar-button guard
- **Pure functions created**: 0

## Work Unit Evidence (Batch 3 / PR 3, FINAL)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_views.py -k "generar or revision" -q` → `17 passed, 17 deselected` |
| Runtime harness command/scenario and exact result | Manual POST via Django test client for `generar` (matches the tasks artifact's designated runtime harness), including the real download round-trip: `load_workbook(BytesIO(response.content))` against the streamed `.xlsx` bytes, asserting `Content-Type`, `Content-Disposition`, and cell values (`M10`, `M25`) |
| Rollback boundary | Revert `reportes/views.py::generar` (and its new imports), the `reportes_generar` entry in `reportes/urls.py`, the `{% if messages %}` block in `templates/base.html`, the form rewiring in `reportes/templates/reportes/revision.html`, the `rangos` fix in `reportes/tests/conftest.py`, and the new tests + imports in `reportes/tests/test_views.py`. PR 1/PR 2 (`models`, `cerrar_reporte`) stay functional standalone; no data loss. |

## Full Suite Confirmation (Batch 3)

- `pytest reportes/tests/test_views.py -k "generar or revision or cerrar" -q` → **17 passed, 17 deselected**
- `pytest reportes/ -q` (isolated) → **83 passed** in 230.28s
- `manage.py makemigrations --check --dry-run --skip-checks` → "No changes detected"
- `pytest -q --reuse-db` (full project, first run, overlapping with a concurrent `reportes/`-only background run) → **222 passed, 2 failed**. Both failures were `psycopg.errors.DeadlockDetected` on `tipos_reporte_tipodereporte_codigo_key` while inserting — caused by two pytest processes hitting the same remote Neon Postgres DB concurrently (a self-inflicted overlap from running two background test commands at once), NOT a code regression. Neither failing test (`test_reporte_is_created_with_tipo_definicion_creador_and_estado_inicial`, `test_valor_de_reporte_is_created_with_identificador_valor_autor_fecha`) touches any file changed in this batch.
- `pytest -q --reuse-db` (full project, re-run in isolation, no concurrent process) → **224 passed** in 347.66s — confirms the deadlock was pure test-runner concurrency flake, not a regression.

## Deviations from Design

- `reporte_listo_para_cerrar`'s `plantilla_xlsx` merge ranges (see "Deviation from design (fixture bug fix...)" above) — test-fixture-only fix, no production code touched, no spec/design contract changed.
- No other deviations — `generar`, the template wiring, and `base.html`'s messages block all match `design.md`'s Interfaces/Contracts and D4 verbatim.

## Issues Found

None beyond the fixture bug documented above (already fixed).

## Change Status

**ALL tasks in `tasks.md` are now complete.** Phases 1-7 are fully implemented across PR 1 (models), PR 2 (`cerrar_reporte`), and PR 3 (`generar` + template wiring + full regression). The change `cierre-y-generacion-reporte` is fully implemented and ready for `sdd-verify`.

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

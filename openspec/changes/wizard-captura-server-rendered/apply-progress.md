# Apply Progress: Wizard de captura server-rendered

## Scope of this run

PR 1 of 4 — Phase 1 only (`tipos_reporte/generador.py` extraction). PR 2-4
(reportes app, models, formularios/valores codec, views/urls/templates) are
NOT started.

## Completed Tasks (Phase 1 / PR 1)

- [x] 1.1 RED: `tipos_reporte/tests/test_generador.py` — added
      `test_claves_de_valor_de_un_campo_escalar_coincide_con_destinos` and
      `test_claves_de_valor_de_un_rango_coincide_con_destinos`, asserting
      `claves_de_valor(nodo)` returns the same keys `_destinos` derives for
      both a scalar field and a `rango-hora-inicio-fin` node.
- [x] 1.2 GREEN: extracted public `claves_de_valor(nodo)` in
      `tipos_reporte/generador.py`; `_destinos(nodo)` now calls it
      internally (zips the returned keys with
      `_claves_de_celda_requeridas(nodo.get("tipo"))` to attach cell
      coordinates), matching design D5.
- [x] 1.3 REFACTOR: ran the full `tipos_reporte` suite — 104 passed (102
      pre-existing + 2 new), 0 failures, 0 regressions.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1.1/1.2 `claves_de_valor` scalar case | `pytest tipos_reporte/tests/test_generador.py -k claves_de_valor` → 2 failed, `ImportError: cannot import name 'claves_de_valor'` (correct failure reason — function did not exist yet) | Same command → 2 passed after extracting `claves_de_valor` and rewriting `_destinos` to use it | Full `tipos_reporte` suite → 104 passed |
| 1.1/1.2 `claves_de_valor` range case | Same RED run as above (both cases written together) | Same GREEN run as above | Same REFACTOR run as above |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest tipos_reporte/tests/test_generador.py -k "claves_de_valor or destinos"` → 4 passed (2 new `claves_de_valor` tests + 2 pre-existing `_destinos` tests, unchanged) |
| Runtime harness command/scenario and exact result | `pytest tipos_reporte --reuse-db` (full existing suite) → 104 passed in 111.88s, 0 failures |
| Rollback boundary | Revert `tipos_reporte/generador.py` diff (the `claves_de_valor` extraction + rewritten `_destinos`) and the two new tests appended to `tipos_reporte/tests/test_generador.py`. No other files touched. |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tipos_reporte/generador.py` | Modified | Extracted public `claves_de_valor(nodo)` from `_destinos`; `_destinos` now zips `claves_de_valor(nodo)` with `_claves_de_celda_requeridas(nodo.get("tipo"))` to attach coordinates. No behavior change to `_destinos`'s external contract — both pre-existing `_destinos` tests still pass unchanged. |
| `tipos_reporte/tests/test_generador.py` | Modified | Added 2 RED→GREEN tests for `claves_de_valor` (scalar + range cases), asserting parity with `_destinos`. |
| `openspec/changes/wizard-captura-server-rendered/tasks.md` | Modified | Marked tasks 1.1, 1.2, 1.3 as `[x]`. |

## Deviations from Design

None — implementation matches design D5 exactly: `claves_de_valor(nodo)` is
public, extracted from `_destinos`, and `_destinos` calls it internally.

## Remaining Tasks (PR 2, PR 3, PR 4 — NOT started this run)

### Phase 2: reportes app + models (PR 2)
- [ ] 2.1 Scaffold `reportes/` app
- [ ] 2.2 RED: `reportes/tests/test_models.py`
- [ ] 2.3 GREEN: `reportes/models.py`
- [ ] 2.4 Generate `reportes/migrations/0001_initial.py`
- [ ] 2.5 `reportes/tests/conftest.py` fixtures
- [ ] 2.6 Register `reportes` in `config/settings.py`

### Phase 3: form builder + codec (PR 3)
- [ ] 3.1 RED: `reportes/tests/test_formularios.py`
- [ ] 3.2 GREEN: `reportes/formularios.py`
- [ ] 3.3 RED: `reportes/tests/test_valores.py`
- [ ] 3.4 GREEN: `reportes/valores.py`
- [ ] 3.5 Contract test: `identificador_de_campo` keys equal `generador.claves_de_valor`

### Phase 4: views, urls, templates (PR 4)
- [ ] 4.1 RED: `reportes/tests/test_views.py` (nuevo)
- [ ] 4.2 GREEN: `reportes/views.py::iniciar_reporte`
- [ ] 4.3 RED: extend `test_views.py` (paso)
- [ ] 4.4 GREEN: `reportes/views.py::paso`
- [ ] 4.5 `reportes/urls.py`
- [ ] 4.6 `config/urls.py` include
- [ ] 4.7 `reportes/templates/reportes/paso.html`
- [ ] 4.8 RED+GREEN: empty-campos section test
- [ ] 4.9 Full suite run: `pytest reportes tipos_reporte`

## Workload / PR Boundary

- Mode: chained/stacked PR slice (`stacked-to-main`)
- Current work unit: Unit 1 — "Extract `claves_de_valor(nodo)` from `_destinos`, no behavior change"
- Boundary: this batch starts and ends entirely within `tipos_reporte/generador.py` and its test file; zero new dependents introduced (the `reportes` app does not exist yet, so nothing imports `claves_de_valor` outside this PR)
- Estimated review budget impact: well under the 400-line budget — this PR's diff is a small, mechanical, internal extraction (~30 lines changed)

## Status

3/32 total tasks complete (Phase 1 fully done). Ready for PR 1 review /
`sdd-verify`. PR 2 (Phase 2: reportes app scaffold + models) is the next
apply batch.

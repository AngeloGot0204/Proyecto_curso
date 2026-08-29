# Apply Progress: Wizard de captura server-rendered

## Scope of this run

PR 2 of 4 — Phase 2 only (`reportes` app scaffold, `Reporte`/`ValorDeReporte`
models, migration, `reportes/tests/conftest.py` fixtures). PR 1 (Phase 1,
`claves_de_valor` extraction) is already merged to main. PR 3-4 (formularios/
valores codec, views/urls/templates) are NOT started.

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

## Completed Tasks (Phase 2 / PR 2)

- [x] 2.1 Scaffolded `reportes/` app: `apps.py` (`ReportesConfig`),
      `__init__.py`, `migrations/__init__.py`, `tests/__init__.py`.
- [x] 2.2 RED: `reportes/tests/test_models.py` — 4 tests: `Reporte` creation
      with `tipo`/`definicion`/`creador`/`fecha_creacion`/`estado` (spec
      scenario "First wizard step creates the Reporte"); subsequent-step
      reuse via `Reporte.objects.get(pk=...)` (spec scenario "Subsequent
      steps reference the existing Reporte"); `ValorDeReporte` row creation
      with `identificador_de_campo`/`valor`/`autor`/`fecha`; `ValorDeReporte`
      unique constraint per `reporte`+`identificador_de_campo`.
- [x] 2.3 GREEN: `reportes/models.py` — `EstadoDeReporte` (`TextChoices`,
      single `EN_PROGRESO` member per design D6), `Reporte` (FKs to
      `TipoDeReporte`/`DefinicionDeTipo`/`AUTH_USER_MODEL`, all `PROTECT`,
      `fecha_creacion` auto_now_add, `estado` default `EN_PROGRESO`),
      `ValorDeReporte` (FK `Reporte` `CASCADE`, `identificador_de_campo`
      CharField, `valor` TextField(blank=True) per design D1, `autor` FK
      `PROTECT`, `fecha` auto_now, `UniqueConstraint` on
      `reporte`+`identificador_de_campo` named
      `valor_unico_por_reporte_y_campo`).
- [x] 2.4 Generated `reportes/migrations/0001_initial.py` via
      `manage.py makemigrations reportes` — creates both tables.
- [x] 2.5 `reportes/tests/conftest.py` — `usuario_factory` (via
      `Usuario.objects.create_user`, so passwords hash, per design's Testing
      Strategy), `definicion_valida` (deep-copy factory, mirrored from
      `tipos_reporte/tests/conftest.py`), `tipo_con_definicion_activa_factory`
      (builds `TipoDeReporte` + an already-activated `DefinicionDeTipo` row
      directly — `estado=ACTIVA`, `version=1`, `activada_en=now` — and
      points `definicion_activa` at it, satisfying
      `definicion_estado_implica_version` directly per design D11),
      `reporte_factory`, `cliente_autenticado` (`client.force_login`).
- [x] 2.6 Registered `reportes` in `config/settings.py` `INSTALLED_APPS`
      (after `tipos_reporte`).

## TDD Cycle Evidence (Phase 2)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.2/2.3 `Reporte` creation | `reportes/tests/test_models.py` | Integration (DB) | N/A (new app) | ✅ `ModuleNotFoundError: No module named 'reportes.models'` (correct — models.py did not exist yet) | ✅ 4/4 passed after `reportes/models.py` + migration | ✅ 2 scenarios (create + reuse-by-pk) | ➖ None needed — model is a thin Django declaration |
| 2.2/2.3 `ValorDeReporte` per value + unique constraint | `reportes/tests/test_models.py` | Integration (DB) | N/A (new app) | Same RED run as above | Same GREEN run as above | ✅ 2 cases (plain creation + IntegrityError on duplicate key) | ➖ None needed |

## Work Unit Evidence (Phase 2)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_models.py -v` → 4 passed |
| Runtime harness command/scenario and exact result | `pytest reportes tipos_reporte usuarios -v` (full project suite) → 125 passed in 134.61s, 0 failures, 0 regressions (121 pre-existing + 4 new) |
| Rollback boundary | `python manage.py migrate reportes zero`, then delete the `reportes/` app directory and remove `'reportes'` from `config/settings.py` `INSTALLED_APPS`. No other file outside `reportes/` and that one settings line was touched. |

## Files Changed (Phase 2)

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/__init__.py`, `reportes/migrations/__init__.py`, `reportes/tests/__init__.py` | Created | App/package scaffolding |
| `reportes/apps.py` | Created | `ReportesConfig` |
| `reportes/models.py` | Created | `EstadoDeReporte`, `Reporte`, `ValorDeReporte` per design Interfaces/Contracts |
| `reportes/migrations/0001_initial.py` | Created | Generated migration creating both tables |
| `reportes/tests/test_models.py` | Created | 4 RED→GREEN tests covering both spec requirements |
| `reportes/tests/conftest.py` | Created | `usuario_factory`, `definicion_valida`, `tipo_con_definicion_activa_factory` (D11), `reporte_factory`, `cliente_autenticado` |
| `config/settings.py` | Modified | Added `'reportes'` to `INSTALLED_APPS` |
| `openspec/changes/wizard-captura-server-rendered/tasks.md` | Modified | Marked tasks 2.1-2.6 as `[x]` |

## Deviations from Design (Phase 2)

None — implementation matches design D1, D6, D11, and the Interfaces/
Contracts section exactly. One naming note (not a deviation): `usuario_factory`
in `reportes/tests/conftest.py` intentionally differs from `tipos_reporte`'s
plaintext-password fixture by using `create_user` (hashed password) — this is
explicit in design's Testing Strategy paragraph and needed for
`cliente_autenticado`'s `force_login` + a future real-login path.

## Remaining Tasks (PR 3, PR 4 — NOT started this run)

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

## Workload / PR Boundary (Phase 2 / PR 2)

- Mode: chained/stacked PR slice (`stacked-to-main`), targeting the PR 1 branch per Chain strategy
- Current work unit: Unit 2 — "`reportes` app scaffold + models + migration + fixtures"
- Boundary: this batch starts and ends entirely within the new `reportes/` app directory plus one added line in `config/settings.py` `INSTALLED_APPS`; zero views/urls/templates/formularios/valores code introduced (that is PR 3/PR 4's scope)
- Estimated review budget impact: well under the 400-line budget — models + migration + fixtures + tests total well under 400 changed lines

## Status

9/32 total tasks complete (Phase 1 + Phase 2 fully done). Ready for PR 2
review / `sdd-verify`. PR 3 (Phase 3: form builder `formularios.py` + codec
`valores.py`) is the next apply batch.

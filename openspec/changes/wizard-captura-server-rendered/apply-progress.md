# Apply Progress: Wizard de captura server-rendered

## Scope of this run

PR 3 of 4 — Phase 3 only (dynamic form builder
`construir_formulario_seccion`, field-type-to-widget mapping, value codec:
serialize/rehydrate via `to_python`, empty-value-deletes-row rule). PR 1
(Phase 1, `claves_de_valor` extraction) and PR 2 (Phase 2, `reportes` app +
models) are already merged to main. PR 4 (views/urls/templates) is NOT
started — this run does not touch `reportes/views.py`, `reportes/urls.py`,
`config/urls.py`, or any template.

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

## Completed Tasks (Phase 3 / PR 3)

- [x] 3.1 RED: `reportes/tests/test_formularios.py` — 11 tests: one per
      scalar type's field/widget class (`texto`→`CharField`/`TextInput`,
      `numero`→`DecimalField`/`NumberInput(step="any")`,
      `fecha`→`DateField`/`DateInput(type="date", format="%Y-%m-%d")`,
      `hora`→`TimeField`/`TimeInput(type="time", format="%H:%M")`,
      `seleccion`→`ChoiceField` with `("", "—")` first, `booleano`→
      `BooleanField`/`CheckboxInput`); `rango-hora-inicio-fin`→2 `TimeField`s
      named `{id}_inicio`/`{id}_fin` with `"{label} — Inicio"`/`"— Fin"`
      labels; empty `campos`/`items` section→`base_fields == {}` (spec:
      "Section with no campos/items still renders"); `obligatorio`→
      `widget.attrs["required"] is True` while `campo.required is False`
      (D8); non-`obligatorio`→no `required` attr; a contract test asserting
      the built form's field names equal the union of
      `generador.claves_de_valor(nodo)` over every node (task 3.5, folded
      into this file per design's Testing Strategy row 5).
- [x] 3.2 GREEN: `reportes/formularios.py` — `construir_formulario_seccion(seccion)`
      iterates `validacion._iterar_nodos({"secciones": [seccion]})` (D4) and
      names every field via `generador.claves_de_valor(nodo)` (D5); a
      private `_campo_escalar(tipo, opciones)` maps each `TipoDeDato` to its
      Field+Widget pair per design's Type mapping table; `_campos_de_rango`
      builds the two range `TimeField`s; `_marcar_obligatorio` adds the HTML
      `required` widget attribute without touching Python `required`
      (always `False`, D8). Returns `type("FormularioDeSeccion", (forms.Form,), campos)`.
- [x] 3.3 RED: `reportes/tests/test_valores.py` — 17 tests: `a_texto`
      round-trip per Python value type (`str` as-is, `Decimal`→`str(Decimal)`,
      `date`→ISO, `time`→`HH:MM`, `bool` True/False→`"true"`/`"false"`,
      checked BEFORE the numeric branch since `bool` subclasses `int`);
      `desde_texto` rehydration via `campo.to_python` for `Decimal`/`date`/
      `time`/`bool`; `guardar_valor`: `None` deletes an existing row,
      `""` deletes an existing row (the D3 completeness-safety case), `None`
      with no existing row is a no-op, a non-empty value creates a row with
      the serialized string, re-`guardar_valor` on the same key upserts
      without duplicating (unique constraint from Phase 2 backs this), and
      `False` persists its own `"false"` row (never deleted/skipped).
- [x] 3.4 GREEN: `reportes/valores.py` — `a_texto(campo, valor)` and
      `desde_texto(campo, texto)` per design D2; both delegate to a private
      `_serializar(valor)` helper (also reused by `guardar_valor`, avoiding
      a duplicated dispatch table); `desde_texto` calls
      `campo.to_python(texto)` directly. `guardar_valor(reporte,
      identificador_de_campo, valor, autor)` implements D3: `valor is None
      or valor == ""` (equality, never truthiness, so `Decimal("0")`/`False`
      are never mistaken for "not provided") deletes the row via
      `ValorDeReporte.objects.filter(...).delete()`; otherwise
      `update_or_create` with `defaults={"valor": _serializar(valor),
      "autor": autor}`.
- [x] 3.5 Contract test: folded into `test_formularios.py`'s
      `test_nombres_de_campo_del_formulario_coinciden_con_claves_de_valor`
      — asserts the built form's field-name set equals the union of
      `generador.claves_de_valor(nodo)` over every node the section
      declares (scalar + range).

## TDD Cycle Evidence (Phase 3)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1/3.2 `construir_formulario_seccion` per-type mapping | `reportes/tests/test_formularios.py` | Unit | N/A (new file) | ✅ `ModuleNotFoundError: No module named 'reportes.formularios'` (correct — file did not exist yet) | ✅ 11/11 passed after `reportes/formularios.py`; one iteration needed — initial `DateInput`/`TimeInput` `attrs.get("type")` assertions were wrong (Django's `Input.__init__` pops `attrs["type"]` into `self.input_type`, it never stays in `attrs`); fixed the TEST assertions to `widget.input_type`, production code was already correct against design's literal widget construction | ✅ 7 type cases (texto/numero/fecha/hora/seleccion/booleano/rango) + empty-section + obligatorio-true + obligatorio-false + contract test | ✅ none needed — builder was already a small dispatch function |
| 3.3/3.4 `a_texto`/`desde_texto` codec | `reportes/tests/test_valores.py` | Unit | N/A (new file) | ✅ `ModuleNotFoundError: No module named 'reportes.valores'` (correct — file did not exist yet) | ✅ 11/11 (non-DB) passed after `reportes/valores.py` | ✅ 4 value types × serialize + rehydrate (str/Decimal/date/time/bool) | ✅ extracted `_serializar` helper shared by `a_texto` and `guardar_valor`, moved `from reportes.models import ValorDeReporte` to module top (no circular import risk — `models.py` never imports `valores.py`); re-ran full file after each refactor step, stayed green |
| 3.3/3.4 `guardar_valor` empty-deletes / upsert | `reportes/tests/test_valores.py` | Integration (DB) | N/A (new file) | Same RED run as above | ✅ 6/6 DB tests passed on first GREEN run | ✅ 6 cases: None-deletes-existing, empty-string-deletes-existing, None-no-existing-row (no-op), non-empty-creates, re-save-upserts-no-duplicate, booleano-False-persists-as-"false" | Same refactor pass as above |

### Test Summary
- **Total tests written**: 28 (11 `test_formularios.py` + 17 `test_valores.py`)
- **Total tests passing**: 28/28
- **Layers used**: Unit (22), Integration/DB (6)
- **Approval tests** (refactoring): None — no refactoring tasks, both files are new
- **Pure functions created**: 6 (`_campo_escalar`, `_marcar_obligatorio`, `_campos_de_rango`, `construir_formulario_seccion`, `_serializar`, `a_texto`); `desde_texto` and `guardar_valor` are thin wrappers with one delegated side effect each

## Work Unit Evidence (Phase 3)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_formularios.py reportes/tests/test_valores.py -v` → 28 passed |
| Runtime harness command/scenario and exact result | `pytest reportes tipos_reporte usuarios` (full project suite, `--reuse-db`) → 153 passed in 147.16s, 0 failures, 0 regressions (125 pre-existing + 28 new) |
| Rollback boundary | Revert `reportes/formularios.py`, `reportes/valores.py`, `reportes/tests/test_formularios.py`, `reportes/tests/test_valores.py` (all four new files, zero modifications to any pre-existing file). No models, migrations, views, urls, or `tipos_reporte` code touched this batch. |

## Files Changed (Phase 3)

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/formularios.py` | Created | `construir_formulario_seccion(seccion)` + type→field/widget dispatch per design's Type mapping table |
| `reportes/valores.py` | Created | `a_texto`, `desde_texto`, `guardar_valor` — the D2/D3 codec |
| `reportes/tests/test_formularios.py` | Created | 11 tests covering every field type, empty section, obligatorio marker, and the field-name/`claves_de_valor` contract |
| `reportes/tests/test_valores.py` | Created | 17 tests covering codec round-trip per type and `guardar_valor`'s empty-deletes/upsert rule |
| `openspec/changes/wizard-captura-server-rendered/tasks.md` | Modified | Marked tasks 3.1-3.5 as `[x]` |

## Deviations from Design (Phase 3)

None — implementation matches design D2, D3, D4, D5, D8, and the Type
mapping table exactly. One test-writing correction (not a design or
production-code deviation): the initial RED test for `DateInput`/`TimeInput`
asserted `widget.attrs.get("type")`, which is always `None` because Django's
`Input.__init__` pops `"type"` out of `attrs` into `self.input_type` (it
renders the HTML `type` attribute from there, never from `attrs`). Fixed the
test assertions to `widget.input_type`; the production widget construction
(`attrs={"type": "date"/"time"}`) already matched design's literal
instruction and needed no change.

## Remaining Tasks (PR 4 — NOT started this run)

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

## Workload / PR Boundary (Phase 3 / PR 3)

- Mode: chained/stacked PR slice (`stacked-to-main`), targeting the PR 2 branch per Chain strategy
- Current work unit: Unit 3 — "`formularios.py` builder + `valores.py` codec"
- Boundary: this batch touches only two new production files
  (`reportes/formularios.py`, `reportes/valores.py`) and their two matching
  new test files; zero views, urls, templates, or settings changes; zero
  modification to any pre-existing file
- Estimated review budget impact: well under the 400-line budget — two
  small production modules (~95 + ~60 lines) plus their tests

## Status

14/23 total tasks complete (Phase 1 + Phase 2 + Phase 3 fully done: 3 + 6 +
5). Ready for PR 3 review / `sdd-verify`. PR 4 (Phase 4: views, urls,
templates — 9 tasks) is the next and final apply batch.

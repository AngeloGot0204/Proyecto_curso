# Tasks: Validación de datos del formulario

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550–650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `validacion.py` + fixture, anti-drift locked to generator | PR 1 | `pytest reportes/tests/test_validacion.py` | N/A — pure module, no server/UI to exercise | `reportes/validacion.py`, fixture addition; delete without affecting other modules |
| 2 | `formularios.py` companion field + JS data attrs | PR 2 | `pytest reportes/tests/test_formularios.py` | manual GET on an existing `paso` page, inspect rendered attrs | revert `formularios.py` diff; PR1 unaffected |
| 3 | S-09 `revision` view + template + urls | PR 3 | `pytest reportes/tests/test_views.py -k revision` | `manage.py runserver`, GET `/reportes/<id>/revision/` | remove route/view/template; wizard flow unaffected |
| 4 | `paso.html`/`paso.js` client-side layer | PR 4 | `pytest reportes/tests/test_views.py -k paso` | browser: toggle hora fields and "No cumple" select on a live `paso` page | revert template/js; server behavior unchanged (JS-only) |

## Phase 1: Foundation

- [x] 1.1 Add `estructura_con_validaciones` fixture to `reportes/tests/conftest.py` (obligatorio `texto`, `seleccion` with `["Cumple","No cumple"]`, obligatorio `rango-hora-inicio-fin`)

## Phase 2: `validar_reporte` core (TDD)

- [x] 2.1 RED `test_validacion.py`: all obligatorio filled → empty `errores` (spec scenario 1)
- [x] 2.2 GREEN: create `reportes/validacion.py` — `ProblemaDeReporte`, `ResultadoDeRevision`, `_indice_de_campos`, `validar_reporte` calling `generador._validar_completitud` in `try/except ValoresIncompletos`
- [x] 2.3 RED: missing obligatorio field → one `errore` with `identificador_de_campo`+`seccion_id` (scenario 2)
- [x] 2.4 RED: anti-drift lock — `validar_reporte` vs direct `_validar_completitud` call agree on missing set (scenario 3)
- [x] 2.5 GREEN: confirm 2.3/2.4 pass via `.faltantes` translation only, no reimplementation
- [x] 2.6 RED: stray `fin<=inicio` → advertencia, not errore (scenario 4)
- [x] 2.7 GREEN: implement rango pass (`desde_texto(TimeField())`, skip unparsable)
- [x] 2.8 RED: "No cumple" without observación → advertencia (scenario 5)
- [x] 2.9 RED: "No cumple" with observación → no advertencia (scenario 6)
- [x] 2.10 GREEN: implement seleccion "No cumple" pass

## Phase 3: `formularios.py` companion field (TDD)

- [ ] 3.1 RED `test_formularios.py`: rango `TimeField` widgets carry `data-rango`/`data-rango-extremo`
- [ ] 3.2 GREEN: `_campos_de_rango` gains `nodo_id` param, sets both attrs
- [ ] 3.3 RED: seleccion field with "No cumple" option → companion `{id}_observacion` `CharField(required=False)` in `form.fields`, `data-requiere-observacion` on select
- [ ] 3.4 GREEN: `construir_formulario_seccion` injects companion field with `data-observacion-de`

## Phase 4: S-09 review screen (TDD)

- [ ] 4.1 RED `test_views.py`: GET `revision` as creador → 200, lists errores/advertencias
- [ ] 4.2 RED: GET `revision` as another user → 404
- [ ] 4.3 RED: GET `revision` anon → redirect to login
- [ ] 4.4 RED: Generar `disabled` present iff `errores` non-empty (two cases)
- [ ] 4.5 GREEN: add `revision` view to `reportes/views.py` (`@login_required`, creador-scoped `get_object_or_404`, calls `validar_reporte`)
- [ ] 4.6 GREEN: add `path("<int:reporte_id>/revision/", ...)` to `reportes/urls.py`
- [ ] 4.7 GREEN: create `reportes/templates/reportes/revision.html` — Debes corregir / Advertencias lists linked via `reportes_paso`, Generar button

## Phase 5: Client-side JS layer (TDD)

- [ ] 5.1 RED `test_views.py`: `paso` GET HTML contains `data-campo`, `data-rango`, `data-requiere-observacion`, `data-siguiente`, `<script src=".../paso.js">`
- [ ] 5.2 GREEN: modify `reportes/templates/reportes/paso.html` — wrap fields in `<p data-campo>`, add `{% load static %}` + deferred script, `data-siguiente` on nav anchor
- [ ] 5.3 GREEN: create `reportes/static/reportes/paso.js` — hora-range lexicographic compare disables Siguiente/submit; No-cumple toggle sets/strips `required` on hidden observación input

## Phase 6: Regression

- [ ] 6.1 Run `test_post_paso_sin_valor_obligatorio_no_bloquea` unmodified — confirm still passes (`paso` POST untouched, design decision 2)
- [ ] 6.2 Add `test_post_paso_con_rango_invalido_no_bloquea` — 302 + both values persisted, no server-side block in `paso` POST
- [ ] 6.3 Full suite: `pytest reportes/tests/test_validacion.py reportes/tests/test_views.py reportes/tests/test_formularios.py`

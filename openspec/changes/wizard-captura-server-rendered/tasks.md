# Tasks: Wizard de captura server-rendered

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~650-800 (models+migration+forms+codec+views+templates+tests+generador refactor) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (ask user) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Extract `claves_de_valor(nodo)` from `_destinos`, no behavior change | PR 1 | `pytest tipos_reporte/tests -k destinos_or_claves` | `pytest tipos_reporte/tests` (existing 102 tests) | Revert `generador.py` diff only |
| 2 | `reportes` app scaffold + models + migration + fixtures | PR 2 | `pytest reportes/tests/test_models.py` | `pytest reportes` | `python manage.py migrate reportes zero`; drop app dir |
| 3 | `formularios.py` builder + `valores.py` codec | PR 3 | `pytest reportes/tests/test_formularios.py reportes/tests/test_valores.py` | `pytest reportes` | Revert two files + their tests |
| 4 | Views, urls, templates, settings wiring, integration tests | PR 4 | `pytest reportes/tests/test_views.py` | `python manage.py runserver` + manual POST through wizard | Remove `reportes/views.py`, `urls.py`, templates; unregister app |

## Phase 1: generador.py extraction (PR 1)

- [x] 1.1 RED: `tipos_reporte/tests/test_generador.py` — add test asserting `claves_de_valor(nodo)` returns same keys `_destinos` currently derives (simple field, `rango-hora-inicio-fin`).
- [x] 1.2 GREEN: extract `claves_de_valor(nodo)` (public) in `tipos_reporte/generador.py`; `_destinos` calls it internally.
- [x] 1.3 REFACTOR: run full `tipos_reporte` suite (102 existing + 2 new = 104 tests), confirm unchanged pass count (0 failures, 0 regressions).

## Phase 2: reportes app + models (PR 2)

- [x] 2.1 Scaffold `reportes/` app (`apps.py`, `__init__.py`, `migrations/__init__.py`, `tests/__init__.py`).
- [x] 2.2 RED: `reportes/tests/test_models.py` — `Reporte` creation (Requirement: Reporte creation, both scenarios); `ValorDeReporte` unique constraint per `reporte`+`identificador_de_campo`.
- [x] 2.3 GREEN: `reportes/models.py` — `EstadoDeReporte`, `Reporte`, `ValorDeReporte` per design Interfaces/Contracts.
- [x] 2.4 Generate `reportes/migrations/0001_initial.py`.
- [x] 2.5 `reportes/tests/conftest.py` — `usuario_factory`, `definicion_valida`, `tipo_con_definicion_activa_factory` (satisfies `definicion_estado_implica_version` CheckConstraint directly, D11), `reporte_factory`, `cliente_autenticado`.
- [x] 2.6 Register `reportes` in `config/settings.py` `INSTALLED_APPS`.

## Phase 3: form builder + codec (PR 3)

- [x] 3.1 RED: `reportes/tests/test_formularios.py` — per-type field/widget assertions, `rango-hora-inicio-fin`→2 fields, empty section→0 fields, `obligatorio`→`attrs["required"]` + `required=False` (spec: One URL and dynamic form per section).
- [x] 3.2 GREEN: `reportes/formularios.py` — `construir_formulario_seccion(seccion)` using `validacion._iterar_nodos` (D4) and `generador.claves_de_valor` (D5) for field names.
- [x] 3.3 RED: `reportes/tests/test_valores.py` — codec round-trip per type; `booleano` always writes `"true"`/`"false"`; empty value deletes row (D2, D3).
- [x] 3.4 GREEN: `reportes/valores.py` — `a_texto(campo, valor)` serialize; rehydrate via `campo.to_python(texto)`.
- [x] 3.5 Contract test: `identificador_de_campo` keys equal `generador.claves_de_valor` for same node (design Testing Strategy row 5).

## Phase 4: views, urls, templates (PR 4)

- [ ] 4.1 RED: `reportes/tests/test_views.py` — `POST /nuevo/` creates one `Reporte` (D7); GET on `nuevo` is 405; anonymous → 302 login (Requirement: Authentication required).
- [ ] 4.2 GREEN: `reportes/views.py::iniciar_reporte` (`require_POST`, `login_required`), redirect to first section.
- [ ] 4.3 RED: extend `test_views.py` — `paso` GET rehydrates from `ValorDeReporte` (Requirement: GET rehydration); POST upserts, no duplicate rows on re-POST (Requirement: Per-step durable persistence); foreign `Reporte` → 404 (D9); missing `obligatorio` value still persists rest (Requirement: Non-blocking obligatorio marker); unknown `seccion_id` → 404.
- [ ] 4.4 GREEN: `reportes/views.py::paso` (`login_required`), section list from `estructura["secciones"]` order, `update_or_create`/`delete` per D3, PRG redirect (last step → itself).
- [ ] 4.5 `reportes/urls.py` — flat `path()` list, no namespace.
- [ ] 4.6 `config/urls.py` — `include("reportes.urls")`.
- [ ] 4.7 `reportes/templates/reportes/paso.html` — extends `templates/base.html`, iterates form fields, renders `pasos`/`url_anterior`/`url_siguiente`/`posicion` nav.
- [ ] 4.8 RED+GREEN: `reportes/tests/test_views.py` — section with empty campos renders without error, allows next-step navigation (spec: Section with no campos/items still renders).
- [ ] 4.9 Full suite run: `pytest reportes tipos_reporte` — confirm no regressions.

## Key Learnings

1. `generador.claves_de_valor(nodo)` must be extracted before any wizard code so both sides derive identical `ValorDeReporte` keys.
2. `reportes/tests/conftest.py` fixtures must satisfy `DefinicionDeTipo`'s `definicion_estado_implica_version` CheckConstraint directly, not via `servicios.activar_definicion`.
3. Estimated diff size (~650-800 lines) exceeds the 400-line budget; chaining into 4 PRs keeps each reviewable and independently revertible.

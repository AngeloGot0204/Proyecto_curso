# Tasks: Mis Reportes — Agrupado por Estado + Selección de Tipo (S-02/S-03)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380-450 (7 files) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Bucket/avance/relacion helpers + S-02 view/template | PR 1 | `pytest reportes/tests/test_listado.py reportes/tests/test_views.py -k "listado or mis_reportes"` | `runserver` → `/reportes/mis/` | Revert `listado.py`, `views.py::mis_reportes`, `mis_reportes.html`, `generador.py` extraction |
| 2 | S-03 selección de tipo | PR 2 (base=PR 1) | `pytest reportes/tests/test_views.py -k seleccion_tipo` | `runserver` → "+ Nuevo reporte" CTA | Remove additive route/view/template |

## Phase 1: Foundation — `tipos_reporte/generador.py`

- [x] 1.1 RED: `test_claves_obligatorias_coincide_con_validar_completitud` in `tipos_reporte/tests/` (missing ids on empty `valores`).
- [x] 1.2 GREEN: add public `claves_obligatorias(estructura)`, mirroring `claves_de_valor` over `_iterar_nodos`/`obligatorio`.
- [x] 1.3 REFACTOR: `_validar_completitud` delegates to `claves_obligatorias`; confirm existing `test_validar_reporte_coincide_con_validar_completitud` stays green.

## Phase 2: Foundation — `reportes/listado.py`

- [x] 2.1 RED: `test_porcentaje_de_avance` — 7/10→70, 249/250→99, 0 obligatorios→100.
- [x] 2.2 GREEN: `porcentaje_de_avance(estructura, faltantes)` via `100 * llenas // total`, floor, 0-total ⇒ 100.
- [x] 2.3 RED: `test_bucket_de_reporte` priority terminado > listo_para_generar > en_progreso.
- [x] 2.4 GREEN: `BUCKETS` tuple + `bucket_de_reporte(tiene_visto_bueno, puede_generar)`.
- [x] 2.5 RED: `test_normalizar_relacion` — creados/compartidos/todos pass, unrecognized/None → todos.
- [x] 2.6 GREEN: `RELACIONES` tuple, `normalizar_relacion`, `aplicar_relacion(qs, usuario, relacion)`.
- [x] 2.7 GREEN: retarget `normalizar_estado` to bucket ids; unrecognized still → `""`.
- [x] 2.8 RED: `test_construir_tarjetas`/`test_agrupar_por_bucket` — `TarjetaDeReporte` fields, BUCKETS-ordered `[{id,titulo,tarjetas}]`.
- [x] 2.9 GREEN: frozen `TarjetaDeReporte(reporte,bucket,avance,numero_registro)`, `construir_tarjetas(qs)`, `agrupar_por_bucket(tarjetas)`.

## Phase 3: Core — `reportes/views.py::mis_reportes`

- [x] 3.1 RED: integration tests — filter-before-group, default todos, same bucket for creador/invitado, `?estado=terminado` finds page-2 report, CTA on empty results, local chip on `numero_registro=None`.
- [x] 3.2 GREEN: rewrite view per D2 — `reportes_accesibles` → `aplicar_busqueda` → `aplicar_relacion` → annotate `Exists(VistoBueno)` + `select_related("definicion")` + `prefetch_related("valores")` → `construir_tarjetas` → filter `?estado=` → `Paginator.get_page` → `agrupar_por_bucket`.
- [x] 3.3 Add `assertNumQueries` regression test (~4 queries regardless of N).

## Phase 4: Integration — Template

- [x] 4.1 Rewrite `mis_reportes.html`: 3 bucket sections, `?relacion=`/`?estado=` controls, avance/registro chips, fixed "+ Nuevo reporte" CTA to `reportes_seleccion_tipo` (always present, even empty results). Deviation: CTA uses a literal `/reportes/nuevo/` href, not `{% url 'reportes_seleccion_tipo' %}`, since that URL name is created by Phase 5 (PR2 of this stacked chain) — see Deviations in the return summary.

## Phase 5: S-03 — Selección de Tipo

- [x] 5.1 RED: `test_seleccion_de_tipo_lista_activos`, `..._muestra_inactivos_deshabilitados`, `..._anonimo_redirige`.
- [x] 5.2 GREEN: `seleccion_de_tipo` view (`@login_required`) — active = `definicion_activa__isnull=False` (never `.filter(activo=True)`, D6), rest disabled.
- [x] 5.3 GREEN: `path("nuevo/", views.seleccion_de_tipo, name="reportes_seleccion_tipo")` in `urls.py`, BEFORE `<str:codigo_tipo>/nuevo/`.
- [x] 5.4 GREEN: create `seleccion_tipo.html` — one POST form per active tipo (código, N° secciones, CSRF) to `reportes_nuevo`; inactive disabled "próximamente".
- [x] 5.5 RED+GREEN: `test_seleccion_de_tipo_selecciona_activo_crea_reporte` — POST to `reportes_nuevo` creates `Reporte` via existing logic.

## Phase 6: Cleanup

- [x] 6.1 Update `mis_reportes`/`iniciar_reporte` docstrings for 3-bucket model + S-03 entry point.
- [x] 6.2 Confirm `cierre-en-participantes` redirect still targets `?estado=terminado` unchanged (no code change expected).
- [x] 6.3 Run full `pytest reportes/ tipos_reporte/`; no regression in adjuntos/paso/revision/participantes suites.

## Key Learnings

1. Bucket priority is terminado > listo_para_generar > en_progreso, identical for every viewer, no per-user attribution.
2. `claves_obligatorias` must be public in `generador.py` first, so `listado.py` reuses it instead of a second obligatorio enumeration.
3. `TipoDeReporte.activo` is a property, not a column — S-03 must filter `definicion_activa__isnull=False`.

# Tasks: Cierre manual (visto bueno) y generación del documento

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~420-480 (2 migrations ~60, models ~40, valores/validacion refactor ~30, views ~120, urls ~10, base.html ~10, revision.html ~60, conftest ~60, tests ~200+) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (models+migrations+valores refactor) → PR 2 (cierre_reporte view+tests) → PR 3 (generar view+templates+tests) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Models (`TERMINADO`, `VistoBueno`, `Generacion`), 2 migrations, `valores_de_reporte` refactor | PR 1 | `pytest reportes/tests/test_models.py reportes/tests/test_valores.py -q` | `manage.py migrate reportes` on a scratch DB | Revert migrations 0002/0003 + models.py/valores.py/validacion.py diff; no data loss |
| 2 | `cerrar_reporte` view + route + creator-only tests + idempotency | PR 2 | `pytest reportes/tests/test_views.py -k cerrar -q` | Manual POST via Django test client / dev server | Revert `cerrar_reporte`, its URL entry, and its tests; VistoBueno rows remain valid but unused |
| 3 | `generar` view + template wiring + `base.html` messages + download tests | PR 3 | `pytest reportes/tests/test_views.py -k generar -q` | Manual POST + download `.xlsx` via dev server, open in Excel/LibreOffice | Revert `generar`, its URL entry, template changes, and its tests; PR 1/2 stay functional standalone |

## Phase 1: Models & Migrations (Foundation)

- [x] 1.1 RED: `reportes/tests/test_models.py` — add `test_estado_de_reporte_admite_terminado` asserting `EstadoDeReporte.TERMINADO == "terminado"` is a valid choice.
- [x] 1.2 GREEN: `reportes/models.py` — add `TERMINADO = "terminado", "Terminado"` to `EstadoDeReporte`.
- [x] 1.3 Generate `reportes/migrations/0002_estado_terminado.py` (`AlterField` on `Reporte.estado`, choices-only).
- [x] 1.4 RED: `reportes/tests/test_models.py` — add `test_visto_bueno_defaults_y_auto_now_add`, `test_segundo_visto_bueno_lanza_integrity_error` (OneToOne), `test_generacion_permite_multiples_filas`.
- [x] 1.5 GREEN: `reportes/models.py` — add `VistoBueno` (`OneToOneField(Reporte, related_name="visto_bueno")`, `usuario` FK `PROTECT`, `fecha` `auto_now_add=True`) and `Generacion` (`reporte` FK `CASCADE`, `definicion` FK `PROTECT` to `tipos_reporte.DefinicionDeTipo`, `usuario` FK `PROTECT`, `fecha` `auto_now_add=True`).
- [x] 1.6 Generate `reportes/migrations/0003_vistobueno_generacion.py` (`CreateModel` × 2).
- [x] 1.7 Run `pytest reportes/tests/test_models.py -q` — confirm all model tests pass.

## Phase 2: Shared Valores Helper (Refactor, behavior-preserving)

- [x] 2.1 RED: create `reportes/tests/test_valores.py` — `test_valores_de_reporte_construye_dict_desde_filas`, `test_valores_de_reporte_reporte_vacio_retorna_dict_vacio`.
- [x] 2.2 GREEN: create `reportes/valores.py` with `def valores_de_reporte(reporte) -> dict[str, str]: return {v.identificador_de_campo: v.valor for v in reporte.valores.all()}`.
- [x] 2.3 REFACTOR: `reportes/validacion.py::validar_reporte` — replace inline `reporte.valores.all()` comprehension with `valores_de_reporte(reporte)`.
- [x] 2.4 REFACTOR: `reportes/views.py::paso` — replace `ValorDeReporte.objects.filter(reporte=reporte)` comprehension with `valores_de_reporte(reporte)`; drop unused `ValorDeReporte` import if no longer referenced elsewhere in the file.
- [x] 2.5 Run `pytest reportes/tests/ -k "validar_reporte_coincide_con_validar_completitud or paso" -q` — confirm `test_validar_reporte_coincide_con_validar_completitud` and existing `paso` tests still pass unchanged.

## Phase 3: Test Fixtures (Foundation for generation tests)

- [x] 3.1 `reportes/tests/conftest.py` — add `plantilla_xlsx(tmp_path)` factory fixture building a real `openpyxl` workbook with sheet `REPORTE` and merged ranges (`rangos=("M10:P10", "M12:P12", "M25:P25")`), mirroring `tipos_reporte/tests/conftest.py`'s pattern.
- [x] 3.2 `reportes/tests/conftest.py` — add `reporte_listo_para_cerrar` fixture returning `(client, reporte)`: uses `estructura_con_validaciones`, the real `plantilla_xlsx`, logs in the creator, and persists all four obligatorio `ValorDeReporte` rows (`observaciones-generales="Todo en orden."`, `estado-general="Cumple"`, `p-01_inicio="08:00"`, `p-01_fin="09:00"`) so `puede_generar` is true. Implemented in PR 2 (`cerrar_reporte` work unit).
- [x] 3.3 Run `pytest reportes/tests/ -q` — confirm no regressions from fixture additions (fixtures unused yet, so this is a smoke check). Scoped to PR 1's additions only (`plantilla_xlsx` + Phase 1/2 changes); full-suite confirmation captured below.

## Phase 4: `cerrar_reporte` View (Core Implementation)

- [x] 4.1 RED: `reportes/tests/test_views.py` — `test_cerrar_reporte_no_creador_devuelve_404` (user B POSTs to A's reporte → 404, no `VistoBueno` row).
- [x] 4.2 RED: `reportes/tests/test_views.py` — `test_cerrar_reporte_rechazado_si_no_puede_generar` (missing obligatorio values → no `VistoBueno`, `estado` unchanged).
- [x] 4.3 RED: `reportes/tests/test_views.py` — `test_cerrar_reporte_creador_exitoso` (uses `reporte_listo_para_cerrar`: `VistoBueno` created, `estado == TERMINADO`, redirect to `reportes_revision`).
- [x] 4.4 RED: `reportes/tests/test_views.py` — `test_cerrar_reporte_doble_post_es_idempotente` (two POSTs → exactly one `VistoBueno` row, no 500/`IntegrityError`).
- [x] 4.5 GREEN: `reportes/urls.py` — add `path("<int:reporte_id>/cerrar/", views.cerrar_reporte, name="reportes_cerrar")`.
- [x] 4.6 GREEN: `reportes/views.py` — add module-level `logger = logging.getLogger(__name__)`; implement `cerrar_reporte` per design (creator-scoped `get_object_or_404`, `validar_reporte(reporte).puede_generar` re-check with `messages.error` + redirect on failure, `transaction.atomic()` block with `VistoBueno.objects.get_or_create(reporte=reporte, defaults={"usuario": request.user})` + `estado = EstadoDeReporte.TERMINADO` + `save(update_fields=["estado"])`, `messages.success` + redirect on success).
- [x] 4.7 Run `pytest reportes/tests/test_views.py -k cerrar -q` — confirm all `cerrar_reporte` tests pass.

## Phase 5: `generar` View (Core Implementation)

- [ ] 5.1 RED: `reportes/tests/test_views.py` — `test_generar_sin_visto_bueno_redirige_con_error` (no `.xlsx` streamed, no `Generacion` row, redirect to `revision`, flash error present).
- [ ] 5.2 RED: `reportes/tests/test_views.py` — `test_generar_rechazado_si_no_puede_generar_pese_a_visto_bueno` (VistoBueno exists but `puede_generar` now False → rejected).
- [ ] 5.3 RED: `reportes/tests/test_views.py` — `test_generar_no_creador_tambien_puede_generar` (user B, not creator, generation succeeds, `Generacion.usuario == B`).
- [ ] 5.4 RED: `reportes/tests/test_views.py` — `test_generar_captura_problema_de_generacion_y_redirige` (mock `generador.generar_reporte` to raise `PlantillaIlegible`/`ValoresIncompletos` → redirect to `revision`, flash error via `get_messages`, status != 500).
- [ ] 5.5 RED: `reportes/tests/test_views.py` — `test_generar_exitoso_streamea_xlsx_con_headers_correctos` (asserts `Content-Type`, `Content-Disposition: attachment; filename="..."`, `load_workbook(BytesIO(response.content))` round-trip, cell values at `M10`/`M25`).
- [ ] 5.6 RED: `reportes/tests/test_views.py` — `test_generar_repetido_crea_multiples_filas_generacion` (two successful POSTs → two `Generacion` rows, no error).
- [ ] 5.7 GREEN: `reportes/urls.py` — add `path("<int:reporte_id>/generar/", views.generar, name="reportes_generar")`.
- [ ] 5.8 GREEN: `reportes/views.py` — implement `generar` per design (`@login_required @require_POST`, non-creator-scoped `get_object_or_404`, `VistoBueno`-exists check + `messages.error` + redirect, `validar_reporte(reporte).puede_generar` re-check + `messages.error` + redirect, `try: generador.generar_reporte(reporte.definicion, valores_de_reporte(reporte)) except ProblemaDeGeneracion: logger.exception(...); messages.error(...); return redirect(...)`, on success `Generacion.objects.create(reporte=reporte, definicion=reporte.definicion, usuario=request.user)` + build filename `f"{reporte.tipo.codigo}-{reporte.id}-{timezone.localdate():%Y%m%d}.xlsx"` + `HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")` + `Content-Disposition` header).
- [ ] 5.9 Run `pytest reportes/tests/test_views.py -k generar -q` — confirm all `generar` tests pass.

## Phase 6: Template & Messages Wiring (Integration)

- [ ] 6.1 `templates/base.html` — add `{% if messages %}` block rendering each message with its `.tags`/level (Bootstrap-alert style consistent with existing markup).
- [ ] 6.2 RED: `reportes/tests/test_views.py` — extend/add `test_get_revision_sin_errores_habilita_generar` assertions if needed to confirm no bare `"disabled"` substring appears when `puede_generar` is true and no `VistoBueno` exists yet (per design D4).
- [ ] 6.3 RED: `reportes/tests/test_views.py` — `test_get_revision_con_visto_bueno_muestra_form_generar` (Generar form rendered as real POST with `{% csrf_token %}` once `VistoBueno` exists).
- [ ] 6.4 RED: `reportes/tests/test_views.py` — `test_get_revision_no_creador_no_ve_boton_cerrar` (Cerrar reporte button absent for non-creator).
- [ ] 6.5 GREEN: `reportes/views.py::revision` — add `tiene_visto_bueno` to the template context (`hasattr(reporte, "visto_bueno")` or `VistoBueno.objects.filter(reporte=reporte).exists()`).
- [ ] 6.6 GREEN: `reportes/templates/reportes/revision.html` — render the Generar form only when `tiene_visto_bueno` (real POST to `reportes_generar` with `{% csrf_token %}`); render a creator-only Cerrar reporte form (POST to `reportes_cerrar`, `{% csrf_token %}`) with `{% if not resultado.puede_generar %}disabled{% endif %}` per design D4.
- [ ] 6.7 Run `pytest reportes/tests/test_views.py -k revision -q` — confirm `test_get_revision_sin_errores_habilita_generar` and `test_get_revision_con_errores_deshabilita_generar` still pass unchanged, plus new template tests.

## Phase 7: Full Regression & Cleanup

- [ ] 7.1 Run the full suite `pytest reportes/ -q` — confirm zero regressions across models, valores, validacion, views, templates.
- [ ] 7.2 RED+GREEN: `reportes/tests/test_views.py` — `test_edicion_post_cierre_sigue_funcionando` (creator submits `paso` after `estado=TERMINADO` → `ValorDeReporte` update succeeds, no closure-related restriction).
- [ ] 7.3 Confirm `ProblemaDeGeneracion` logging path (`logger.exception`) is exercised by test 5.4 and does not raise; no Sentry wiring added (out of scope, D6).
- [ ] 7.4 Review diff size per work unit against the 400-line budget before opening each PR; split further if any unit exceeds it.

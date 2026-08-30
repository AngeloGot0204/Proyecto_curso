# Tasks: Administración de tipos de reporte (S-14, backlog #13)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | PR1 ~480-560 (decorators.py ~20, listado.py ~55, views.py ~80, urls.py ~15, config/urls.py ~2, lista.html ~60, detalle.html ~70, test_decorators.py ~50, test_listado.py ~60, test_vistas.py ~180, conftest.py ~30); PR2 ~560-680 (validacion.py +~35, admin.py ~-25/+5, forms.py ~70, views.py +~90, urls.py +~15, formulario_tipo.html ~40, formulario_definicion.html ~35, test_formularios.py ~140, test_vistas.py +~180, test_generador.py +~20) |
| 400-line budget risk | PR1: Medium; PR2: High (forms.py + validacion.py extraction + admin.py deregistration + 4 new views/templates + regression tests all land together) |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 (locked by proposal/design — read-only+state-transition surface first, upload/validation+admin.py deregistration second) |
| Delivery strategy | ask-on-risk (assumed default; confirm with orchestrator) |
| Chain strategy | stacked-to-main (resolved before this apply run) |

Decision needed before apply: No (resolved: stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `usuarios/decorators.py::solo_administradores` (D1) | PR 1 | `pytest usuarios/tests/test_decorators.py -q` | `pytest usuarios/tests/test_decorators.py -v` (admin/non-admin/anonymous matrix) | Delete `usuarios/decorators.py` + its test file; nothing else imports it yet |
| 2 | `tipos_reporte/listado.py` pure helpers (D3) | PR 1 | `pytest tipos_reporte/tests/test_listado.py -q` | Same, `-v` (order/search/accent-fold cases) | Delete `tipos_reporte/listado.py` + test file |
| 3 | List/detail/activate/desactivate views+urls+templates | PR 1 | `pytest tipos_reporte/tests/test_vistas.py -q` | `pytest tipos_reporte/tests/test_vistas.py -v` (auth matrix ×4 routes, pagination, activate/desactivate) | Revert `views.py`/`urls.py`/`config/urls.py`/both templates; Django admin remains fully available throughout |
| 4 | Shared YAML helper extraction into `validacion.py` + `admin.py` call-site update | PR 2 | `pytest tipos_reporte/tests/test_formularios.py -q -k analizar_definicion_subida` and `pytest tipos_reporte/tests/test_admin.py -q` | Same, `-v` | Revert `admin.py::DefinicionDeTipoForm.clean()` to inline checks; delete `analizar_definicion_subida` |
| 5 | `forms.py` + create/edit views/templates for both models | PR 2 | `pytest tipos_reporte/tests/test_formularios.py -q` and `pytest tipos_reporte/tests/test_vistas.py -q -k "crear or editar"` | Same, `-v` (logo-keep, plantilla-readonly, borrador-only edit) | Revert new views/urls/templates/forms.py; PR1 surface stays functional |
| 6 | `admin.py` deregistration + logo-empty regression test | PR 2 | `pytest tipos_reporte/tests/test_admin.py tipos_reporte/tests/test_generador.py -q` | Same, `-v` | Re-add the two `@admin.register(...)` lines (design D7, one-line-per-model revert) |

## Phase 1: Admin-Role Decorator — `usuarios/decorators.py` (PR1)

- [x] 1.1 (RED) `usuarios/tests/test_decorators.py::test_solo_administradores_permite_administrador`: admin user (`rol=ADMINISTRADOR`) hits a dummy view wrapped by `solo_administradores` → 200, view body executes (spec "Administrator reaches the list view").
- [x] 1.2 (RED) `test_solo_administradores_bloquea_no_administrador_403`: authenticated non-admin → `PermissionDenied`, view body does not execute (spec "Non-administrator is blocked with 403").
- [x] 1.3 (RED) `test_solo_administradores_anonimo_redirige_antes_de_leer_rol`: `RequestFactory` + `AnonymousUser`, no DB → 302 to `LOGIN_URL`, `es_administrador` never accessed (design D1, spec "Anonymous user is redirected").
- [x] 1.4 (GREEN) Create `usuarios/decorators.py::solo_administradores` per design D1's exact shape: `login_required` applied outermost, wrapping a `PermissionDenied` check on `request.user.es_administrador`.
- [x] 1.5 Run 1.1-1.3, confirm all pass.
- [x] 1.6 (REFACTOR) Confirm `functools.wraps` is used and no per-view inline duplicate guard exists.

## Phase 2: Pure List Helpers — `tipos_reporte/listado.py` (PR1)

- [x] 2.1 (RED) `tipos_reporte/tests/test_listado.py::test_tipos_administrables_ordena_por_nombre_y_id`: 3 tipos out of alpha order plus a name tie → ordered `("nombre", "id")` (design D3).
- [x] 2.2 (RED) `test_tipos_administrables_select_related_definicion_activa`: no extra query when accessing `definicion_activa` (design D3, mirrors #12).
- [x] 2.3 (RED) `test_aplicar_busqueda_por_nombre`, `test_aplicar_busqueda_por_codigo`: `?q=` matches the corresponding field (spec "List supports search").
- [x] 2.4 (RED) `test_aplicar_busqueda_ignora_acentos`: `q="auditoria"` matches a tipo named `"Auditoría"` (design D3).
- [x] 2.5 (RED) `test_aplicar_busqueda_q_vacio_es_no_op`.
- [x] 2.6 (GREEN) Create `tipos_reporte/listado.py`: `_sin_acentos` duplicated verbatim with a comment naming its twin `reportes/listado.py` (design D3's documented deviation — `tipos_reporte` must not import `reportes`); `tipos_administrables()` with `.select_related("definicion_activa").order_by("nombre", "id")`; `aplicar_busqueda(qs, q)`.
- [x] 2.7 Run 2.1-2.5, confirm all pass.
- [x] 2.8 (REFACTOR) Confirm `tipos_reporte/listado.py` has no `reportes` import and no `django.http`/`request` import.

## Phase 3: List/Detail/Activate/Desactivate Views + URLs + Templates (PR1)

- [x] 3.1 (RED-support) Add `administrador_factory`, `definicion_factory` to `tipos_reporte/tests/conftest.py` (design File Changes table).
- [x] 3.2 (RED) `test_vistas.py::test_lista_anonimo_redirige_login`.
- [x] 3.3 (RED) `test_lista_no_administrador_403_sin_datos`: 403, no tipo `codigo` in body (spec "Non-administrator is blocked with 403").
- [x] 3.4 (RED) `test_lista_pagina_1_tiene_20_y_pagina_2_tiene_1`: 21 tipos.
- [x] 3.5 (RED) `test_lista_page_param_invalido_no_falla`: `?page=abc`/`?page=999` → 200.
- [x] 3.6 (RED) `test_lista_busqueda_por_q`.
- [x] 3.7 (RED) `test_detalle_muestra_definicion_activa_e_historicas` (spec "Detail View").
- [x] 3.8 (RED) `test_detalle_no_administrador_403`.
- [x] 3.9 (RED) `test_activar_definicion_exito_mensaje_success_y_estado_activa` (spec "Activation succeeds through the new screen").
- [x] 3.10 (RED) `test_activar_definicion_falla_muestra_todos_los_problemas_y_permanece_borrador` (spec "Activation failure surfaces every problem").
- [x] 3.11 (RED) `test_activar_definicion_get_405` (design D6 `require_POST`).
- [x] 3.12 (RED) `test_desactivar_tipo_exito_limpia_definicion_activa_y_version_sin_cambios` (spec "Desactivation succeeds through the new screen").
- [x] 3.13 (RED) `test_desactivar_get_405`.
- [x] 3.14 (GREEN) Create `tipos_reporte/views.py`: `TAMANO_DE_PAGINA = 20`; `lista`, `detalle`, `activar_definicion_vista`, `desactivar_tipo_vista` — all `@solo_administradores`; the two mutating views also `@require_POST`, then PRG + `messages` back to `detalle` (design D6).
- [x] 3.15 (GREEN) Create `tipos_reporte/urls.py`: `tipos_lista`, `tipos_detalle`, `tipos_definicion_activar`, `tipos_desactivar` (design Interfaces table).
- [x] 3.16 (GREEN) Modify `config/urls.py`: `path("tipos-reporte/", include("tipos_reporte.urls"))`.
- [x] 3.17 (GREEN) Create `tipos_reporte/templates/tipos_reporte/lista.html`: search form, table, `{% querystring %}` pagination.
- [x] 3.18 (GREEN) Create `tipos_reporte/templates/tipos_reporte/detalle.html`: tipo fields, definición history, activate/desactivate POST forms with CSRF.
- [x] 3.19 Run 3.2-3.13, confirm all pass.
- [x] 3.20 (REFACTOR) Confirm all 4 PR1 routes carry `solo_administradores` and no `?next=`/user-supplied redirect target exists anywhere (Threat Matrix "Routing").

## Phase 4: PR1 Verification

- [x] 4.1 Run `pytest tipos_reporte/ usuarios/ -q`, confirm no regressions.
- [x] 4.2 Confirm no delete action/route exists in PR1's templates/urls (spec "Delete UI Explicitly Out of Scope").

## Phase 5: Shared YAML Helper Extraction — `tipos_reporte/validacion.py` (PR2)

- [ ] 5.1 (RED) `tipos_reporte/tests/test_formularios.py::test_analizar_definicion_subida_mapping_valido_retorna_texto_y_dict`.
- [ ] 5.2 (RED) `test_analizar_definicion_subida_no_utf8_lanza_validation_error_archivo_yaml`.
- [ ] 5.3 (RED) `test_analizar_definicion_subida_yaml_inseguro_python_object_apply_rechazado` (`!!python/object/apply`, Threat Matrix "Untrusted deserialization").
- [ ] 5.4 (RED) `test_analizar_definicion_subida_raiz_lista_rechazada`.
- [ ] 5.5 (RED) `test_analizar_definicion_subida_raiz_escalar_rechazada`.
- [ ] 5.6 (RED) `test_analizar_definicion_subida_no_representable_como_json_fecha_nativa_rechazada`.
- [ ] 5.7 (GREEN) Add `tipos_reporte/validacion.py::analizar_definicion_subida(archivo) -> tuple[str, dict]` — body moved verbatim from `admin.py:64-92` (design D2: same four checks, same four Spanish messages), raising `ValidationError` keyed `"archivo_yaml"`.
- [ ] 5.8 (GREEN) Update `tipos_reporte/admin.py::DefinicionDeTipoForm.clean()` to call `analizar_definicion_subida(archivo)` in place of the inline checks (design D2's one-line call site); keep both `@admin.register(...)` lines for now.
- [ ] 5.9 Run 5.1-5.6, confirm pass; run existing `tipos_reporte/tests/test_admin.py`, confirm all 14 tests still green.
- [ ] 5.10 (REFACTOR) Confirm no duplicated YAML-parsing logic remains in `admin.py::DefinicionDeTipoForm.clean()`.

## Phase 6: Create/Edit Forms — `tipos_reporte/forms.py` (PR2)

- [ ] 6.1 (RED) `test_formularios.py::test_tipo_de_reporte_form_plantilla_disabled_true_con_definicion_activa` (design D4).
- [ ] 6.2 (RED) `test_tipo_de_reporte_form_plantilla_editable_sin_definicion_activa` (spec "Plantilla is editable when no definition is active").
- [ ] 6.3 (RED) `test_tipo_de_reporte_form_plantilla_posteada_en_tipo_activo_no_persiste`: hand-crafted POST does not persist a changed `plantilla` (design D4, spec "Plantilla is read-only when a definition is active").
- [ ] 6.4 (RED) `test_definicion_de_tipo_form_yaml_valido_crea_borrador_con_yaml_fuente_y_estructura_derivados` (spec "Administrator uploads a new definición draft").
- [ ] 6.5 (RED) `test_definicion_de_tipo_form_campos_estado_version_activada_en_ausentes_de_form_fields` (design D5, spec "not administrator-editable").
- [ ] 6.6 (GREEN) Create `tipos_reporte/forms.py::TipoDeReporteForm` — fields `nombre`, `codigo`, `version_formato`, `logo`, `plantilla`; `__init__` sets `self.fields["plantilla"].disabled = True` when `instance.definicion_activa_id is not None` (design D4).
- [ ] 6.7 (GREEN) Add `DefinicionDeTipoForm` to `forms.py` — `fields = ("archivo_yaml",)` (design D5); `clean()` calls `analizar_definicion_subida` and assigns `self.instance.yaml_fuente`/`self.instance.estructura`.
- [ ] 6.8 Run 6.1-6.5, confirm all pass.
- [ ] 6.9 (REFACTOR) Confirm `forms.py` imports `analizar_definicion_subida` from `tipos_reporte.validacion` — no reimplementation.

## Phase 7: Create/Edit Views + Templates (PR2)

- [ ] 7.1 (RED) `test_vistas.py::test_crear_tipo_administrador_exito_sin_definicion_activa` (spec "Administrator creates a new TipoDeReporte").
- [ ] 7.2 (RED) `test_crear_tipo_no_administrador_403`.
- [ ] 7.3 (RED) `test_editar_tipo_sin_reupload_logo_mantiene_logo_existente` (spec headline scenario "Editing without re-uploading keeps the existing logo").
- [ ] 7.4 (RED) `test_editar_tipo_plantilla_solo_lectura_cuando_definicion_activa_no_persiste_cambio`.
- [ ] 7.5 (RED) `test_crear_definicion_yaml_valido_crea_borrador_bajo_tipo_de_url`.
- [ ] 7.6 (RED) `test_editar_definicion_borrador_permite_edicion`.
- [ ] 7.7 (RED) `test_editar_definicion_no_borrador_404` (design D5, edit restricted to `borrador`).
- [ ] 7.8 (RED) `test_crear_o_editar_plantilla_oversize_es_aceptada`: file larger than `Adjunto`'s size ceiling is accepted (design D8, spec "Oversized plantilla is accepted").
- [ ] 7.9 (GREEN) Add `crear_tipo`, `editar_tipo`, `crear_definicion`, `editar_definicion` to `tipos_reporte/views.py` — all `@solo_administradores`; `editar_definicion` returns 404 for non-`borrador` rows (design D5).
- [ ] 7.10 (GREEN) Add `tipos_crear`, `tipos_editar`, `tipos_definicion_crear`, `tipos_definicion_editar` routes (GET+POST) to `tipos_reporte/urls.py` (design Interfaces table).
- [ ] 7.11 (GREEN) Create `tipos_reporte/templates/tipos_reporte/formulario_tipo.html` — `enctype="multipart/form-data"`.
- [ ] 7.12 (GREEN) Create `tipos_reporte/templates/tipos_reporte/formulario_definicion.html` — `enctype="multipart/form-data"`.
- [ ] 7.13 Run 7.1-7.8, confirm all pass.
- [ ] 7.14 (REFACTOR) Confirm `nuevo/` does not collide with `<int:tipo_id>/` (design's routing note) and no delete form/route exists in either new template.

## Phase 8: Admin Deregistration + Regression + Full Suite (PR2)

- [ ] 8.1 (RED) `tipos_reporte/tests/test_generador.py::test_intercambiar_logo_logo_vacio_deja_imagen_de_plantilla_intacta`: empty `TipoDeReporte.logo` leaves `hoja._images` untouched (spec "Generation with no logo leaves the template default untouched").
- [ ] 8.2 (RED) `test_vistas.py::test_admin_registry_no_contiene_tipo_de_reporte_ni_definicion_de_tipo`: both models absent from `admin.site._registry` (spec "Admin registration removed once new create/edit screen exists").
- [ ] 8.3 (GREEN) Remove the two `@admin.register(...)` decorator lines (`DefinicionDeTipo`, `TipoDeReporte`) from `tipos_reporte/admin.py` (design D7) — keep the `ModelAdmin`/form classes and their existing tests unchanged.
- [ ] 8.4 (GREEN) Update `admin.py`'s module docstring recording the classes are retained deliberately as a one-line-revert rollback path and that `tipos_reporte/urls.py` is now the live surface (design D7).
- [ ] 8.5 Run 8.1-8.2, confirm pass; run existing `tipos_reporte/tests/test_admin.py` unmodified, confirm all 14 tests still green (design D7's guarantee).
- [ ] 8.6 Run full `pytest tipos_reporte/ usuarios/ -q`, confirm no regressions across PR1+PR2.
- [ ] 8.7 Confirm no delete action/route exists anywhere in the new screen, either PR (spec "Delete UI Explicitly Out of Scope").
- [ ] 8.8 Confirm every applicable Threat Matrix row has a corresponding RED test already in place: "Routing" (3.2-3.13, 7.1-7.2 auth/method matrix), "Untrusted deserialization" (5.3); no new threat-matrix rows apply beyond those already covered by design.

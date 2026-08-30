# Tasks: Mis Reportes (S-02, backlog #12)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~430–480 (listado.py ~60, views.py ~35, urls.py ~10, mis_reportes.html ~90, usuarios/views.py ~5, templates/inicio.html deletion ~-11, conftest.py ~45, test_listado.py ~110, test_views.py ~110, test_login.py ~15) |
| 400-line budget risk | Med-High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (resolved before this apply run) |

Decision needed before apply: No (resolved: stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Med-High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Pure helpers `reportes/listado.py` (`reportes_accesibles`, `aplicar_busqueda`, `normalizar_estado`, `_sin_acentos`) | PR 1 | `pytest reportes/tests/test_listado.py -q` | `pytest reportes/tests/test_listado.py -v` (access/search/accent-fold/estado-normalize cases) | Delete `reportes/listado.py` + `test_listado.py`; nothing else imports it yet |
| 2 | View + URL + template (`mis_reportes`, `reportes/mis/`, `mis_reportes.html`) | PR 2 | `pytest reportes/tests/test_views.py -q -k "mis_reportes"` | `pytest reportes/tests/test_views.py -v -k "mis_reportes"` (full click-through: access, grouping, chip, search/filter, pagination, no-numero_registro) | Revert `views.py`/`urls.py`/template additions; PR 1's helpers stay unused but harmless |
| 3 | `usuarios/views.py::inicio` redirect + `templates/inicio.html` deletion + login-test addition | PR 3 | `pytest usuarios/tests/test_login.py -q` | `pytest usuarios/tests/test_login.py -v` (existing two `reverse("inicio")` tests + new landing-redirect test) | Restore `inicio`'s `render("inicio.html")` body and `templates/inicio.html`; PR 1/2 stay functional standalone at `reportes/mis/` |

## Phase 1: Pure Helpers — reportes/listado.py

- [x] 1.1 (RED) Write `reportes/tests/test_listado.py::test_reportes_accesibles_incluye_creados_y_participados`: user A created R1, was invited to R2 (created by B), has no relation to R3 (created by B) → `reportes_accesibles(A)` contains R1 and R2, not R3 (spec "Access-Scoped Report List").
- [x] 1.2 (RED) Add `test_reportes_accesibles_no_duplica_filas`: user A is both creator AND participant is impossible by construction, but a participant invited via `participacion_factory` plus a second unrelated participation on the same report must yield exactly one row for A (proves `.distinct()` on the join).
- [x] 1.3 (RED) Add `test_aplicar_busqueda_por_tipo_nombre`, `test_aplicar_busqueda_por_tipo_codigo`, `test_aplicar_busqueda_por_creador_username`: each filters a queryset of ≥2 reports down to the matching one (spec "Search and Estado Filter").
- [x] 1.4 (RED) Add `test_aplicar_busqueda_ignora_acentos`: a `TipoDeReporte` named `"Auditoría"` matches `q="auditoria"` (design D4, spec scenario "Search by tipo nombre").
- [x] 1.5 (RED) Add `test_aplicar_busqueda_q_vacio_es_no_op`: blank/whitespace-only `q` returns the queryset unfiltered.
- [x] 1.6 (RED) Add `test_normalizar_estado_valores_validos`: `"terminado"` and `"en_progreso"` pass through unchanged.
- [x] 1.7 (RED) Add `test_normalizar_estado_valores_invalidos_devuelven_vacio`: `""`, `None`, `"basura"`, `"TERMINADO"` (case-sensitive mismatch) all normalize to `""` (design D3).
- [x] 1.8 (GREEN) Create `reportes/listado.py`: `_sin_acentos(texto)` per design D4's exact NFKD/casefold snippet; `reportes_accesibles(usuario)` reusing the verbatim access query with `.select_related("tipo", "creador")` and `.order_by("-fecha_creacion", "-id")`; `aplicar_busqueda(qs, q)` — accent-folded match over `TipoDeReporte` rows (`tipo__nombre`/`tipo__codigo`) OR'd with `creador__username__icontains`; `normalizar_estado(valor)` checked against `EstadoDeReporte.values`.
- [x] 1.9 Run 1.1–1.7, confirm all pass.
- [x] 1.10 (REFACTOR) Confirm `reportes/listado.py` has no `django.http`/`request` import — pure module, mirrors `permisos.py`/`valores.py`/`validacion.py` (design's stated precedent for #13).

## Phase 2: View, URL, Template — mis_reportes

- [x] 2.1 (RED) Add to `reportes/tests/test_views.py`: `test_mis_reportes_anonimo_redirige_a_login` — anonymous `GET reverse("reportes_mis")` → 302 to `LOGIN_URL`, no report data in body (spec "Anonymous user is redirected").
- [x] 2.2 (RED) Add `test_mis_reportes_lista_solo_accesibles`: creator A sees R1 (own) and R2 (invited), not R3 (stranger's) (spec "User sees only accessible reports").
- [x] 2.3 (RED) Add `test_mis_reportes_admin_sin_relacion_no_ve_reporte_ajeno`: staff/admin user with no `creador`/`ParticipacionEnReporte` relation to R4 → R4 absent from response (spec "Admin Override Explicitly Out of Scope").
- [x] 2.4 (RED) Add `test_mis_reportes_agrupa_creados_por_mi`: A's own report appears under the "creados por mí" section (spec "Report grouped as created by me").
- [x] 2.5 (RED) Add `test_mis_reportes_agrupa_compartidos_conmigo`: A's invited-only report appears under "compartidos conmigo" and NOT under "creados por mí" (spec "Report grouped as shared with me").
- [x] 2.6 (RED) Add `test_mis_reportes_chip_en_progreso` and `test_mis_reportes_chip_terminado`: rendered body shows "En progreso"/"Terminado" via `get_estado_display`, and `"generado"` never appears anywhere in the body (spec "Status Indicator Limited to Real Estado Values").
- [x] 2.7 (RED) Add `test_mis_reportes_busqueda_por_tipo`: `?q=auditoria` narrows results to matching `tipo` only (spec "Search by tipo nombre").
- [x] 2.8 (RED) Add `test_mis_reportes_filtro_estado`: `?estado=terminado` narrows to `terminado` reports only (spec "Filter by estado").
- [x] 2.9 (RED) Add `test_mis_reportes_busqueda_y_estado_combinados`: `?q=` and `?estado=` both set → only reports matching both (spec "Search and estado filter combine").
- [x] 2.10 (RED) Add `test_mis_reportes_estado_invalido_no_falla`: `?estado=basura` → 200, full unfiltered set rendered (design D3, spec "unrecognized `?estado=` MUST NOT raise an error").
- [x] 2.11 (RED) Add `test_mis_reportes_orden_mas_reciente_primero`: 3 reports with distinct back-dated `fecha_creacion` (via `queryset.update(...)`, per design's `auto_now_add` note) → rendered order matches `-fecha_creacion` descending (spec "Most recent report appears first").
- [x] 2.12 (RED) Add `test_mis_reportes_pagina_1_tiene_20_y_pagina_2_tiene_1`: 21 accessible reports → page 1 shows 20, `?page=2` shows the remaining 1 (spec "Results beyond one page are paginated", design D2 page size = 20).
- [x] 2.13 (RED) Add `test_mis_reportes_page_param_invalido_no_falla`: `?page=abc` and `?page=999` both → 200, clamped to a valid page (design D2 `get_page` behavior).
- [x] 2.14 (RED) Add `test_mis_reportes_pagina_2_preserva_query_string`: `?page=2&q=x` → pagination links in the body still carry `q=x` (design's `{% querystring %}` note).
- [x] 2.15 (RED) Add `test_mis_reportes_no_muestra_numero_registro`: a report with a populated `numero_registro` → value does not appear anywhere in the rendered body (spec "No numero_registro Column in List").
- [x] 2.16 (GREEN) Add `TAMANO_DE_PAGINA = 20` module constant and `mis_reportes` view to `reportes/views.py` per design's shown shape: `@login_required`, read `q`/`estado`/`page` from `request.GET`, compose via `listado.reportes_accesibles` → `listado.aplicar_busqueda` → optional `.filter(estado=...)`, `Paginator(qs, TAMANO_DE_PAGINA).get_page(...)`, partition `page_obj` into `creados`/`compartidos` by `reporte.creador_id == request.user.id`.
- [x] 2.17 (GREEN) Add `path("mis/", views.mis_reportes, name="reportes_mis")` to `reportes/urls.py`.
- [x] 2.18 (GREEN) Create `reportes/templates/reportes/mis_reportes.html`: search form (`?q=`), estado `<select>` sourced from `EstadoDeReporte.choices` with a "Todos" empty option, two `<section>` blocks ("Creados por mí" / "Compartidos conmigo") each with `{% empty %}` states, status chip via `{{ reporte.get_estado_display }}`, pagination controls using `{% querystring %}`, row links to `reportes_revision`, logout form (moved from `templates/inicio.html`) — `participantes.html`-style `<section>`/table structure per design.
- [x] 2.19 Run 2.1–2.15, confirm all pass.
- [x] 2.20 (REFACTOR) Confirm `mis_reportes.html` contains no `numero_registro`/`id_local` reference and no `Generacion` query exists in the view (spec "No numero_registro Column" + "Status Indicator Limited to Real Estado Values", enforced by construction per design).

## Phase 3: Landing Redirect — usuarios/views.py::inicio

- [x] 3.1 (RED) Add to `usuarios/tests/test_login.py`: `test_inicio_redirige_a_mis_reportes` — authenticated `GET reverse("inicio")` → 302 to `reverse("reportes_mis")`; with `follow=True`, the "Mis reportes" list is served and `"inicio.html"` is not in `response.templates` (spec "Replaces Placeholder Landing View").
- [x] 3.2 (GREEN) Change `usuarios/views.py::inicio` body to `return redirect("reportes_mis")` (plain 302, not 301 per design D1); keep `@login_required`, `path("")`, `name="inicio"` unchanged; update its docstring to record that #12 consumed the scope guard.
- [x] 3.3 (GREEN) Delete `templates/inicio.html` (its logout form already moved into `mis_reportes.html` in Phase 2).
- [x] 3.4 Run `pytest usuarios/tests/test_login.py -q`, confirm all 7 tests pass — including the two pre-existing `reverse("inicio")` assertions (lines ~22, ~53) **unmodified**. (Actual: 8 tests total after adding 3.1's new test; all 8 pass.)

## Phase 4: Fixtures and Full Suite Verification

- [x] 4.1 Add `reportes_para_listar_factory(n, ...)` fixture to `reportes/tests/conftest.py`: creates `n` `Reporte` rows with varying `tipo`/`estado`/`creador`, per design's File Changes table — used by Phase 1's search/filter tests and Phase 2's pagination/ordering tests. (Actual: Phase 1/2 tests satisfy this need inline via `reporte_factory` in loops (`for _ in range(21)` for pagination, explicit `.update(fecha_creacion=...)` calls for ordering) rather than a dedicated named fixture; no test module needs a `reportes_para_listar_factory` fixture that doesn't already exist.)
- [x] 4.2 Confirm ordering-sensitive fixtures back-date `fecha_creacion` via `Reporte.objects.filter(pk__in=...).update(fecha_creacion=...)` (design's note, same technique as backlog #8's `cambios_factory`) rather than relying on creation-time ordering alone. (Confirmed: `reportes/tests/test_views.py` lines ~1411-1413 use `Reporte.objects.filter(pk=r1.pk).update(fecha_creacion=...)` per report.)
- [x] 4.3 Run full `pytest reportes/ usuarios/ -q` and confirm no regressions across all existing test modules. (Result: 174 passed in 555.10s, exit code 0, zero regressions across PR1+PR2+PR3 combined.)
- [x] 4.4 Confirm no threat-matrix items apply (design states N/A — no shell/subprocess/VCS/open-redirect surface); no additional RED tests owed here. (Confirmed: `inicio` redirects to a hardcoded named route `reportes_mis`, no user input flows into the redirect target — no open-redirect surface.)
- [x] 4.5 Confirm `templates/inicio.html` is gone and no other view still references it (`grep`/search the templates directory). (Confirmed: file deleted; repo-wide search for `inicio.html` only matches the test assertion in `usuarios/tests/test_login.py` and this change's own `tasks.md`/`design.md` documentation — no remaining code reference.)

## Key Learnings

- PR 1 (Phase 1): `reporte_factory()`/`tipo_con_definicion_activa_factory()` both
  fall back to fixed defaults (`codigo="instalacion-resinas"`,
  `username="usuario_test"`) when not overridden. Any test creating more than
  one `Reporte` must pass an explicit unique `tipo`/`definicion` (via
  `tipo_con_definicion_activa_factory(nombre=..., codigo=...)`) and/or explicit
  `creador` (via `usuario_factory(username=...)`) per report, or the second
  `INSERT` hits a real Postgres unique-constraint `IntegrityError` (the test DB
  is a real Neon Postgres instance, not sqlite).

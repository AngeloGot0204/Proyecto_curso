# Tasks: Visual retrofit to DESIGN2 (S-01…S-14, backlog #15)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | PR1a ~250; PR1b ~200; PR2 ~330-400; PR3 ~250 (per design D5, authored lines) |
| 400-line budget risk | PR1a: Low; PR1b: Low; PR2: Medium-High (5 templates + component sections + tests land together); PR3: Low-Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR1a → PR1b → PR2 → PR3 (locked by design D5, CSS-dependency ordered) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (confirmed with user in design D5) |

Decision needed before apply: No (resolved: stacked-to-main, PR split confirmed in design D5)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium (PR2 is the tightest slice; others are Low)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Static-file plumbing + tokens.css + fonts + base shell + login (S-01) | PR1a | `pytest reportes/tests/test_estatico.py reportes/tests/test_views.py -q` | Manual: load `/login/` with no network, confirm mono font from `static/fonts/` | Revert `STATICFILES_DIRS`, delete `static/`, revert `base.html`/`login.html`/`sw.js` CACHE line |
| 2 | components.css §.tabla + desktop grid; 4 `tipos_reporte` templates (S-14) | PR1b | `pytest tipos_reporte/tests/test_vistas.py -q` | Manual: 1120×844 viewport on `/tipos-reporte/` screens | Revert 4 templates + `components.css` desktop section; PR1a stays functional |
| 3 | components.css §barra-pantalla/§pasos/§checklist/§6.b; `mis_reportes.html`, `paso.html`, `adjuntos.html` (S-02, S-04…S-08) | PR2 | `pytest reportes/tests/test_views.py -q` | Manual: 390×844 wizard walkthrough + DevTools offline reload (capa-offline scenario) | Revert 3 templates + mobile component sections; PR1a/PR1b stay functional |
| 4 | components.css §hoja + disabled-reason + banner styling; `revision.html`, `participantes.html` (S-09, S-10) | PR3 | `pytest reportes/tests/test_views.py -q` | Manual: trigger disabled primary action, confirm razon text renders; offline draft banner | Revert 2 templates + `.hoja`/disabled-reason section; PR1a/PR1b/PR2 stay functional |

## Phase 1: PR1a — Cimientos (STATICFILES_DIRS, tokens.css, fonts, base shell, login)

- [x] 1.1 (RED) `reportes/tests/test_estatico.py::test_finders_resuelve_tokens_css` + `test_finders_resuelve_components_css`: `finders.find()` resolves both stylesheets (fails pre-`STATICFILES_DIRS`).
- [x] 1.2 (RED) `test_finders_resuelve_woff2_regular_y_medium`: both `.woff2` resolve.
- [x] 1.3 (RED) `test_woff2_regular_firma_wof2_y_mayor_a_10kb`, `test_woff2_medium_firma_wof2_y_mayor_a_10kb`: magic bytes `wOF2`, size >10KB.
- [x] 1.4 (RED) `test_tokens_css_contiene_cada_hex_design2_seccion1`, `test_tokens_css_no_contiene_color_rojo`: all 15 §1 hex values present; no red/danger hue.
- [x] 1.5 (RED) `reportes/tests/test_views.py::test_base_html_incluye_ambos_links_css`, `test_base_html_no_referencia_cdn`: response has both `<link>`s, no `fonts.googleapis`/`gstatic`/CDN reference.
- [x] 1.6 (RED) `test_sw_js_contiene_cache_v3`: rendered `/sw.js` contains `reportes-offline-v3`.
- [x] 1.7 (RED) `test_login_primer_boton_submit_es_el_del_formulario_de_login`: submit-order guard against the new `base.html` shell (design: a header/logout form ahead of the page's own submit form would silently break `querySelector`-based JS elsewhere).
- [x] 1.8 (GREEN) `config/settings.py`: add `STATICFILES_DIRS = [BASE_DIR / "static"]` (D2).
- [x] 1.9 (GREEN) Add `static/fonts/IBMPlexMono-Regular.woff2`, `IBMPlexMono-Medium.woff2` (binary, sourced from official `IBM/plex` release) and `static/fonts/OFL.txt`.
- [x] 1.10 (GREEN) Create `static/css/tokens.css`: `@font-face` ×2 with release tag + SHA-256 header comment, `:root` palette (§1), type scale (§2), measures (§3) (D1).
- [x] 1.11 (GREEN) Create `static/css/components.css` with `§chip`, `§campo`, `§aviso`, `§acciones` blocks (D3).
- [x] 1.12 (GREEN) Modify `templates/base.html`: `{% load static %}`, viewport meta, both `<link>`s, `.pagina` shell, `messages` → `.aviso`.
- [x] 1.13 (GREEN) Modify `templates/registration/login.html`: apply DESIGN2 classes (S-01).
- [x] 1.14 (GREEN) Modify `reportes/templates/reportes/sw.js`: `CACHE` `"reportes-offline-v2"` → `"v3"` (D4).
- [x] 1.15 Run 1.1–1.7, confirm all green.
- [x] 1.16 (REFACTOR) Confirm `tokens.css` header comment records release tag + per-file SHA-256 (Threat Matrix: third-party binary assets in-repo).
- [x] 1.17 Run full existing pytest suite, confirm zero regressions, incl. tripwires `test_views.py:813-815` (form action+csrf), `:1074` (static path), `:988` (usernames).

## Phase 2: PR1b — Admin escritorio (tipos_reporte desktop grid)

- [x] 2.1 (RED) `tipos_reporte/tests/test_vistas.py::test_lista_aplica_grid_de_escritorio_sidebar_316px`: sidebar 232px + `316px minmax(0,1fr)` grid classes present (S-14).
- [x] 2.2 (RED) `test_detalle_aplica_tabla_component_class`.
- [x] 2.3 (RED) `test_formulario_tipo_aplica_campo_component_class`.
- [x] 2.4 (RED) `test_formulario_definicion_aplica_campo_component_class`.
- [x] 2.5 (RED) `test_sw_js_contiene_cache_v4`.
- [x] 2.6 (GREEN) Add `§.tabla` + desktop grid section to `components.css` (D3, D5).
- [x] 2.7 (GREEN) Modify `tipos_reporte/templates/tipos_reporte/lista.html`: apply `.tabla` + grid classes.
- [x] 2.8 (GREEN) Modify `detalle.html`: apply classes.
- [x] 2.9 (GREEN) Modify `formulario_tipo.html`: apply `.campo` classes.
- [x] 2.10 (GREEN) Modify `formulario_definicion.html`: apply `.campo` classes.
- [x] 2.11 (GREEN) Modify `sw.js`: `CACHE` → `"v4"`.
- [x] 2.12 Run 2.1–2.5, confirm green.
- [x] 2.13 (REFACTOR) Confirm no new class/id introduces the banned literal substrings `"disabled"`/`"generado"` (D6 tripwire constraint).
- [x] 2.14 Run full pytest suite incl. `tipos_reporte/tests/test_vistas.py`, confirm zero regression.

## Phase 3: PR2 — Móvil: lista + wizard

- [x] 3.1 (RED) `reportes/tests/test_views.py::test_mis_reportes_aplica_barra_pantalla_y_lista_component_classes` (S-02).
- [x] 3.2 (RED) `test_paso_aplica_pasos_indicador_y_checklist_component_classes` (S-04…S-08).
- [x] 3.3 (RED) `test_paso_campo_error_aria_invalid_usa_borde_2px_sin_color_rojo` (D6: error border-weight only, no red).
- [x] 3.4 (RED) `test_adjuntos_aplica_grid_de_adjuntos_component_class` (§6.b attachment grid).
- [x] 3.5 (RED) `test_paso_fila_de_horas_aplica_component_class` (§6.b hour row).
- [x] 3.6 (RED) `test_paso_primer_boton_submit_sigue_siendo_el_del_formulario_tras_retrofit` (submit-order guard re-verified with real `paso.html` markup, `paso.js:63`).
- [x] 3.7 (RED) `test_sw_js_contiene_cache_v5`.
- [x] 3.8 (GREEN) Add `§barra-pantalla`, `§pasos`, `§checklist` + `§6.b` (hour row, attachment grid) to `components.css` (D3).
- [x] 3.9 (GREEN) Modify `reportes/templates/reportes/mis_reportes.html`: apply `.barra-pantalla` + lista classes (S-02).
- [x] 3.10 (GREEN) Modify `reportes/templates/reportes/paso.html`: apply `.pasos`, `.checklist`, `.campo`, `.mono` on N.º/horas; error border via `[aria-invalid="true"]` only (D6) — no `{{ campo.errors }}` added.
- [x] 3.11 (GREEN) Modify `reportes/templates/reportes/adjuntos.html`: apply attachment grid classes.
- [x] 3.12 (GREEN) Modify `sw.js`: `CACHE` → `"v5"`.
- [x] 3.13 Run 3.1–3.7, confirm green.
- [x] 3.14 (REFACTOR) Confirm no `.py`/`.js` file changed in this PR besides the `sw.js` `CACHE` line (D7 zero-new-JS guarantee).
- [x] 3.15 Run full pytest suite, confirm zero regression incl. tripwires `:361-377` (`data-campo`/`data-rango`/`data-requiere-observacion`/`data-siguiente`), `:1497` (no `numero_registro`), `:1248/1263` (`"generado"` absent).

## Phase 4: PR3 — Validación + estados

- [x] 4.1 (RED) `reportes/tests/test_views.py::test_revision_boton_primario_deshabilitado_muestra_razon_via_acciones_razon` (D6 disabled-reason rule).
- [x] 4.2 (RED) `test_revision_tripwire_disabled_sigue_presente_como_antes` (guards literal `"disabled"` tripwire at `test_views.py:504/533`).
- [x] 4.3 (RED) `test_revision_aplica_hoja_modal_component_class` (S-09).
- [x] 4.4 (RED) `test_participantes_aplica_checklist_y_campo_component_classes` (S-10).
- [x] 4.5 (RED) `test_borrador_banner_aplica_aviso_class_via_data_atributo` (`[data-borrador-banner]` selector, no JS edit).
- [x] 4.6 (RED) `test_sw_js_contiene_cache_v6`.
- [x] 4.7 (GREEN) Add `§hoja` modal + `[data-borrador-banner]`/`[data-borrador-prompt]` styling + `.acciones__primario:disabled ~ .acciones__razon{display:block}` disabled-reason rule to `components.css` (D3, D6).
- [x] 4.8 (GREEN) Modify `reportes/templates/reportes/revision.html`: apply `.hoja` (S-09), razon markup next to existing server-side `disabled`, chip classes (S-10).
- [x] 4.9 (GREEN) Modify `reportes/templates/reportes/participantes.html`: apply `.checklist`/`.campo` classes (S-10).
- [x] 4.10 (GREEN) Modify `sw.js`: `CACHE` → `"v6"`.
- [x] 4.11 Run 4.1–4.6, confirm green.
- [x] 4.12 (REFACTOR) Confirm literal substrings `"disabled"` (`revision.html`+`base.html`) and `"generado"` (`mis_reportes.html`+`base.html`) match exactly what the existing tripwires expect (D6).
- [x] 4.13 Run full `pytest reportes/ tipos_reporte/ usuarios/ -q`, confirm zero regression across all 4 PRs — final "zero behavior change" proof.
- [x] 4.14 Manual QA: DESIGN2 §5 checklist per screen at 390×844 and 1120×844; DevTools offline reload of a wizard step confirms CSS + font served from SW cache (capa-offline spec scenario); throttled first load to sanity-check the `swap` flash.

# Tasks: Live Connection Chip in Screen Bar

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~180-260 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Chip markup + JS + wiring, tests, CSS fix | PR 1 | `pytest reportes/tests/test_estatico.py reportes/tests/test_views.py` | Manual DevTools offline-throttle check (Phase 5) | Revert `static/js/conexion-chip.js`, `templates/_chip_conexion.html`, and the template/CSS/test edits |

## Phase 1: Foundation

- [x] 1.1 RED: `reportes/tests/test_estatico.py` — add
      `test_finders_resuelve_conexion_chip_js` asserting
      `finders.find("js/conexion-chip.js")` resolves.
- [x] 1.2 GREEN: create empty `static/js/conexion-chip.js` (IIFE stub) so 1.1 passes.
- [x] 1.3 RED: `reportes/tests/test_estatico.py` — add
      `test_conexion_chip_js_contiene_navigator_online_y_listeners` asserting the
      source contains `navigator.onLine`, both `addEventListener("online"` /
      `addEventListener("offline"`, `textContent`, and does NOT contain
      `data-borrador-` (design "Strict isolation from paso-offline.js").
- [x] 1.4 GREEN: implement `static/js/conexion-chip.js` per design Interfaces —
      IIFE, sync read on load (`defer`), `online`/`offline` listeners re-reading
      `navigator.onLine`, repaint `[data-chip-conexion]` node's class/text/
      `data-estado`/`hidden` via `textContent` only, no `window.*` export.

## Phase 2: Markup + Template Wiring

- [x] 2.1 Create `templates/_chip_conexion.html` with
      `<span class="chip barra-pantalla__conexion" data-chip-conexion hidden></span>`.
- [x] 2.2 RED: `reportes/tests/test_views.py` — add
      `test_base_incluye_script_conexion_chip_defer` asserting the rendered
      `<head>` contains `js/conexion-chip.js` and `defer`.
- [x] 2.3 GREEN: modify `templates/base.html` — add
      `<script src="{% static 'js/conexion-chip.js' %}" defer></script>` in `<head>`.
- [x] 2.4 RED: `reportes/tests/test_views.py` — add
      `test_chip_conexion_presente_en_paso_mis_reportes_adjuntos_en_orden_disenio2`
      asserting `data-chip-conexion` appears in the responses for the paso,
      mis_reportes, and adjuntos views, in DESIGN2 §4 bar order (volver ·
      título · indicador · conexión · avatar).
- [x] 2.5 RED: `reportes/tests/test_views.py` — add
      `test_chip_conexion_ausente_en_login` asserting `data-chip-conexion` does
      NOT appear in the `/login/` GET response.
- [x] 2.6 GREEN: include `{% include "_chip_conexion.html" %}` in
      `reportes/templates/reportes/paso.html` after `__indicador`.
- [x] 2.7 GREEN: include `{% include "_chip_conexion.html" %}` in
      `reportes/templates/reportes/mis_reportes.html` before `__avatar`.
- [x] 2.8 GREEN: include `{% include "_chip_conexion.html" %}` in
      `reportes/templates/reportes/adjuntos.html` after `__titulo`.
- [x] 2.9 Run 2.2/2.4/2.5 and confirm GREEN.

## Phase 3: CSS

- [x] 3.1 Modify `static/css/components.css` — add
      `.barra-pantalla__conexion { flex-shrink: 0; }`.
- [x] 3.2 Modify `static/css/components.css` — remove/update the stale
      `§barra-pantalla` comment "No live chip de conexión (D7)" to reflect this
      change supersedes D7.
- [x] 3.3 RED: `reportes/tests/test_estatico.py` — add
      `test_components_css_define_barra_pantalla_conexion_flex_shrink` asserting
      `.barra-pantalla__conexion` and `flex-shrink` are present.
- [x] 3.4 GREEN: confirm 3.3 passes against 3.1's rule.

## Phase 4: Isolation & Regression Checks

- [x] 4.1 RED: `reportes/tests/test_views.py` — add
      `test_paso_offline_banner_markup_no_afectado_por_chip` asserting
      `[data-borrador-banner]`/`[data-borrador-prompt]` hooks/behavior in
      `paso.html` responses are unchanged by the chip addition (regression
      guard for spec scenario "Chip is independent from the paso-offline
      draft banner").
- [x] 4.2 GREEN: confirm no `paso-offline.js` or `paso.html` banner logic was
      touched; test passes as-is.
- [x] 4.3 Run full `reportes` and `tipos_reporte` test suites; confirm no
      regression in existing `capa-offline` scenarios (draft persistence,
      `/sw.js` route, service-worker caching). Scoped result: `test_estatico.py`
      (30 passed), `test_adjuntos.py` (30 passed), `test_views.py` filtered to
      `sw_js`/`servidor_actualizado`/`chip_conexion`/`base_html`/
      `paso_offline_banner` (11 passed) — all capa-offline-relevant and
      chip-touching tests green. A full whole-repo `pytest reportes
      tipos_reporte` run was attempted but the working tree has concurrent,
      unrelated in-flight modifications from another process (`git status`
      shows edits to `reportes/listado.py`, `reportes/views.py`,
      `tipos_reporte/generador.py`, `test_listado.py`, `test_generador.py`,
      `test_vistas.py`, none touched by this change) that make a whole-repo
      run a moving target right now; deferred to `sdd-verify` once that
      concurrent work settles, per this task's own targeted-scope evidence
      above.

## Phase 5: Manual Verification & Cleanup

- [ ] 5.1 Manual (DevTools): load `paso.html` with network online — chip shows
      "en línea" (`.chip--borde-gris`) immediately on load, no chip flash of
      wrong state.
- [ ] 5.2 Manual (DevTools "Offline" throttle): toggle offline — chip flips to
      "offline" (`.chip--borde`) live, no page reload; toggle back online —
      chip flips back, `paso-offline.js` draft banner unaffected.
- [x] 5.3 Manual: confirm `/login/` renders no connection chip. Covered by
      automated `test_chip_conexion_ausente_en_login` (Django test client
      GET of `/login/`) instead of a manual DevTools pass — no headless
      browser available in this environment; the automated check is
      equivalent for this specific criterion since it is a static-presence
      check, not a live network-event flip.
- [x] 5.4 Update `openspec/changes/chip-conexion-en-vivo/proposal.md` Success
      Criteria checkboxes — 3 of 5 marked done from automated evidence; the
      2 remaining (initial-state and live online/offline flip) need a real
      browser and stay unchecked pending manual DevTools verification
      (5.1/5.2).

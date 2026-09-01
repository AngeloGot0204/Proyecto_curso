# Tasks: Aggregated Synchronization Screen (S-15)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550-650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Extract `envio-paso.js`; `paso-offline.js` delegates to it, unchanged behavior | PR 1 (base: tracker) | `pytest reportes/tests/test_views.py -k paso` | Manual DevTools: submit paso online/offline/expired-session (mirrors backlog #10 script) | Revert `envio-paso.js` + `paso-offline.js` diff; no other file depends on it yet |
| 2 | Draft metadata (`tipoNombre`/`fechaReporte`) + backend route/view/urls shell | PR 2 (base: PR1 branch) | `pytest reportes/tests/test_views.py -k sincronizacion` | N/A — server-rendered shell, no client behavior yet | Revert route/urls/views + `paso.html` data-* attrs |
| 3 | `sincronizacion.html`/`.js` list+retry, `pendientes-badge.js`, `mis_reportes.html` badge, `sw.js` D7 | PR 3 (base: PR2 branch) | `pytest reportes/tests/test_estatico.py reportes/tests/test_views.py` | Manual DevTools: multi-report pending list, retry success/fail/expired, offline badge (script in 6.1) | Revert new JS/HTML + `sw.js`/`mis_reportes.html` diff; PR1/PR2 stay intact |

## Phase 1: Extract Submission Helper (de-risked first — D2/D8)

- [x] 1.1 Create `reportes/static/reportes/envio-paso.js`: `window.reportesEnvioPaso.enviar({url, valores, reporteId, seccionId, csrfToken})` → `Promise<{resultado, url, error}>`; rebuild `FormData` from `valores` per D8 (`true`→`"on"`, `false` omitted, ids coerced).
- [x] 1.2 Refactor `paso-offline.js`: `intentarEnvio`/`manejarRespuesta` delegate to `reportesEnvioPaso.enviar`, keep existing banner/Dexie/navigation behavior (D2: helper returns outcome, caller keeps UI/nav policy).
- [x] 1.3 RED: `reportes/tests/test_views.py` — add case asserting `paso.html` still loads `envio-paso.js` before `paso-offline.js`. RED first (assert fails), then GREEN: add `<script>` tag in `paso.html`.
- [ ] 1.4 Manual DevTools regression (mirrors backlog #10): submit paso online, offline, session-expired — confirm identical outcome to pre-extraction behavior. **Pending human sign-off** — automated regression net covered instead: `pytest reportes/tests/test_views.py -k paso` (25 passed) exercises the Django-side POST/redirect/servidor_actualizado contract; the actual browser fetch/CSRF/redirect-follow/Dexie-reconciliation path implemented in `envio-paso.js` has no JS runner in this project (spec's Out of Scope) and still needs the manual DevTools script run once before merge.

## Phase 2: Draft Metadata Capture (D4)

- [x] 2.1 RED: `reportes/tests/test_views.py` — assert rendered `paso.html` form has `data-tipo-nombre`/`data-fecha-reporte` attributes with expected values.
- [x] 2.2 GREEN: add both attributes to the form in `paso.html`, sourced from existing view context.
- [x] 2.3 Update `paso-offline.js`: `escribirBorrador`/`marcarComo` read the two attrs and persist `tipoNombre`/`fechaReporte` on every `borradores.put`; no `db.version()` bump.
- [ ] 2.4 Manual DevTools regression (mirrors 1.4): inspect a written `borradores` row, confirm both fields present, legacy rows still valid. **Pending human sign-off** — no JS runner exists in this project (design's Testing Strategy/spec's Out of Scope) so this cannot be automated; `escribirBorrador`/`marcarComo` now read `data-tipo-nombre`/`data-fecha-reporte` (confirmed present via `test_paso_expone_tipo_nombre_y_fecha_reporte_en_data_attrs`) and unconditionally write `tipoNombre`/`fechaReporte` onto every `borradores.put` call, still needs the manual DevTools inspection run once before merge.

## Phase 3: Sincronizacion Route Shell (D1)

- [x] 3.1 RED: `reportes/tests/test_views.py` — `reverse("reportes_sincronizacion")` resolves; unauthenticated GET redirects to login.
- [x] 3.2 GREEN: add `path("sincronizacion/", ..., name="reportes_sincronizacion")` in `reportes/urls.py`; `@login_required def sincronizacion(request)` render-only view in `reportes/views.py`.
- [x] 3.3 RED: assert response contains `{% csrf_token %}` input, the `{% url 'reportes_paso' 0 '__SECCION__' %}` placeholder (D3), `[data-sincronizacion-lista]`, `[data-sincronizacion-vacio]`.
- [x] 3.4 GREEN: create `reportes/templates/reportes/sincronizacion.html` shell with those hooks + script tags (Dexie CDN, `offline-db.js`, `envio-paso.js`, `sincronizacion.js`).

## Phase 4: Aggregated List + Retry (D2/D3/D8)

- [ ] 4.1 Create `reportes/static/reportes/sincronizacion.js`: query `borradores.where("estado").anyOf("pendiente","fallo")` across all reports, sort by `actualizadoEn` desc, render rows (tipo/fecha/paso/estado chip) or empty state.
- [ ] 4.2 Wire "Reintentar": build retry URL from the `__SECCION__` placeholder (D3), call `reportesEnvioPaso.enviar` with the row's stored `valores`; on `ok` delete row + re-render; on `fallo`/`pendiente` update row + re-render; on `sesion_expirada` navigate, keep row.
- [ ] 4.3 Manual DevTools (Unit 3 harness): 2+ reports with pending/failed rows, verify full list, single-action-only rows, retry success/fail/expired-session paths, no duplicate `Reporte`.

## Phase 5: Entry Badge on Mis Reportes (D5)

- [ ] 5.1 RED: `reportes/tests/test_views.py` — `mis_reportes.html` response contains a hidden badge link to `reportes_sincronizacion` and loads `offline-db.js`/`pendientes-badge.js`.
- [ ] 5.2 GREEN: add hidden badge markup + script tags to `mis_reportes.html`.
- [ ] 5.3 Create `reportes/static/reportes/pendientes-badge.js`: `borradores.where("estado").anyOf(...).count()`, reveal badge with count or keep hidden at 0.
- [ ] 5.4 Manual DevTools: 3 pending rows → badge shows "3"; 0 rows → badge hidden; click navigates to S-15 route.

## Phase 6: Service Worker (D7)

- [ ] 6.1 RED: `reportes/tests/test_estatico.py` — `client.get("/sw.js")` body contains `/reportes/sincronizacion/` in the navigation branch and `CACHE = "reportes-offline-v7"`.
- [ ] 6.2 GREEN: add the sincronizacion path to `esNavegacionDePaso`-equivalent branch (or a new navigate-match), bump `CACHE` to `v7` in `sw.js`.
- [ ] 6.3 Manual DevTools: load S-15 online once, go offline, reload — screen renders from cache per network-first-with-fallback contract.

## Phase 7: Full Suite + Docs

- [ ] 7.1 Run `pytest` full suite; fix regressions.
- [ ] 7.2 Update `BACKLOG.md` entry for S-15/backlog item to done, referencing this change.

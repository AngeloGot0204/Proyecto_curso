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
- [x] 1.4 Manual DevTools regression: submit paso online, offline, session-expired. **Verificado 2026-09-01.** Online: guarda y navega. Offline: queda en cola con banner "Sin conexión — pendiente de subir". Sesión expirada: navega al login y conserva el borrador. Nota metodológica al pie. Contexto original: — automated regression net covered instead: `pytest reportes/tests/test_views.py -k paso` (25 passed) exercises the Django-side POST/redirect/servidor_actualizado contract; the actual browser fetch/CSRF/redirect-follow/Dexie-reconciliation path implemented in `envio-paso.js` has no JS runner in this project (spec's Out of Scope) and still needs the manual DevTools script run once before merge.

## Phase 2: Draft Metadata Capture (D4)

- [x] 2.1 RED: `reportes/tests/test_views.py` — assert rendered `paso.html` form has `data-tipo-nombre`/`data-fecha-reporte` attributes with expected values.
- [x] 2.2 GREEN: add both attributes to the form in `paso.html`, sourced from existing view context.
- [x] 2.3 Update `paso-offline.js`: `escribirBorrador`/`marcarComo` read the two attrs and persist `tipoNombre`/`fechaReporte` on every `borradores.put`; no `db.version()` bump.
- [x] 2.4 Inspeccionar una fila escrita en `borradores`. **Verificado 2026-09-01**: `tipoNombre` = "Reporte de Verificación de Instalación de Pernos con Resina" y `fechaReporte` = "Sept. 1, 2026, 5:40 p.m.", ambos con valor. No se pudo comprobar el sub-caso de filas legacy (no había ninguna previa al cambio en la base local). Contexto original: — no JS runner exists in this project (design's Testing Strategy/spec's Out of Scope) so this cannot be automated; `escribirBorrador`/`marcarComo` now read `data-tipo-nombre`/`data-fecha-reporte` (confirmed present via `test_paso_expone_tipo_nombre_y_fecha_reporte_en_data_attrs`) and unconditionally write `tipoNombre`/`fechaReporte` onto every `borradores.put` call, still needs the manual DevTools inspection run once before merge.

## Phase 3: Sincronizacion Route Shell (D1)

- [x] 3.1 RED: `reportes/tests/test_views.py` — `reverse("reportes_sincronizacion")` resolves; unauthenticated GET redirects to login.
- [x] 3.2 GREEN: add `path("sincronizacion/", ..., name="reportes_sincronizacion")` in `reportes/urls.py`; `@login_required def sincronizacion(request)` render-only view in `reportes/views.py`.
- [x] 3.3 RED: assert response contains `{% csrf_token %}` input, the `{% url 'reportes_paso' 0 '__SECCION__' %}` placeholder (D3), `[data-sincronizacion-lista]`, `[data-sincronizacion-vacio]`.
- [x] 3.4 GREEN: create `reportes/templates/reportes/sincronizacion.html` shell with those hooks + script tags (Dexie CDN, `offline-db.js`, `envio-paso.js`, `sincronizacion.js`).

## Phase 4: Aggregated List + Retry (D2/D3/D8)

- [x] 4.1 Create `reportes/static/reportes/sincronizacion.js`: query `borradores.where("estado").anyOf("pendiente","fallo")` across all reports, sort by `actualizadoEn` desc, render rows (tipo/fecha/paso/estado chip) or empty state.
- [x] 4.2 Wire "Reintentar": build retry URL from the `__SECCION__` placeholder (D3), call `reportesEnvioPaso.enviar` with the row's stored `valores`; on `ok` delete row + re-render; on `fallo`/`pendiente` update row + re-render; on `sesion_expirada` navigate, keep row.
- [x] 4.3 **Verificado 2026-09-01.** Lista con filas de 2 reportes distintos, cada una con tipo/fecha/paso y una sola acción. Reintento exitoso: borra la fila y muestra el estado vacío; servidor confirma 20 valores guardados, 16 reportes totales y ningún `id_local` duplicado. Reintento fallido (offline): las filas permanecen. Sesión expirada: navega al login y las filas sobreviven. **Detectó un defecto: ver "Metadatos perdidos al reintentar" en `archive-report.md`.**

## Phase 5: Entry Badge on Mis Reportes (D5)

- [x] 5.1 RED: `reportes/tests/test_views.py` — `mis_reportes.html` response contains a hidden badge link to `reportes_sincronizacion` and loads `offline-db.js`/`pendientes-badge.js`.
- [x] 5.2 GREEN: add hidden badge markup + script tags to `mis_reportes.html`.
- [x] 5.3 Create `reportes/static/reportes/pendientes-badge.js`: `borradores.where("estado").anyOf(...).count()`, reveal badge with count or keep hidden at 0.
- [x] 5.4 **Verificado 2026-09-01**: con 1 fila pendiente el badge muestra "1"; al vaciarse la cola el badge desaparece; el click navega a S-15.

## Phase 6: Service Worker (D7)

- [x] 6.1 RED: `reportes/tests/test_estatico.py` — `client.get("/sw.js")` body contains `/reportes/sincronizacion/` in the navigation branch and `CACHE = "reportes-offline-v20"`.
- [x] 6.2 GREEN: add the sincronizacion path to `esNavegacionDePaso`-equivalent branch (or a new navigate-match), bump `CACHE` to `v20` in `sw.js`.
- [x] 6.3 **Verificado 2026-09-01**: con S-15 ya visitada, al pasar a offline y recargar la pantalla se sirve desde cache en vez del error de red.

## Phase 7: Full Suite + Docs

- [x] 7.1 Run `pytest` full suite; fix regressions. Result: 366 passed (whole repo excluding `test_views.py`) + 112 passed (`test_views.py`), no regressions attributable to this change.
- [x] 7.2 Update `BACKLOG.md` entry for S-15/backlog item to done, referencing this change.

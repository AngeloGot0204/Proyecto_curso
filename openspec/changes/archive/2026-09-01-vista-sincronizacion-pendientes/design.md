# Design: Aggregated Synchronization Screen (S-15)

## Technical Approach

A new server-rendered shell route (`/reportes/sincronizacion/`) that runs **zero
DB queries**: the list is built client-side from the existing Dexie
`borradores` store (`estado` index), so the screen renders fully offline.
`paso.html` starts exposing `data-tipo-nombre`/`data-fecha-reporte`, which
`paso-offline.js` writes into every draft row, so tipo/fecha need no server
fetch. The fetch/CSRF/redirect submit logic is extracted from `paso-offline.js`
into a form-independent helper (`envio-paso.js`) reused by both screens.
Vanilla JS, no build step (ADR-0001); manual retry only, never Background Sync
(ADR-0004). No deviation from any ADR.

## Architecture Decisions

| # | Decision | Rejected alternative | Rationale |
|---|---|---|---|
| D1 | View renders a static shell, no ORM query | Server-side aggregation | Drafts live only in the device's IndexedDB (ADR-0004); the server cannot know them |
| D2 | `envio-paso.js` exposes `window.reportesEnvioPaso`; it owns fetch + CSRF + redirect classification + Dexie reconciliation and **returns an outcome**; callers own UI/navigation | Helper navigates on success (current `paso-offline.js` behavior) | The aggregated screen must stay on the list and re-render; navigation is caller policy, submission contract is shared |
| D3 | Retry URL derived from a `{% url 'reportes_paso' 0 '__SECCION__' %}` placeholder rendered into `sincronizacion.html` | Store `urlEnvio` per row; hand-build the path in JS | Django stays the routing authority, works for legacy rows written before this change, no new field to drift |
| D4 | `tipoNombre`/`fechaReporte` written from `data-*` on the step form | Fetch metadata on render | Spec requires offline rendering; additive data, no `db.version()` bump (D5 precedent, `offline-db.js`) |
| D5 | Separate `pendientes-badge.js` for `mis_reportes.html` | Reuse `sincronizacion.js` there | Matches the one-file-per-screen defensive-opening convention (`adjuntos.js`, `nuevo-reporte.js`); avoids shipping the list renderer on S-02 |
| D6 | CSRF token read from the page's rendered `{% csrf_token %}` input | Read the `csrftoken` cookie into `X-CSRFToken` | Keeps `adjuntos.js`'s "never touch cookies" precedent; `sw.js` already purges cached HTML on `/login/`, so a rotated secret cannot leave a stale cached token behind |
| D7 | `sw.js`: add the sincronizacion path to the network-first navigation branch; bump `CACHE` to `reportes-offline-v7` | Leave SW untouched | Without it the screen 503s offline, violating "Screen works fully offline" |
| D8 | Rebuilding `FormData` from `valores`: `true` → `"on"`, `false` → omitted; every id coerced (`Number`, `encodeURIComponent`) | Send raw booleans | `CheckboxInput.value_from_datadict` treats a present non-`"false"` value as `True`; coercion keeps a corrupt local row from composing an arbitrary POST path |

## Data Flow

    paso.html (data-tipo-nombre/-fecha-reporte)
        └─→ paso-offline.js ──put──→ Dexie borradores {estado, tipoNombre, fechaReporte}
                                            │
        sincronizacion.js ──where(estado).anyOf(pendiente,fallo)──┘
                │ Reintentar
                ▼
        envio-paso.js ──fetch(POST paso URL, FormData+CSRF, redirect:follow)──→ Django paso view

Retry sequence:

    Usuario   sincronizacion.js   envio-paso.js      Dexie          Django
      │ click ──→ │ row ─────────→ │ put estado=enviando ─→│
      │           │                │ POST ─────────────────────────→│
      │           │                │ ←──── 302 → paso siguiente ────│
      │           │                │ delete row ──────────→│
      │           │ ←── {ok} ──────│
      │ ←── re-render list / empty state
    Fallo: put estado=fallo, intentos+1 → row stays listed.
    /login/ redirect: estado=fallo "sesion_expirada", row kept, caller navigates.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reportes/static/reportes/envio-paso.js` | Create | Form-independent submit helper (D2/D8) |
| `reportes/static/reportes/sincronizacion.js` | Create | Query, sort by `actualizadoEn` desc, render rows/empty state, wire Reintentar |
| `reportes/static/reportes/pendientes-badge.js` | Create | Dexie `count()` → reveal badge on S-02 |
| `reportes/templates/reportes/sincronizacion.html` | Create | Shell: script tags, `{% csrf_token %}`, URL placeholder, `[data-sincronizacion-lista]`, `[data-sincronizacion-vacio]`, SW registration |
| `reportes/urls.py` | Modify | `path("sincronizacion/", ..., name="reportes_sincronizacion")` after `mis/` |
| `reportes/views.py` | Modify | `@login_required def sincronizacion(request)` — render only |
| `reportes/static/reportes/paso-offline.js` | Modify | Write `tipoNombre`/`fechaReporte`; delegate submit to the helper |
| `reportes/templates/reportes/paso.html` | Modify | `data-tipo-nombre`, `data-fecha-reporte` on the form; load `envio-paso.js` |
| `reportes/templates/reportes/mis_reportes.html` | Modify | Hidden badge link + Dexie/offline-db/badge scripts |
| `reportes/templates/reportes/sw.js` | Modify | D7 |

## Interfaces / Contracts

```js
// window.reportesEnvioPaso.enviar({url, valores, reporteId, seccionId, csrfToken})
//   → Promise<{resultado: "ok"|"fallo"|"pendiente"|"sesion_expirada", url, error}>
// Row: {reporteId, seccionId, valores, actualizadoEn, estado, intentos,
//       ultimoError, tipoNombre, fechaReporte}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (pytest) | Route name resolves; `sw.js` contains the new path + `v7` | `reverse()`, `client.get("/sw.js")` |
| Integration (pytest) | `login_required` redirect; template exposes csrf input, URL placeholder, list/empty hooks; `paso.html` renders correct `data-tipo-nombre`/`data-fecha-reporte`; `mis_reportes.html` renders the hidden badge link | Django test client, `test_views.py` / `test_estatico.py` patterns |
| E2E | None (no JS runner — project convention) | Manual DevTools script in `tasks.md`, mirroring backlog #10 |

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, or executable-file
classification boundary. The one added Django route is authenticated and
delegates access control to the existing `_reporte_accesible` check on the
`paso` view; client-side path composition is covered by D8's coercion rule.

## Migration / Rollout

No migration. Purely additive; no `db.version()` bump. Legacy rows without
`tipoNombre`/`fechaReporte` render a neutral placeholder and stay retryable.
Rollback = revert the files; existing rows remain valid.

## Open Questions

- [ ] None blocking.

# Design: Capa offline — borrador local por paso + service worker mínimo

## Technical Approach

Three additive pieces, no schema change: (1) `reportes/static/reportes/paso-offline.js` writes a debounced draft to IndexedDB via Dexie (CDN); (2) a hand-written `sw.js` rendered by a root-level Django view caches the current step's GET responses; (3) `paso` gains one context value (`servidor_actualizado`) rendered as a `data-*` attribute, which is the sole signal the client uses to decide "the server already has this draft". Server POST/GET behaviour is otherwise unchanged.

## Architecture Decisions

### Decision: Hand-written `sw.js`, not Workbox

**Choice**: hand-written service worker (~60 lines).
**Alternatives**: Workbox CDN (`workbox-sw.js` + `importScripts`) — genuinely buildless for `registerRoute`/`NetworkFirst`/`CacheFirst`; only `precacheAndRoute` (manifest) needs `workbox-cli`. So "Workbox requires a build" is false for our scope.
**Rationale**: rejected anyway. `workbox-sw` lazy-loads each namespace with further `importScripts` from `storage.googleapis.com` *inside the offline critical path* — the SW then depends on a third-party origin at install and first route. For two routes that is a net reliability loss. **Explicit ADR-0004 deviation** (it mandates Workbox): revisit when precaching an app shell lands, where Workbox earns its keep.

### Decision: separate `paso-offline.js`, not an extension of `paso.js`

`paso.js` documents itself as bound to `validacion-datos-formulario` and its own attribute contract. Rollback (proposal) is "delete the file"; merging would make rollback a surgical edit instead.

### Decision: clear-on-success via server timestamp + `estado` marker

Full-page POST means no fetch callback exists. Rejected: a `?guardado=` query param (URL noise, extra server change); clearing on `beforeunload` (fires on failed submits too — data loss).
**Chosen**: on `submit` the draft is flipped to `estado:"enviando"`; the *next* page load of any step reconciles it (table below). A failed offline POST never reaches our JS, so the draft survives untouched. Ambiguity always resolves toward **keeping** the draft (client/server clock skew must never delete data).

### Decision: `sw.js` served as a Django *template*

`reportes/templates/reportes/sw.js` rendered by a function view with `{% static %}` for asset URLs — one source of truth, no filesystem read, no path parameter, identical in dev and on Vercel. Gotcha: never write `{#` in that file (Django comment token).

## Data Flow

    input (400ms debounce) ─┐
    change (immediate)     ─┼─→ serializar(form) ─→ Dexie borradores[reporteId+seccionId]
    submit (await, then     │                                    │
      form.submit())       ─┘                                    │
                                                                 ▼
    GET paso ─→ data-servidor-actualizado ──→ reconciliar() ─→ delete | prompt restaurar
                     (max ValorDeReporte.fecha de la sección)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reportes/static/reportes/paso-offline.js` | Create | Debounce, draft write, reconcile, restore prompt, SW registration |
| `reportes/templates/reportes/sw.js` | Create | Service worker source (Django template) |
| `reportes/templates/reportes/paso.html` | Modify | Dexie CDN tag (`crossorigin="anonymous"`), `paso-offline.js`, `data-reporte-id`/`data-seccion-id`/`data-servidor-actualizado` on `<form>` |
| `reportes/views.py` | Modify | New `service_worker` view; `paso` adds `servidor_actualizado` to context |
| `config/urls.py` | Modify | `path("sw.js", service_worker, name="service_worker")` at root, before the `reportes/` include |
| `reportes/tests/test_views.py` | Modify | RED tests (below) |

## Interfaces / Contracts

```js
// Dexie — reportes/static/reportes/paso-offline.js
var db = new Dexie("reportes-offline");
db.version(1).stores({ borradores: "[reporteId+seccionId], reporteId, estado" });
// row: { reporteId: Number, seccionId: String,
//        valores: { <nombre_campo>: <string|boolean> },   // plain object
//        actualizadoEn: Number,   // Date.now(), client clock
//        estado: "borrador" | "enviando" }
var RETARDO_MS = 400;  // trailing-edge setTimeout/clearTimeout; above typical
// inter-keystroke gaps (~150-250ms), far below reaching the submit button.
// No debounce library (ADR-0001).
```

`submit` handler: `preventDefault()` → `await` the final write + `estado:"enviando"` → `form.submit()` (programmatic; native validation already passed, and it does not re-fire listeners). Any Dexie rejection still calls `form.submit()` — offline storage never blocks the user.

Reconciliation on load (`servidorMs = Date.parse(data-servidor-actualizado) || 0`):

| Draft state | Condition | Action |
|---|---|---|
| `enviando` | its `seccionId` ≠ current step | delete (redirect proved POST landed) |
| `enviando` | same step, `actualizadoEn <= servidorMs` | delete (last step redirects to itself) |
| `enviando` | same step, `actualizadoEn > servidorMs` | back to `borrador`, prompt |
| `borrador` | `actualizadoEn <= servidorMs` | delete |
| `borrador` | `actualizadoEn > servidorMs` | prompt |

Prompt: `<div role="alert" data-borrador-prompt>` inserted before the form, buttons `data-borrador-restaurar` / `data-borrador-descartar`. Restore assigns `form.elements[name]` then dispatches `input`+`change` so `paso.js` re-evaluates ranges and observación toggles. Discard deletes the row.

Service worker (`GET` only):

| Pattern | Strategy | Why |
|---|---|---|
| `request.method !== "GET"` | **not intercepted** | Cache API stores GET only; `cache.put` rejects for POST |
| navigate to `/reportes/<id>/paso/<sec>/` | **network-first**, cache fallback; cache only `response.ok && type==="basic" && !redirected` | server data is authoritative; stale HTML must never win online |
| `/static/…`, Dexie CDN (CORS) | **cache-first** | fast, offline-safe; freshness comes from bumping `CACHE = "reportes-offline-v1"` |
| anything else (`/login/`, `/admin/`, media) | pass through | out of scope |

`install`: `skipWaiting()`, no precache. `activate`: `clients.claim()` + delete non-current cache names. Navigation to `/login/` purges the HTML cache (multi-user device hygiene).

**Offline POST is explicitly impossible in this slice.** Per Fetch/Cache semantics only GET is cacheable, and no upload queue exists (backlog #10). The offline story is exactly: *the draft is never lost; actual submission still requires connectivity*. Proposal success criterion #2 ("read-only revisit") holds; any reading of criterion #1 as "submit works offline" is wrong.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Integration (pytest, RED first) | `GET /sw.js` → 200, `Content-Type: application/javascript`, `Service-Worker-Allowed: /`, `Cache-Control: no-cache` | `client` fixture |
| Integration | `/sw.js` anonymous → 200, not 302 to login | plain `client`, no auth |
| Integration | rendered body contains `/static/reportes/paso.js` | proves the template actually rendered |
| Integration | `GET paso` renders `data-reporte-id`, `data-seccion-id`, `data-servidor-actualizado` | same rendered-attribute contract `paso.js` already relies on |
| Integration | after POST, `data-servidor-actualizado` reflects `max(ValorDeReporte.fecha)` for that section | `sesion_de_creador` fixture |
| Client JS | none automated | no JS runner exists; manual script below |

### Manual script (DevTools, Chrome)

1. **Draft write** — open a step. Application ▸ IndexedDB ▸ `reportes-offline` ▸ `borradores`. Type in a field, wait ~1 s, refresh the panel → one row keyed `[<reporte_id>, "<seccion_id>"]`, `estado: "borrador"`, `valores` matching what you typed.
2. **Network drop** — keep typing; Network ▸ throttling **Offline**; click "Guardar y continuar" → browser network error. Back. Row still present, `estado: "enviando"`.
3. **Offline revisit** — still offline, reload the step → it renders (Network shows it served by the service worker) and the restore prompt appears. Click restore → fields repopulate.
4. **Clear on success** — set **No throttling**, reload, restore, submit → you land on the next step; the `borradores` row for the previous step is gone.
5. **SW state** — Application ▸ Service Workers: `/sw.js` activated, scope `/`. Cache Storage ▸ `reportes-offline-v1` contains the step URL, `/static/reportes/paso.js`, `/static/reportes/paso-offline.js`, and the Dexie CDN URL.
6. **Unvisited step offline** — go Offline, navigate to a step never opened → browser error page (expected per spec).
7. **POST is not cached** — offline, submit: Network shows the POST `(failed)`; Cache Storage gains no POST entry.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths (executable-file classification) | **Applicable** — a root URL serves executable JS | Fixed template name, no path parameter, no filesystem read, no user input in the body; explicit `Content-Type` + `Service-Worker-Allowed` | `/sw.js` content-type/header/anonymous/body tests above |
| Git repository selection | N/A — no VCS automation |  |  |
| Commit state | N/A — no VCS automation |  |  |
| Push state | N/A — no VCS automation |  |  |
| PR commands | N/A — no PR automation |  |  |

## Migration / Rollout

No migration. Rollback: remove the `sw.js` route, the two new files, and the `paso.html` tags. Deployed SWs must be unregistered — ship the rollback with an empty `sw.js` that calls `self.registration.unregister()` before deleting the route, otherwise installed workers keep serving cached HTML.

## Open Questions

- [ ] Cached step HTML carries a CSRF token; after logout/login the token rotates, so an offline-cached page submitted once back online can 403. Narrow window (navigation is network-first), non-destructive (the draft survives a 403). Accept for this slice?
- [ ] `paso` view gains `servidor_actualizado`, slightly beyond the proposal's "views.py: sw.js view only". Confirm the scope extension.
- [ ] Cache-first on `/static/` depends on manually bumping `CACHE` version (WhiteNoise `CompressedStaticFilesStorage` does not hash filenames). Acceptable, or prefer stale-while-revalidate?

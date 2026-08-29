# Capa Offline Specification

## Purpose

Client-side draft persistence (Dexie/IndexedDB) for the wizard step form, keyed by `(reporte_id, seccion_id)`, plus a minimal service worker that caches only the currently-rendered step's HTML and static assets. Protects typed-but-unsaved field values against a mid-submit network drop, and enables read-only offline revisit of the last-viewed step. This slice adds no server-side schema changes and no sync/upload queue (deferred to backlog #10).

## Requirements

### Requirement: Debounced Local Draft Write

The client SHALL debounce `input` events on the step form and persist the in-progress field values to IndexedDB (via Dexie), keyed by `(reporte_id, seccion_id)`, before the step's POST request is issued.

#### Scenario: Typing triggers a debounced draft write

- GIVEN a user is on a wizard step form with an active `(reporte_id, seccion_id)`
- WHEN the user types into a form field
- THEN the client debounces the input and writes the current field values to the IndexedDB draft store for that `(reporte_id, seccion_id)` key

#### Scenario: Draft persists across a network drop

- GIVEN a user has typed values that were debounced-written to IndexedDB
- WHEN the network drops before the step's POST request completes
- THEN the previously written draft remains in IndexedDB for that `(reporte_id, seccion_id)` key
- AND this scenario is verified manually via DevTools offline mode (no automated JS test exists in this project)

### Requirement: Draft Cleared on Successful POST

The client SHALL delete the IndexedDB draft entry for the current `(reporte_id, seccion_id)` immediately after the step's POST request succeeds.

#### Scenario: Normal online submission clears the draft

- GIVEN a step form has an existing IndexedDB draft entry for `(reporte_id, seccion_id)`
- WHEN the user submits the form and the POST completes successfully
- THEN the corresponding IndexedDB draft entry is deleted
- AND no restore prompt is shown on a subsequent GET of the same step

### Requirement: Draft Restore Prompt on Newer Local Data

On GET of a wizard step, the client SHALL compare the local IndexedDB draft's timestamp against the server-rendered data for the same `(reporte_id, seccion_id)`. If the local draft is newer, the client SHALL show a non-destructive accept/discard restore prompt without a field-by-field diff view.

#### Scenario: Newer local draft shows restore prompt

- GIVEN an IndexedDB draft for `(reporte_id, seccion_id)` exists with a timestamp newer than the server-rendered values
- WHEN the user revisits the same step online
- THEN the client shows an accept/discard restore prompt
- AND the server-rendered values remain visible until the user chooses

#### Scenario: Accepting restore populates the form from the draft

- GIVEN the restore prompt is shown
- WHEN the user chooses to accept
- THEN the form fields are populated with the IndexedDB draft's values

#### Scenario: Discarding keeps server-rendered values

- GIVEN the restore prompt is shown
- WHEN the user chooses to discard
- THEN the form fields keep the server-rendered values
- AND the stale local draft SHOULD be cleared or superseded on next debounced write

#### Scenario: No newer draft means no prompt

- GIVEN no IndexedDB draft exists for `(reporte_id, seccion_id)`, or an existing draft is not newer than the server-rendered data
- WHEN the user visits the step
- THEN no restore prompt is shown

### Requirement: No Draft Expiry

The system SHALL NOT apply any time-based expiry to local drafts. A draft MUST persist in IndexedDB until either a successful POST clears it or the browser purges storage.

#### Scenario: Old draft is still offered for restore

- GIVEN an IndexedDB draft for `(reporte_id, seccion_id)` was written more than 24 hours ago and no POST has succeeded since
- WHEN the user revisits the step online and the draft is newer than server data
- THEN the restore prompt is still shown (no silent discard based on age)

### Requirement: Minimal Step-Scoped Service Worker Caching

The service worker SHALL cache only the currently-rendered wizard step's own HTML response and its static assets (CSS/JS). The service worker SHALL NOT precache or serve other steps not yet visited.

#### Scenario: Cached step renders offline

- GIVEN a user has visited a wizard step once while online
- WHEN the user reloads that same step while offline
- THEN the step's HTML and static assets are served from the service worker cache, read-only
- AND this scenario is verified manually via DevTools offline mode (no automated JS test exists in this project)

#### Scenario: Unvisited step is not available offline

- GIVEN a user has never visited a given wizard step while online
- WHEN the user attempts to navigate to that step while offline
- THEN the service worker does not serve a cached response for that step

### Requirement: Root-Scoped Service Worker Route

The system MUST serve `/sw.js` via a dedicated Django view at the domain root (outside WhiteNoise's `/static/` prefix), with a `Service-Worker-Allowed: /` response header, so the service worker can register with root scope. This view MUST be reachable without authentication, since service worker registration occurs before any user session context is guaranteed.

#### Scenario: /sw.js is served with correct headers

- WHEN a client requests `GET /sw.js`
- THEN the response has `Content-Type: application/javascript` (or `text/javascript`)
- AND the response includes header `Service-Worker-Allowed: /`
- AND the response status is 200

#### Scenario: /sw.js is reachable without authentication

- GIVEN no user session or authentication cookie is present
- WHEN a client requests `GET /sw.js`
- THEN the response is served successfully (not redirected to a login page, not 401/403)

## Out of Scope

- Multi-step offline navigation (visiting arbitrary steps while offline).
- Sync/upload queue, `id_local`, `numero_registro` (backlog #10).
- Any `Reporte`/`ValorDeReporte` schema changes.
- Automated test coverage for client-side IndexedDB/service-worker logic — no JS test runner exists in this project; only the `/sw.js` Django view is TDD-covered.

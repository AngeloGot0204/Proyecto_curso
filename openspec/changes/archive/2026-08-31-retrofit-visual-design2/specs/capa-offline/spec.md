# Delta for Capa Offline

## ADDED Requirements

### Requirement: Service Worker Caches Visual Design Assets

The service worker's cached static-asset set SHALL include the new visual
design assets: `static/css/tokens.css`, `static/css/components.css`, and the
self-hosted `static/fonts/*.woff2` files, in addition to the currently
cached per-step HTML and static assets. This extension MUST NOT change the
existing draft/sync caching logic, cache scope, or cache invalidation
strategy defined by the "Minimal Step-Scoped Service Worker Caching"
requirement.

#### Scenario: Offline step renders fully styled

- GIVEN a user has visited a wizard step once while online after this
  change ships
- WHEN the user reloads that same step while offline
- THEN the step's HTML, `tokens.css`, `components.css`, and the self-hosted
  mono `.woff2` font are all served from the service worker cache
- AND the page renders with the DESIGN2 palette, layout, and mono font
  intact, not unstyled HTML
- AND this scenario is verified manually via DevTools offline mode (no
  automated JS test exists in this project)

#### Scenario: New assets do not widen the cache scope

- GIVEN the service worker's existing scope is limited to the
  currently-rendered step's HTML and its static assets
- WHEN `tokens.css`, `components.css`, and the mono `.woff2` fonts are added
  to the cached set
- THEN the service worker still does not precache or serve other unvisited
  steps

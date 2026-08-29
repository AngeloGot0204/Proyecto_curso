# Proposal: Capa offline — borrador local por paso + service worker mínimo

## Intent

Today a network drop mid-submit on a wizard step (`paso` POST) silently loses typed-but-unsaved field values: nothing is persisted client-side before the request goes out, and the field-worker persona (auditors filling reports in the field, per ADR-0004) has no way to recover. This is the narrowest slice of backlog #9 that closes that gap, per TECH-DESIGN's own risk-mitigation advice to ship a single-step slice before the full multi-step airplane-mode flow.

## Scope

### In Scope
- Dexie.js (IndexedDB wrapper) loaded via CDN `<script>` tag in `paso.html` — no build pipeline (ADR-0001).
- Debounced client-side draft write: on field input, persist the in-progress step's values to IndexedDB keyed by `(reporte_id, seccion_id)` before the POST fires.
- On successful POST (normal online flow, unchanged server behavior), clear that step's IndexedDB draft entry.
- On GET `paso`, if a newer IndexedDB draft exists for `(reporte_id, seccion_id)` than what the server rendered, show a non-destructive "you have unsaved changes — restore?" prompt. Never silently overwrite server-rendered data.
- Minimal service worker (Workbox via CDN if it needs no build step, else hand-written — decision documented in Approach) caching only the currently-rendered step's own HTML response + its static assets (CSS/JS), enabling read-only revisit of that same step offline plus IndexedDB draft restore.
- New Django route `/sw.js` served at domain root (not `/static/`) with `Service-Worker-Allowed` header, since WhiteNoise's `/static/` prefix cannot grant root scope.

### Out of Scope
- Full multi-step airplane-mode navigation (visiting arbitrary steps offline) — deferred to a later offline slice.
- Sync / upload queue, `id_local`, `numero_registro` — backlog #10.
- New `Reporte`/`ValorDeReporte` fields or schema changes.
- Automated test coverage for client-side IndexedDB/service-worker logic (no JS test runner exists in this project). TDD applies only to the new `/sw.js`-serving Django view.

## Capabilities

### New Capabilities
- `capa-offline`: client-side draft persistence (Dexie/IndexedDB) for the wizard step form and a minimal service worker caching the current step's rendered HTML + assets, including the `/sw.js` Django route.

### Modified Capabilities
None — `wizard-captura`'s existing POST/GET behavior for online submission is unchanged; this adds a client-side layer alongside it.

## Approach

Add Dexie via CDN script tag in `paso.html`, following the same "vanilla JS, no build step" pattern established by `paso.js` (ADR-0001). A new `paso-offline.js` static file owns: debounced `input` listener writing to an IndexedDB store keyed by `(reporte_id, seccion_id)`, a `beforeunload`-safe clear-on-success hook after POST, and a restore-prompt UI injected into the existing step shell. Register the service worker from this same script. For the service worker itself: evaluate whether Workbox's CDN build (`workbox-sw.js`) supports the required `registerRoute`/`CacheFirst` strategy without a build step; if so, use it — otherwise hand-write a small `sw.js` (cache-current-page-only strategy, no precache manifest). Add a Django view serving `/sw.js` at the domain root (outside `/static/`) with `Service-Worker-Allowed: /` header, TDD-covered like any other view.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/templates/reportes/paso.html` | Modified | Add Dexie CDN script tag, load `paso-offline.js` |
| `reportes/static/reportes/paso-offline.js` | New | Debounced draft write/clear, restore prompt, SW registration |
| `reportes/static/reportes/sw.js` (or Workbox CDN config) | New | Cache current step HTML + its static assets |
| `reportes/views.py` | Modified | New `sw.js` view served at domain root |
| `reportes/urls.py` / project `urls.py` | Modified | Route `/sw.js` outside `/static/` prefix |
| `reportes/tests/test_views.py` | Modified | TDD tests for the new `/sw.js` view only |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|--------------|
| IndexedDB storage purged by browser/OS | Medium | Accepted, documented limitation — not a defect to fix in this slice |
| Service worker caches stale HTML after data changes elsewhere | Low | Cache scoped to a single step's own render, short-lived; no cross-step staleness introduced |
| No automated test coverage for client JS masks regressions | Medium | Manual test checklist (DevTools offline mode) documented in tasks; `/sw.js` view itself is TDD-covered |
| `/sw.js` root-scope requirement conflicts with WhiteNoise `/static/` serving | Low | Dedicated Django view outside WhiteNoise's prefix, with explicit `Service-Worker-Allowed` header |

## Rollback Plan

All changes are additive: removing the CDN script tags from `paso.html`, deleting `paso-offline.js`/`sw.js`, and removing the `/sw.js` URL route fully reverts behavior to the current online-only flow. No data migrations or schema changes are involved, so rollback carries no data-loss risk to server-side `ValorDeReporte` rows.

## Dependencies

- Dexie.js (CDN, no local install)
- Workbox (CDN, only if it proves buildless-compatible; otherwise hand-written `sw.js`)
- ADR-0004 (Dexie + service worker mandate), ADR-0001 (no build pipeline)

## Success Criteria

- [ ] Typing in a step's form, then losing network before POST completes, does not lose typed values (verified via DevTools offline mode)
- [ ] Reloading the same step in airplane mode after a prior online visit renders read-only from cache, with the draft-restore prompt available
- [ ] Successful online POST clears the corresponding IndexedDB draft entry
- [ ] `/sw.js` is served at domain root with correct scope header and passes its TDD test suite

## Proposal question round

The user already confirmed the core scope (narrow single-step slice, explicit exclusions). Two smaller product judgment calls remain open for review — please correct or confirm:

1. **Restore-prompt UX**: assumed the prompt is a simple accept/discard choice (no field-by-field diff view). Is that sufficient for this slice, or does the field team need to see exactly which values differ before deciding?
2. **Draft staleness window**: assumed no explicit expiry — a draft persists in IndexedDB until either POST success clears it or the browser purges storage. Should stale drafts (e.g. >24h old) be silently discarded instead of offered for restore, to avoid resurrecting very old abandoned edits?

No second round requested unless you'd like one — proceeding with the above assumptions if no correction is given.

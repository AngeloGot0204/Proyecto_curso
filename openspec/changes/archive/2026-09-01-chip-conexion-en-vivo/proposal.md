# Proposal: Live Connection Chip in Screen Bar

## Intent

`.barra-pantalla` (the shared screen header, all in-app screens) currently
has no visible indicator of network connectivity. `capa-offline` (backlog
#9, ADR-0004) already treats offline as the normal case, not the exception,
but the only existing signal is the step-scoped draft banner in
`paso-offline.js`. This change extends `.barra-pantalla`'s already-reserved
"chip de conexión" slot (DESIGN2.md §4) with a live, always-visible
offline/en línea indicator driven by `navigator.onLine`, closing a visibility
gap the prior visual-retrofit change explicitly deferred (D7, "Zero new
JavaScript") because it required new JS the retrofit's zero-functional-change
guarantee could not carry.

## Scope

### In Scope
- New JS (loaded on in-app screens using `.barra-pantalla`) that reads
  `navigator.onLine` synchronously on load and updates the chip's text/weight
  immediately, before any `online`/`offline` event fires.
- `online`/`offline` event listeners on `window` that update the same chip
  live, without a page reload.
- Chip markup/state wiring inside the existing `.barra-pantalla` component,
  using the existing `.chip` / `.chip--borde` styles already defined in
  `static/css/components.css` (per DESIGN2.md §4 chip-de-estado weights:
  `offline` = borde negro, `en línea` = no chip or neutral state — exact
  states per DESIGN2.md §1/§4).

### Out of Scope
- Any change to `paso-offline.js`'s existing one-shot `navigator.onLine`
  check (submit-time gating) or the draft-restore banner — they stay
  separate, complementary signals, not merged with the chip.
- Real server-reachability detection (heartbeat/ping). The chip reflects
  network-adapter state only, the same limitation `navigator.onLine` already
  has; accepted for this slice.
- Login screen (`templates/registration/login.html`) — no `.barra-pantalla`
  there, chip does not apply pre-login.
- Full offline-capable login / cached-session entry (DESIGN2 mockup S-01
  "sin señal, sesión cacheada"). That is a separate auth-offline feature
  touching ADR-0005, explicitly parked for a future change.
- `aria-live` announcement on state change — plain visual text/weight change
  is sufficient for this slice.
- Any change to service worker caching scope or IndexedDB draft logic
  (`capa-offline` spec stays as-is).

## Capabilities

### New Capabilities
- None (this extends an existing capability's requirements, not a new one).

### Modified Capabilities
- `capa-offline`: adds a requirement that the shared screen bar exposes a
  live connection-state chip driven by `navigator.onLine` plus
  online/offline listeners, as a visibility extension of the existing
  offline strategy (ADR-0004). No change to draft persistence, sync queue,
  or service-worker caching requirements.

## Approach

Add one small, dedicated JS file (e.g. `static/js/conexion-chip.js`),
following the same defensive/degrade-safely pattern already used by
`offline-db.js` / `paso-offline.js` (ADR-0001's "vanilla JS, no frameworks,
no build pipeline" constraint applies). On `DOMContentLoaded`, read
`navigator.onLine` once to set initial chip state, then attach `online`/
`offline` listeners on `window` for the life of the page to keep it live.
Include the script wherever `.barra-pantalla` renders (via `base.html` or an
equivalent shared include), guarded so its absence doesn't break the chip
markup (script-optional degrade, consistent with existing offline JS
patterns). No new backend endpoint, no schema change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `static/js/conexion-chip.js` | New | `navigator.onLine` init + online/offline listeners updating the chip |
| `templates/base.html` (or shared `.barra-pantalla` partial) | Modified | Include new script; add chip markup slot per DESIGN2.md §4 |
| `static/css/components.css` | Modified (maybe) | Reuse/extend existing `.chip`/`.chip--borde` classes for offline/en línea states, no new visual language |
| `reportes/templates/reportes/sw.js` | Unchanged | Service worker caching stays as-is (out of scope) |
| `openspec/specs/capa-offline/spec.md` | Modified (delta) | New requirement for the live connection chip |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `navigator.onLine` false positive (adapter up, no real internet) misleads user | Medium | Accepted limitation (user decision #3); label/copy stays honest about network-adapter state, not "server reachable" |
| Script load order breaks other JS on the page | Low | Follow existing `offline-db.js`/`paso-offline.js` defensive-load pattern; script is additive and isolated |
| New JS surface increases review/regression risk beyond the "zero JS" retrofit baseline | Low | Small, single-purpose file; no interaction with draft/sync logic |

## Rollback Plan

Revert the new script include and chip markup in `.barra-pantalla`; remove
`static/js/conexion-chip.js`. No data migration, no backend change, so
rollback is a pure static-asset/template revert with no state to reconcile.

## Dependencies

- DESIGN2.md §4 (chip slot already reserved in `.barra-pantalla` layout) and
  §1 (chip visual weights/states).
- ADR-0004 (offline strategy) for the "offline is normal" framing this chip
  makes visible.
- Existing `.chip` CSS from the visual retrofit (`static/css/components.css`).

## Success Criteria

- [ ] Chip shows correct offline/en línea state on initial page load without
      waiting for an event. (Source-content contract test-covered; live
      DevTools confirmation still pending — tasks.md 5.1.)
- [ ] Chip updates live (no reload) when the browser fires `online`/`offline`.
      (Listener-registration test-covered; live DevTools confirmation still
      pending — tasks.md 5.2.)
- [x] Chip appears on every in-app screen using `.barra-pantalla`; does not
      appear on the login screen.
- [x] Existing `paso-offline.js` banner/prompt behavior is unchanged.
- [x] No regression in existing `capa-offline` spec scenarios (draft
      persistence, service-worker caching, `/sw.js` route).

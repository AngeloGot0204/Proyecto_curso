# Proposal: Aggregated Synchronization Screen (S-15)

## Intent

Backlog #10 ships per-step pending/failed sync visibility (`upload-queue`), but a
field user with several drafts across several reports has no single place to see
"what still needs to go up." Today they must open each report and each step to
discover a `pendiente`/`fallo` state. S-15 (DESIGN.md §5, DESIGN2.md tweak S-15)
closes that gap: one screen listing every pending/failed step across every
report, with tipo, fecha, paso, and a per-row "Reintentar", so regaining
connectivity means one screen to clear instead of a report-by-report hunt.

## Scope

### In Scope
- New read-only aggregated list, sourced from the existing Dexie `borradores`
  store (`reportes-offline` DB), across ALL reports for the current device/user
  — no server round-trip required to populate the list.
- Per-row: tipo de reporte, fecha, paso (sección), estado chip (`local`/
  `falló Nv`, per DESIGN2.md tokens), and a "Reintentar" action reusing the
  existing fetch-based submit pipeline (`upload-queue` spec) — no new
  submission path, no duplicate creation (`reporte-idempotent-creation`).
- Empty state when nothing is pending.

### Out of Scope
- Pending/failed *attachment* uploads (`adjuntos_pendientes` store, backlog
  #11) — separate queue, explicitly deferred to a later iteration (confirmed).
- Deleting/discarding a pending row, editing values from this screen, or any
  bulk retry — single-row "Reintentar" only, matching the existing per-step
  affordance. A chronically-failing row stays visible and retryable rather
  than dismissible, to avoid silent data loss (confirmed).
- Fetching display metadata (tipo/fecha) from the server — captured locally
  at draft-write time instead, so the screen works fully offline (confirmed;
  see Approach).
- An embedded panel inside "Mis reportes" (S-02) — this ships as its own
  route, entered via a link/badge from S-02 (confirmed; see Approach).
- Cross-device sync visibility — IndexedDB is per-device (ADR-0004); this
  screen only ever shows what is local to the current browser.
- Changing `iniciar_reporte`/`numero_registro` assignment semantics — reused
  as-is.

## Capabilities

### New Capabilities
- `sincronizacion-pendientes`: aggregated cross-report view of all
  `pendiente`/`fallo` Dexie draft rows, with per-row retry.

### Modified Capabilities
None — `upload-queue` and `reporte-idempotent-creation` requirements are
reused, not changed. If the metadata question below resolves toward capturing
`tipo`/`fecha` at draft-write time, `paso-offline.js`'s write path gains
fields; this is additive data, not a change to any existing scenario in
`upload-queue`'s spec.

## Approach

Add a new route/template rendering a dedicated S-15 page whose JS reads every
row across all `[reporteId+seccionId]` keys in `borradores` (`estado in
{pendiente, fallo}`), grouped/sorted by `actualizadoEn`. `paso-offline.js`'s
`escribirBorrador`/`marcarComo` writers gain `tipoNombre` and `fechaReporte`
fields (read from new `data-*` attributes already available on the step
template's rendered context) so the aggregated screen never depends on a
network call to display tipo/fecha — additive data, no Dexie schema version
bump (per D5 precedent). Reuse `offline-db.js`'s shared schema and the
existing retry/submit fetch logic from `paso-offline.js`, factored into a
shared helper so it can run against a row's stored `valores` without a live
step `<form>` in the DOM. "Mis reportes" (S-02) gains a small entry link/badge
(e.g. "N pendientes de mandar →") pointing at the new route; S-15 is its own
page, not a panel embedded in S-02.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/static/reportes/offline-db.js` | Unchanged (reused) | Shared Dexie schema, already exposes `borradores` |
| `reportes/static/reportes/paso-offline.js` | Modified | Write `tipoNombre`/`fechaReporte` into draft rows; extract retry/submit logic into a shared, form-independent helper |
| `reportes/static/reportes/sincronizacion.js` (new) | New | Aggregated list read (all reports) + retry wiring via the shared helper |
| `reportes/templates/reportes/sincronizacion.html` (new) | New | S-15 screen, own route |
| `reportes/templates/reportes/paso.html` | Modified | Expose `data-tipo-nombre`/`data-fecha-reporte` for the JS to capture |
| `reportes/urls.py`, `reportes/views.py` | Modified | New route serving the S-15 screen shell |
| `reportes/templates/reportes/mis_reportes.html` | Modified | Entry link/badge into the new S-15 route (count of pending/failed rows) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|--------------|
| Retrying outside a live step form breaks CSRF/redirect-follow contract (D4) | Med | Reuse exact `fetch` construction from `paso-offline.js`, verified manually per existing DevTools script |
| Pending-count badge on "Mis reportes" reads IndexedDB, which needs a page-load query across all rows | Low | Single indexed `estado` query on `borradores`, cheap even with many drafts |

## Rollback Plan

Purely additive (new route, new files, one factoring change to
`paso-offline.js`). Revert = remove the new route/template/JS and revert the
factoring diff; no migration, no schema version bump required unless the
metadata question adds fields (still additive, no `db.version()` bump needed
per D5's precedent — new fields are data, not schema).

## Dependencies

- `upload-queue` spec (fetch submit, pendiente/fallo states, manual retry)
- `reporte-idempotent-creation` spec (retry safety, no duplicate `Reporte`)
- Backlog #9 (`capa-offline`) Dexie foundation

## Success Criteria

- [ ] A user with pending/failed steps across 2+ reports sees all of them on
      one screen without opening each report.
- [ ] "Reintentar" from this screen clears the row on success, identically to
      the existing per-step retry.
- [ ] No new duplicate-submission path is introduced.
- [ ] The S-15 screen renders tipo/fecha/paso for every row with zero network
      requests (fully offline-capable).
- [ ] "Mis reportes" (S-02) shows an entry link/badge with the pending/failed
      count, linking to the S-15 route.

## Confirmed Product Decisions

Resolved by the user in the proposal question round; reflected throughout
this document:

1. **Scope**: wizard steps only in this first slice. Pending/failed
   attachment uploads (backlog #11, `adjuntos_pendientes`) are explicitly
   deferred to a later iteration.
2. **Metadata source**: `tipo`/`fecha` are captured locally into the Dexie
   draft row at write time (not fetched from the server), so the screen works
   100% offline.
3. **Entry point**: S-15 is its own route, reached via a link/badge from "Mis
   reportes" (e.g. "3 pendientes de mandar →") — not a panel embedded in S-02.
4. **Actions**: retry only in this first slice. No discard/delete of a
   repeatedly-failing row, to avoid silent data loss.

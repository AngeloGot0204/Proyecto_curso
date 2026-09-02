# Sincronizacion Pendientes Specification

## Purpose

Add a single aggregated, cross-report screen (S-15) listing every
`pendiente`/`fallo` wizard step draft stored locally in Dexie, so a field
user recovering connectivity has one place to clear outstanding work instead
of a report-by-report hunt. The screen is read-only except for a per-row
"Reintentar" action that reuses the existing `upload-queue` fetch/CSRF/
redirect submission contract. Sourced entirely from local IndexedDB — no
server round-trip is required to populate the list. Attachment uploads
(backlog #11, `adjuntos_pendientes`) are out of scope.

## Requirements

### Requirement: Aggregated Cross-Report Pending List

The system MUST provide a dedicated route rendering a list of every Dexie
`borradores` row across ALL reports for the current device/user whose
`estado` is `pendiente` or `fallo`. The list MUST be built entirely from
local IndexedDB reads — no server request is required to populate it.

#### Scenario: Multiple pending/failed steps across multiple reports

- GIVEN the current device's Dexie `borradores` store contains pending/failed
  step rows belonging to 2 or more different reports
- WHEN the user navigates to the sincronizacion-pendientes route
- THEN every pending/failed row across all of those reports is listed on
  this single screen
- AND no network request is made to populate the list

#### Scenario: Screen works fully offline

- GIVEN the device has no network connectivity
- WHEN the user navigates to the sincronizacion-pendientes route
- THEN the list renders using only local Dexie data
- AND no request fails or blocks the render

### Requirement: Per-Row Display Metadata

Each listed row MUST show: tipo de reporte, fecha, paso (sección), and an
estado chip reflecting the row's `pendiente`/`fallo` state per the
DESIGN2.md token set. Tipo and fecha MUST be sourced from data captured
locally in the Dexie row at draft-write time, not fetched from the server.

#### Scenario: Row renders tipo/fecha without a server fetch

- GIVEN a pending/failed draft row was written with `tipoNombre` and
  `fechaReporte` captured at write time
- WHEN the row is rendered on the sincronizacion-pendientes screen
- THEN the tipo de reporte and fecha displayed come from the locally stored
  `tipoNombre`/`fechaReporte` fields
- AND no additional request is made to resolve that metadata

### Requirement: Draft Write Captures Display Metadata

The Dexie draft write path (`paso-offline.js`) MUST persist `tipoNombre` and
`fechaReporte` on each draft row at write time, sourced from data already
available in the step template's rendered context, so the aggregated screen
never depends on a network call. This is additive data and MUST NOT require
a Dexie schema version bump.

#### Scenario: New draft row includes tipo/fecha at write time

- GIVEN a user completes a paso for a report with a known tipo and fecha
- WHEN the client writes/updates the corresponding `borradores` row
- THEN the row includes `tipoNombre` and `fechaReporte` fields matching the
  report's tipo and fecha
- AND no `db.version()` bump is required for this row to be written

### Requirement: Retry-Only Actions, No Discard

Each pending/failed row MUST expose a single "Reintentar" action and MUST
NOT expose any discard/delete/edit action from this screen. A repeatedly
failing row MUST remain visible and retryable rather than being dismissible.

#### Scenario: Row has no discard option

- GIVEN a row is shown as pending/failed on the sincronizacion-pendientes
  screen
- WHEN the user views the available actions for that row
- THEN only "Reintentar" is offered
- AND no discard, delete, or edit action is present

#### Scenario: Repeated retry failure keeps the row visible

- GIVEN a row has failed retry more than once
- WHEN the user views the sincronizacion-pendientes screen again
- THEN the row is still listed with its estado chip and "Reintentar" action
- AND the row is not automatically removed or hidden

### Requirement: Retry Reuses Upload-Queue Submission Contract

The "Reintentar" action MUST resubmit the step using the same fetch-based
submission logic, CSRF handling, and redirect-follow behavior defined by the
`upload-queue` spec, factored into a form-independent helper capable of
running against a stored row's `valores` without a live step `<form>` in the
DOM. Retry MUST NOT introduce a new submission path and MUST NOT create a
duplicate `Reporte` (per `reporte-idempotent-creation`).

#### Scenario: Retry from the aggregated screen succeeds

- GIVEN a pending/failed row is listed on the sincronizacion-pendientes
  screen and connectivity is available
- WHEN the user clicks "Reintentar" for that row
- THEN the client resubmits the step via the shared fetch-based helper using
  the row's stored `valores`
- AND on success the Dexie row is reconciled/cleared identically to a
  same-page retry per the `upload-queue` spec
- AND no duplicate `Reporte` is created

#### Scenario: Retry from the aggregated screen fails again

- GIVEN a pending/failed row is listed on the sincronizacion-pendientes
  screen
- WHEN the user clicks "Reintentar" and the request fails again
- THEN the row remains marked `pendiente`/`fallo`
- AND the row remains visible with the "Reintentar" action, without data
  loss

#### Scenario: Retry follows session-expiry redirect

- GIVEN the Django session has expired
- WHEN the user clicks "Reintentar" for a row on the aggregated screen
- THEN the client follows the same redirect-to-login behavior defined by the
  `upload-queue` spec
- AND the Dexie row is not deleted or cleared

### Requirement: Empty State

The system MUST render an explicit empty state when no `pendiente`/`fallo`
rows exist in Dexie.

#### Scenario: Nothing pending

- GIVEN the current device's Dexie `borradores` store has no rows with
  `estado` in `{pendiente, fallo}`
- WHEN the user navigates to the sincronizacion-pendientes route
- THEN an explicit empty state is shown instead of an empty list
- AND no "Reintentar" actions are rendered

### Requirement: Entry Point From Mis Reportes

The "Mis reportes" screen MUST show an entry link/badge indicating the count
of pending/failed rows and linking to the sincronizacion-pendientes route.
The badge count MUST be derived from a local Dexie query, not a server
request.

#### Scenario: Badge reflects pending count

- GIVEN the current device's Dexie `borradores` store has 3 rows with
  `estado` in `{pendiente, fallo}`
- WHEN the user views "Mis reportes"
- THEN an entry link/badge is shown with a count of 3
- AND the count is computed from a local Dexie query without a server round
  trip

#### Scenario: Badge links to the aggregated screen

- GIVEN the entry link/badge is shown on "Mis reportes"
- WHEN the user activates it
- THEN the user is navigated to the sincronizacion-pendientes route

#### Scenario: No badge when nothing is pending

- GIVEN the current device's Dexie `borradores` store has no rows with
  `estado` in `{pendiente, fallo}`
- WHEN the user views "Mis reportes"
- THEN no pending-count badge is shown (or it shows a zero/hidden state
  consistent with the empty-state convention)

## Out of Scope

- Pending/failed attachment uploads (`adjuntos_pendientes`, backlog #11).
- Discarding, deleting, or editing a pending/failed row from this screen.
- Bulk retry of multiple rows at once.
- Fetching tipo/fecha display metadata from the server.
- An embedded panel inside "Mis reportes" — this ships as its own route.
- Cross-device sync visibility.
- Changes to `iniciar_reporte`/`numero_registro` assignment semantics.

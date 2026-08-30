# Upload Queue Specification

## Purpose

Replace `paso-offline.js`'s synchronous, connectivity-blocking `form.submit()` with a fetch-based, visible pending/failed upload queue that gives the user manual control over retries (per ADR-0004 S-15: sync must be visible and user-retryable, never silent background sync), while preserving drafts across session expiry.

## Requirements

### Requirement: Fetch-Based Step Submission

The system MUST submit each completed paso via `fetch()` instead of a synchronous `form.submit()`, so submission outcome (success/failure) can be observed and reflected in the UI without a full page reload being the only feedback mechanism.

#### Scenario: Successful step submission

- GIVEN a user completes a paso with connectivity available
- WHEN the client submits the step via `fetch()`
- THEN the server processes the step normally
- AND the Dexie draft is reconciled/cleared for that step as it is today

### Requirement: Visible Pending/Failed State

The system MUST mark a Dexie draft's step as `pendiente` or `fallo` when the fetch-based submit does not succeed, and MUST render a visible UI indicator for pending/failed steps. The system MUST NOT silently retry submission in the background without user action.

#### Scenario: Network failure marks draft as pending/failed

- GIVEN a user submits a paso while offline or the network request fails
- WHEN the fetch call errors or returns a non-success response
- THEN the corresponding Dexie draft row is marked `estado: "pendiente"` or `estado: "fallo"`
- AND the UI visibly shows the step as pending/failed
- AND no automatic background retry (e.g. Background Sync API) is triggered

#### Scenario: No silent retry occurs

- GIVEN a step is marked `pendiente`/`fallo`
- WHEN time passes without user interaction
- THEN the client does not automatically resubmit the step
- AND the step remains visibly pending/failed until the user acts

### Requirement: Manual Retry Affordance

The system MUST provide a visible "Reintentar" button for each pending/failed step, which resubmits the step via `fetch()` and clears the pending/failed marker on success.

#### Scenario: Manual retry succeeds

- GIVEN a step is shown as pending/failed with a "Reintentar" button
- WHEN the user clicks "Reintentar" and connectivity is available
- THEN the client resubmits the step via `fetch()`
- AND on success, the pending/failed marker is cleared and the step is reconciled as synchronized

#### Scenario: Manual retry fails again

- GIVEN a step is shown as pending/failed
- WHEN the user clicks "Reintentar" and the request fails again
- THEN the step remains marked `pendiente`/`fallo`
- AND the UI continues to show the retry affordance without data loss

### Requirement: Draft Survives Session Expiry

The system MUST preserve the IndexedDB (Dexie) draft independent of Django session state. If the Django session expires mid-draft, the system MUST redirect the user to login without discarding the local draft, and MUST allow idempotent resubmission after re-login via `id_local`.

#### Scenario: Session expires mid-draft

- GIVEN a user has an in-progress draft stored in IndexedDB with an assigned `id_local`
- WHEN the Django session expires and the next step submission is rejected/redirected to login
- THEN the user is redirected to the login page
- AND the IndexedDB draft (including `id_local` and pending steps) is not deleted or cleared

#### Scenario: Resubmission after re-login is idempotent

- GIVEN a draft survived a session expiry as above
- WHEN the user re-logs in and resubmits the pending step(s) using the same `id_local`
- THEN the server treats the resubmission idempotently (per `reporte-idempotent-creation`), creating no duplicate `Reporte`
- AND the draft is reconciled and marked synchronized on success

## Out of Scope

- Field-by-field sync granularity (rejected per ADR-0004).
- Background Sync API (explicitly rejected per ADR-0004).

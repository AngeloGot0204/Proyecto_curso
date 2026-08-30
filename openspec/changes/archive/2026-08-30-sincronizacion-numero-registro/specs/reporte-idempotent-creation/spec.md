# Reporte Idempotent Creation Specification

## Purpose

Ensure `Reporte` creation via `iniciar_reporte` is race-free and idempotent, and that `numero_registro` is assigned from a Postgres DB sequence rather than computed in Python, so retried requests never produce duplicate `Reporte` rows or duplicate/skipped registration numbers.

## Requirements

### Requirement: Client-Generated Local Identifier

The system MUST support a client-generated `id_local` (UUID) field on `Reporte`, sent as a hidden form field on the `/reportes/<codigo>/nuevo/` POST, and MUST enforce uniqueness for `id_local` at the database level.

#### Scenario: id_local sent on creation POST

- GIVEN a user starts a new reporte in `paso-offline.js`
- WHEN the client generates a UUID and includes it as a hidden `id_local` field on the POST to `/reportes/<codigo>/nuevo/`
- THEN the server persists `id_local` on the created `Reporte`
- AND the database rejects any second `Reporte` row with the same `id_local` via a unique constraint

### Requirement: Sequence-Based numero_registro Assignment

The system MUST assign `Reporte.numero_registro` using a Postgres database sequence (`nextval`), and MUST NOT compute it via Python (e.g. `max() + 1`) or any other race-prone application-level method.

#### Scenario: First creation consumes one sequence value

- GIVEN no `Reporte` exists yet for a given `id_local`
- WHEN `iniciar_reporte` creates the `Reporte` for the first time
- THEN `numero_registro` is assigned via `nextval` on the dedicated Postgres sequence
- AND the assigned value is unique and monotonically increasing across concurrent creations

#### Scenario: Two distinct drafts get distinct sequential numbers

- GIVEN two different `id_local` values are submitted by the same or different users
- WHEN both trigger `iniciar_reporte`
- THEN two distinct `Reporte` rows are created
- AND each has a distinct `numero_registro`, both drawn from the same sequence

### Requirement: Idempotent iniciar_reporte

The system MUST implement `iniciar_reporte` as an idempotent operation keyed on `(id_local, creador)`, using `get_or_create` semantics, so that retrying the same POST (network retry, double-click, offline-then-retry) returns the existing `Reporte` and its already-assigned `numero_registro` instead of creating a new row or consuming a new sequence value.

#### Scenario: Retried POST with same id_local is idempotent

- GIVEN a `Reporte` was already created for a given `id_local` and `creador`, with `numero_registro` N
- WHEN the same POST (same `id_local`, same `creador`) is submitted again to `iniciar_reporte`
- THEN no new `Reporte` row is created
- AND the response references the same `Reporte`
- AND `numero_registro` is still N (no new sequence value is consumed)

#### Scenario: Concurrent identical retries do not duplicate

- GIVEN two near-simultaneous POSTs are received with the same `id_local` and `creador`
- WHEN both reach `iniciar_reporte` concurrently
- THEN the database `unique` constraint on `id_local` prevents a duplicate row
- AND the losing request re-fetches and returns the existing `Reporte`/`numero_registro` instead of failing

## Out of Scope

- Field-by-field sync granularity (rejected per ADR-0004; sync remains per completed step/section).
- Displaying `numero_registro` in other screens (e.g. "Mis reportes"); that is separate work.

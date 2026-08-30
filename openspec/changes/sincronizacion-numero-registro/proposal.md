# Proposal: Sincronización y asignación de número de registro

## Intent

`Reporte.numero_registro` is never assigned today, and `iniciar_reporte` unconditionally calls `Reporte.objects.create(...)` on every POST — a retried request (network hiccup, double-click, offline-then-retry) creates a duplicate `Reporte`. Post-#9's offline draft persistence (IndexedDB via Dexie) also has no real upload queue: `paso-offline.js` still uses a synchronous `form.submit()` that requires live connectivity, with no pending/failed state or retry UI. This change closes both gaps: a race-free, idempotent registro-number assignment, and a visible, retryable upload queue consistent with ADR-0004 (S-15: sync must be visible and user-retryable, not silent background sync).

## Scope

### In Scope
- `Reporte.id_local`: client-generated UUID, generated in `paso-offline.js` at Reporte-creation time, stored in IndexedDB with the draft, sent as a hidden field on the `/reportes/<codigo>/nuevo/` POST, enforced unique at the DB level.
- `Reporte.numero_registro`: assigned via a Postgres DB sequence (`RunSQL` migration, `nextval`-based — never Python `max()+1`), assigned at Reporte creation time inside `iniciar_reporte`.
- Idempotent `iniciar_reporte`: `get_or_create` keyed on `(id_local, creador)` (exact uniqueness scope confirmed in design) so a retried POST returns the same `Reporte` and the same `numero_registro` instead of creating a duplicate.
- Client-side upload queue: replace `paso-offline.js`'s synchronous `form.submit()` with a fetch-based submit; on failure mark the Dexie draft row `estado: "pendiente"`/`"fallo"`; visible UI showing pending/failed steps with a manual "Reintentar" button; on success, clear the pending marker and reconcile as today.
- Automated test verifying session-expiry mid-draft preserves the IndexedDB draft (login redirect happens, draft survives independent of Django session) and that re-login + resubmit is idempotent via `id_local`.

### Out of Scope
- Field-by-field sync granularity (ADR-0004 rejected this; sync stays per completed section, matching current per-step POST granularity).
- Background Sync API (explicitly rejected in ADR-0004).
- Any change to `numero_registro` display/usage beyond persisting it (e.g. "Mis reportes" #12 showing it is separate work).

## Capabilities

### New Capabilities
- `reporte-idempotent-creation`: `id_local`-keyed idempotent creation of `Reporte` plus DB-sequence-based `numero_registro` assignment.
- `upload-queue`: client-side pending/failed upload queue with visible manual retry, replacing synchronous form submission.

### Modified Capabilities
- None (no existing spec files cover Reporte creation or client sync today; both above are additive).

## Approach

1. Add `id_local` (UUIDField, unique) and `numero_registro` (IntegerField, nullable until assigned) to `Reporte`, plus a migration creating the Postgres sequence via `RunSQL`.
2. Rewrite `iniciar_reporte` to `get_or_create(id_local=..., creador=...)`, assigning `numero_registro` from `nextval(...)` only on first creation.
3. In `paso-offline.js`, generate `id_local` (UUID) at draft-creation time, persist it in Dexie, and send it as a hidden POST field.
4. Replace `form.submit()` with `fetch()`; introduce `estado: pendiente|fallo|sincronizado` on the Dexie draft; render a visible queue UI with a "Reintentar" button per S-15.
5. Add a test (Django test client + IndexedDB/session simulation, or a documented manual script if automation is infeasible for the browser-side part) proving session-expiry-then-resubmit is idempotent via `id_local`.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/models.py` | Modified | Add `id_local`, `numero_registro` fields |
| `reportes/migrations/` | New | `RunSQL` migration creating Postgres sequence |
| `reportes/views.py::iniciar_reporte` | Modified | `.create()` → idempotent `get_or_create` + sequence assignment |
| `reportes/static/reportes/paso-offline.js` | Modified | `form.submit()` → fetch-based upload queue, `id_local` generation, pendiente/fallo UI |
| `reportes/templates/reportes/` (paso template) | Modified | Add hidden `id_local` field, pending/retry UI markup |
| `reportes/tests/` | New | Sequence assignment, `id_local` uniqueness/idempotency, session-expiry-preserves-draft tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| First DB sequence + idempotency-key pattern in this codebase — no existing convention | Med | Document the pattern explicitly in design.md for reuse |
| `get_or_create` race under concurrent identical retries | Low | Rely on the DB `unique` constraint on `id_local`; catch `IntegrityError` and re-fetch |
| Client JS upload queue has no automated test runner in this project (same limitation as #9) | Med | Cover with a documented manual verification script |
| Session-expiry-preserves-draft assumed but previously unverified | Low | Explicit test added in this change |

## Rollback Plan

Revert the migration (drop sequence, drop columns) and revert `iniciar_reporte`/`paso-offline.js` to prior commits. `id_local`/`numero_registro` are additive and nullable-until-backfill, so rollback does not require a data migration for existing rows created before this change.

## Dependencies

- Postgres as the DB backend (sequence syntax is Postgres-specific `RunSQL`).
- Builds on #9's IndexedDB/Dexie draft persistence (`paso-offline.js`).

## Success Criteria

- [ ] A retried `iniciar_reporte` POST with the same `id_local` never creates a duplicate `Reporte` and returns the same `numero_registro`.
- [ ] `numero_registro` values are assigned via DB sequence with no race under concurrent creation.
- [ ] Upload queue shows pending/failed state and a working manual "Reintentar" button; failed uploads recover without data loss.
- [ ] Automated test confirms session-expiry mid-draft preserves the draft and re-login + resubmit is idempotent.

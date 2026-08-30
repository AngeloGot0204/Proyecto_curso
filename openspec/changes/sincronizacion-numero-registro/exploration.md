# Exploration: Sincronización y asignación de número de registro (Backlog #10)

## ADR-0004 — already fully decided

- **Manual retry, not background sync**: Background Sync API was explicitly considered and rejected in ADR-0004 ("Alternativas consideradas") — browser support is uneven, and it contradicts the design principle that sync must be *visible and retryable by the user* (S-15). "Sincronización" in backlog #10 means: a visible pending queue with a manual "reintentar" button, not automatic background upload.
- **`numero_registro`**: assigned via a **DB sequence** (`nextval`), explicitly not `max()+1` in Python, to eliminate race conditions between concurrent syncs (RESOLUCION-ADVERSARIAL.md). Assigned **when the server receives the synced report** (order of arrival) — not at Reporte creation, not at cierre/generación.
- **`id_local`**: client-generated ID with a `unique` DB constraint, serving as the idempotency key so a retried submission never creates a duplicate `Reporte`.
- **Sync granularity**: one submit per completed role-section, atomically, keyed by `id_local` — finer-grained (field-by-field) sync was explicitly rejected as disproportionate complexity.
- Session-expiry-preserves-draft is a stated acceptance criterion in TECH-DESIGN.md, not elaborated mechanically by ADR-0004.

## Current code state (post-#9)

- `reportes/models.py::Reporte` has only `tipo`, `definicion`, `creador`, `fecha_creacion`, `estado`. **No `id_local`, no `numero_registro` yet.**
- `reportes/views.py::iniciar_reporte` calls `Reporte.objects.create(...)` **unconditionally** on every POST — no idempotency guard exists today. A retried POST to `/reportes/<codigo_tipo>/nuevo/` would create a second row.
- `reportes/static/reportes/paso-offline.js`: persists per-step drafts to IndexedDB via Dexie, but the actual submission is a real synchronous `form.submit()` requiring live connectivity at click time. There is **no upload queue, no network-retry logic, no "falló"/pending UI**. Its `reconciliar()` function only reconciles a local draft against what the server already has *after a page reload/redirect* — it is not a retry-on-reconnect mechanism.
- Session expiry: `@login_required` (Django default) redirects to `LOGIN_URL = "login"` on an expired session, losing the in-flight POST per Django's default behavior. Since the IndexedDB draft is keyed by `reporteId`+`seccionId` independent of session state, the draft itself very likely survives as an architectural side effect — but unverified by any test.

## Codebase precedent

No DB sequence usage exists anywhere. No idempotency-key pattern exists. No test file targets idempotency or sequences. This will be the first instance of both patterns in the codebase.

## Recommended smallest slice for #10

1. `id_local` field (unique) + idempotent `get_or_create` in `iniciar_reporte`, replacing the unconditional `.create()`.
2. `numero_registro` field + Postgres sequence (via `RunSQL` migration), assigned at the point the server first accepts the synced report — needs one design decision: which exact endpoint constitutes "sincronizar" given the current architecture already POSTs eagerly per step rather than queuing.
3. Build the actual client-side "cola de subida": wrap `form.submit()` in a fetch-based submit with failure handling, mark Dexie rows `pendiente`/`falló`, and add a visible retry UI (S-15) — this does not exist yet.
4. Verify (ideally via an automated test) that session-expiry mid-draft truly preserves the draft end-to-end, including that resubmitting after re-login is idempotent via `id_local`.

## Open Decisions (must be settled in proposal)
1. Which exact moment counts as "sincronizar" for `numero_registro` assignment, given the current architecture already submits each step's POST live (not queued)? Options: assign on `iniciar_reporte` (first successful create), or on `cerrar_reporte` (closing), or on first successful step-sync after being offline.
2. Full scope: build the real upload queue (fetch-based submit + pendiente/falló state + retry button) now, or defer to a smaller slice that only adds `id_local`/`numero_registro` plumbing without the queue UI?

## Risks
- Deciding exactly which endpoint/moment counts as "sincronizar" for `numero_registro` assignment is genuinely ambiguous given the current architecture — must be resolved explicitly, not left implicit.
- Session-expiry-preserves-draft is assumed likely-already-working from architecture but unverified — should not be marked "done" without an explicit check.
- This is the first DB sequence and first idempotency-key pattern in the codebase — no existing convention to follow, whatever's built here sets precedent.

## Key Learnings
1. ADR-0004 already rejected Background Sync API in favor of visible manual retry (S-15) — "sincronización" means a retry button, not silent background upload.
2. `numero_registro` must use a DB sequence (`nextval`), never Python-side `max()+1`, to avoid races between concurrent syncs.
3. `iniciar_reporte` currently has zero idempotency guard — every POST unconditionally creates a new `Reporte` row.
4. No upload queue exists yet despite #9's offline draft persistence — submission still requires live connectivity at click time.

**Next**: sdd-propose (pending the 2 open decisions above)

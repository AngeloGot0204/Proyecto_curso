# Design: Sincronización y asignación de número de registro

## Technical Approach

Two independent halves, both additive. **Server**: `Reporte` gains `id_local` (UUID, unique) and `numero_registro` (bigint, unique), both filled by **Postgres-level `DEFAULT` expressions**, not Python; `iniciar_reporte` becomes `get_or_create`-based so a retried POST returns the same row and the same `numero_registro`. **Client**: `paso-offline.js`'s `form.submit()` is replaced by a `fetch()` pipeline with `pendiente`/`fallo` draft states and an inline retry banner (ADR-0004 / S-15: visible, manually retryable — never Background Sync). No ADR deviation.

## Architecture Decisions

### D1 — `numero_registro` via `db_default` + `RunSQL` sequence

**Choice**: `RunSQL("CREATE SEQUENCE IF NOT EXISTS reportes_numero_registro_seq", reverse_sql="DROP SEQUENCE IF EXISTS reportes_numero_registro_seq")` followed, in the same migration, by

```python
numero_registro = models.BigIntegerField(
    unique=True, editable=False,
    db_default=Func(Value("reportes_numero_registro_seq"), function="nextval"),
)
```

**Alternatives**: (a) `save()` override calling `nextval()` — rejected: extra roundtrip, must be guarded against updates, and any INSERT path bypassing `save()` silently gets no number; (b) bare `RunSQL ALTER COLUMN SET DEFAULT` with a plain nullable field — rejected: Django sends an explicit `NULL` for a known nullable column, so the DB `DEFAULT` never fires, and the default is invisible to migration state.

**Rationale (ORM compatibility, verified in the installed Django 5.2 source)**: `Field.db_returning` is `has_db_default() and connection.features.can_return_columns_from_insert` (`django/db/models/fields/__init__.py:933`), and Postgres sets that feature. Django therefore emits `INSERT … RETURNING numero_registro, id_local`, so `reporte.numero_registro` is populated on the in-memory instance immediately — **no `refresh_from_db()` needed** for the response/redirect. `BaseDatabaseSchemaEditor.db_default_sql` (`base/schema.py:434`) keeps the `DEFAULT` on the column (unlike Python `default=`, which Django drops after backfill). `AddField` emits `ADD COLUMN … DEFAULT (nextval(…)) NOT NULL`; `nextval` is volatile, so Postgres rewrites the table and gives each pre-existing row a distinct number. Sequence gaps on rolled-back transactions are expected and are not a defect.

### D2 — `id_local`: UUIDField with a DB default too

**Choice**: `id_local = models.UUIDField(unique=True, editable=False, db_default=Func(function="gen_random_uuid"))`.

**Alternatives**: `default=uuid.uuid4` (Python) — rejected: `AddField` with a Python default writes *the same* UUID into every existing row, violating `unique`; the workaround is a three-step nullable→`RunPython`→`AlterField` migration. `gen_random_uuid()` is volatile, so one `ADD COLUMN` backfills distinct values, is symmetric with D1, and is returned via the same `RETURNING`. Requires Postgres ≥ 13 (built-in since 13; Neon is newer).

Keeping a server-side default means every current caller — the test suite, admin, and any future non-JS entry point — keeps working while no client sends `id_local`.

### D3 — Idempotency scope: lookup on `(id_local, creador)`, uniqueness on `id_local` alone

**Choice**: DB constraint is global (`unique=True` on `id_local`); the view's lookup is `Reporte.objects.get_or_create(id_local=..., creador=request.user, defaults={...})`.

**Rationale**: a client-generated UUID makes cross-user collision astronomically unlikely, but *hostile* reuse is trivial — someone can POST another user's `id_local`. With `creador` in the lookup, that POST does not match, falls through to `create`, and the global unique constraint raises `IntegrityError` → the view answers `400`, never returning another user's `Reporte`. Global uniqueness (rather than `unique_together(id_local, creador)`) is what makes that failure mode *loud* instead of silently forking two reports on one local id.

### D4 — Fetch-based submit, not `XMLHttpRequest`, not `form.submit()`

**Choice**: `fetch(form.action, {method:"POST", body:new FormData(form), credentials:"same-origin", redirect:"follow"})`.

- **CSRF**: `{% csrf_token %}` already renders `csrfmiddlewaretoken` inside the form, and `new FormData(form)` carries it. No `X-CSRFToken` header is needed (that is only required for non-form bodies).
- **Redirect**: `fetch` follows transparently but does **not** navigate. Success is `response.ok` (and `response.redirected`); the client then does `location.assign(response.url)`. `redirect:"manual"` was rejected — it yields an opaque `type:"opaqueredirect"`, `status:0` response whose `Location` cannot be read. Accepted cost: the followed redirect issues one extra `GET` of the next step before the real navigation; that request has `mode:"cors"`, not `"navigate"`, so `sw.js`'s `esNavegacionDePaso` guard misses it and it is passed through uncached — harmless, and the subsequent real navigation is cached normally.
- **Service worker**: unchanged. `sw.js:44` already returns early for non-`GET`, so the POST always hits the network.

### D5 — Shared Dexie schema module

**Choice**: new `reportes/static/reportes/offline-db.js` owning the single `version(2).stores({ borradores: "[reporteId+seccionId], reporteId, estado", nuevos: "codigoTipo" })` declaration, consumed by both `paso-offline.js` and `nuevo-reporte.js`.

**Rationale**: two scripts calling `.version()` on the same Dexie database name with different store sets produces an inconsistent upgrade. `borradores` keeps its v1 shape (the new `estado` values are data, not schema); `nuevos` is new.

### D6 — Retry is scoped to the step's own page (confirming #9's model)

**Choice**: the pending/failed banner renders inline on the current step, injected with `form.insertAdjacentElement("beforebegin", …)` exactly like #9's restore prompt. Leaving the step keeps the row at `pendiente`/`fallo`; returning re-renders the banner from `reconciliar()`.

**Alternative rejected**: a global cross-step queue in `base.html` (full S-15 list). It needs a report-level index page that does not exist yet — "Mis reportes" (#12) owns that surface. Per-step scoping matches the existing `[reporteId+seccionId]` key and adds no new reconciliation model.

### D7 — `id_local` client generation has no host page yet

No template currently POSTs to `reportes_nuevo` (the route is exercised only by tests). `nuevo-reporte.js` is therefore written against a documented hook — `form[data-nuevo-reporte][data-codigo-tipo]` — and **no-ops when absent** (`if (!form) return;`, the same defensive opening as `paso-offline.js`). The wizard-entry template stays out of scope (#12). Until it exists, D2's `gen_random_uuid()` default covers creation.

## Data Flow

```
"Nuevo reporte" page (future, #12)
  nuevo-reporte.js ── DOMContentLoaded ──> Dexie.nuevos[codigoTipo]
        │  crypto.randomUUID() if absent          (persisted BEFORE first POST,
        │                                          so every retry reuses it)
        └──> <input type="hidden" name="id_local"> ──> POST /reportes/<cod>/nuevo/
                                                            │
        iniciar_reporte: get_or_create(id_local, creador) ───┤
              INSERT … RETURNING id_local, numero_registro   │  (nextval fires once;
                                                             │   retry = no INSERT)
                        302 -> /reportes/<id>/paso/<sec>/ <──┘
                                    │
        response.redirected -> delete Dexie.nuevos[codigoTipo], location.assign

Step page
  paso-offline.js:  input/change ──debounce 400ms──> borradores{estado:"borrador"}
        submit ──> estado:"enviando" ──> fetch POST
                       ├─ ok            -> delete row, location.assign(response.url)
                       ├─ /login/       -> estado:"fallo" (sesion_expirada), navigate
                       ├─ HTTP >= 400   -> estado:"fallo",     intentos++
                       └─ network error -> estado:"pendiente", intentos++
                                             └─> banner + [Reintentar] -> re-submit
```

### Draft state machine

| From | Trigger | To | UI |
|------|---------|----|----|
| — | first `input`/`change` | `borrador` | none |
| `borrador` | submit | `enviando` | button disabled |
| `enviando` | `response.ok` | row deleted | navigate to `response.url` |
| `enviando` | fetch rejects / `!navigator.onLine` | `pendiente` | banner "Sin conexión — pendiente de subir (N)" + Reintentar |
| `enviando` | HTTP ≥ 400, or final URL is `/login/` | `fallo` | banner "No se pudo subir (N intentos)" + Reintentar |
| `pendiente`/`fallo` | Reintentar click | `enviando` | re-serializes the *current* form (user may have edited) |
| `pendiente`/`fallo` | page load | unchanged | `reconciliar()` restores values + re-renders banner |
| `enviando` | page load (stale, #9 rule) | `borrador` | existing restore prompt (unchanged) |

Row gains `intentos: number` and `ultimoError: string`. `estado: "sincronizado"` is not persisted — success deletes the row, preserving #9's clear-on-success contract.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reportes/models.py` | Modify | `Reporte.id_local`, `Reporte.numero_registro` (D1, D2) |
| `reportes/migrations/0005_id_local_numero_registro.py` | Create | `RunSQL` sequence → `AddField` × 2, in that order (D8) |
| `reportes/views.py::iniciar_reporte` | Modify | `get_or_create` + `IntegrityError` handling + `id_local` parsing |
| `reportes/static/reportes/offline-db.js` | Create | Single Dexie schema owner, v2 (D5) |
| `reportes/static/reportes/paso-offline.js` | Modify | fetch submit, `pendiente`/`fallo`, retry banner |
| `reportes/static/reportes/nuevo-reporte.js` | Create | `id_local` generation/persistence, no-op without host form (D7) |
| `reportes/templates/reportes/paso.html` | Modify | `<script>` for `offline-db.js` before `paso-offline.js` |
| `reportes/tests/test_idempotencia.py` | Create | D1–D3 coverage |
| `reportes/tests/test_views.py` | Modify | `iniciar_reporte` scenarios, redirect-follow contract |

## Interfaces / Contracts

```python
# reportes/views.py::iniciar_reporte
crudo = request.POST.get("id_local")
if crudo:
    try:
        id_local = uuid.UUID(crudo)
    except (ValueError, AttributeError):
        return HttpResponseBadRequest("id_local inválido.")
else:
    id_local = uuid.uuid4()          # non-JS callers; DB default is the backstop

try:
    with transaction.atomic():
        reporte, creado = Reporte.objects.get_or_create(
            id_local=id_local, creador=request.user,
            defaults={"tipo": tipo, "definicion": tipo.definicion_activa},
        )
except IntegrityError:               # id_local belongs to another creador
    return HttpResponseBadRequest("id_local ya utilizado.")
if not creado and reporte.tipo_id != tipo.id:
    return HttpResponseBadRequest("id_local corresponde a otro tipo de reporte.")
# reporte.numero_registro is already set — INSERT … RETURNING (D1)
```

Migration ordering inside `0005` (single migration; both columns are one logical change — "identity fields for idempotent creation"):

1. `RunSQL(CREATE SEQUENCE …, reverse_sql=DROP SEQUENCE …)` — **must precede** the column, whose `DEFAULT` references it.
2. `AddField("reporte", "id_local", …)`
3. `AddField("reporte", "numero_registro", …)`

Reverse order drops both columns before dropping the sequence, so the reverse is clean.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Integration (pytest, RED first) | sequence, uniqueness, idempotency, session expiry | Django test client + real Postgres test DB (`--reuse-db`) |
| Manual | fetch submit, retry button, pending UI, `id_local` reuse | Chrome DevTools script below (#9 precedent) |

**Server-side scenarios** (`reportes/tests/test_idempotencia.py` unless noted):

1. `test_create_asigna_numero_registro_sin_refresh` — `Reporte.objects.create(...)` returns an instance whose `numero_registro` is not `None` **without** `refresh_from_db()` (proves `RETURNING`).
2. `test_numero_registro_avanza_por_secuencia` — two consecutive creates: `segundo.numero_registro > primero.numero_registro` (strict `>`, not `+1`: gaps are legitimate).
3. `test_numero_registro_es_unico` — a manual duplicate raises `IntegrityError`.
4. `test_id_local_unico_a_nivel_bd` — two `Reporte`s with the same `id_local` → `IntegrityError` inside `transaction.atomic()`.
5. `test_id_local_por_defecto_es_distinto_por_fila` — two creates without `id_local` get different UUIDs (proves `gen_random_uuid`, not a shared Python default).
6. `test_post_nuevo_repetido_mismo_id_local_no_duplica` — same `id_local` POSTed twice → `Reporte.objects.count() == 1`, identical redirect `Location`, identical `numero_registro`.
7. `test_post_nuevo_sin_id_local_sigue_funcionando` — backwards compatibility for the existing `test_post_nuevo_crea_un_reporte` path.
8. `test_id_local_invalido_devuelve_400`.
9. `test_id_local_de_otro_usuario_devuelve_400` — user B POSTs A's `id_local` → 400, `count() == 1`, B has no access to A's report.
10. `test_id_local_de_otro_tipo_devuelve_400`.
11. `test_paso_post_redirect_es_seguible` (`test_views.py`) — the `paso` POST answers 302 and `follow=True` lands 200 on the next step; this is exactly the `response.redirected` / `response.url` contract the fetch client depends on.

**Session expiry — what *is* server-testable** (scenario 12, `test_sesion_expirada_no_rompe_idempotencia`): the IndexedDB persistence itself cannot be tested (no JS runner in this project), but the *resume contract* can be, end to end: POST with `id_local=X` (creates report + number) → `client.logout()` → POST again with `X` → assert 302 to `LOGIN_URL` and `count()` unchanged (the expired POST creates nothing) → `client.force_login(usuario)` → POST again with `X` → assert the **same** `Reporte.pk` and the **same** `numero_registro`, `count() == 1`. That proves the half that can fail server-side: a draft replayed after re-login is idempotent, never a duplicate. Manual step 6 covers the remaining client half (the row surviving in IndexedDB across the login redirect).

**Manual DevTools script (Chrome, live dev server)** — same format as #9:

1. **Fetch submit path** — open a step, edit a field, submit. Network shows a single `fetch` POST (Type `fetch`, not `document`), then a `document` GET of the next step. You land on the next step; the `borradores` row for the previous step is gone.
2. **Pending on network drop** — edit, set Network ▸ **Offline**, submit → no navigation; inline banner "pendiente de subir (1)" appears above the form; Application ▸ IndexedDB ▸ `borradores` row shows `estado:"pendiente"`, `intentos:1`.
3. **Retry while still offline** — click **Reintentar** → banner count becomes 2, `intentos:2`, still `pendiente`.
4. **Retry after reconnect** — **No throttling**, click **Reintentar** → POST succeeds, you navigate to the next step, the row disappears.
5. **Server failure state** — stop the dev server, submit → row `estado:"fallo"`, banner "No se pudo subir"; restart the server, Reintentar → success.
6. **Session expiry preserves the draft** — edit a field (row present), clear the `sessionid` cookie, submit → the response's final URL is `/login/`, row becomes `estado:"fallo"` and **is still present with its `valores` intact**; log in again, return to the step → restore prompt/banner appears with the same values; Reintentar → succeeds.
7. **`id_local` reuse across retries** — with a `data-nuevo-reporte` form present (or one injected by hand), inspect `nuevos[codigoTipo]`: the same `idLocal` before and after a failed POST; after success the row is deleted and the next "Nuevo reporte" gets a fresh UUID.
8. **No duplicate report** — double-click the start button while throttled to Slow 3G → exactly one `Reporte` row in Django admin, one `numero_registro`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The one security-relevant surface (a client-supplied identifier used as a lookup key) is handled in D3.

## Migration / Rollout

Single forward migration; both columns are additive with DB defaults, so no downtime step and no data migration. Rollback = `migrate reportes 0004` (drops both columns, then the sequence) plus reverting the three JS/template files. **#9's service-worker rollback warning does not apply**: `sw.js` is untouched, so no stale worker can survive a revert of this change.

## Open Questions

- [ ] `gen_random_uuid()` assumes Postgres ≥ 13 — confirm the Neon branch version before apply (fallback: the three-step `RunPython` backfill rejected in D2).
- [ ] The full S-15 cross-report queue list stays deferred to "Mis reportes" (#12); this change ships per-step visibility only.
- [ ] `nuevo-reporte.js` ships with no host template (D7) and is therefore only manually verifiable via an injected form until #12 lands.

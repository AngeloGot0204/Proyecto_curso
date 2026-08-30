# Tasks: Sincronización y asignación de número de registro

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~550-650 (migration ~30, models ~15, views ~40, offline-db.js ~30 new, paso-offline.js rewrite ~150, nuevo-reporte.js ~50 new, template ~15, tests ~200+) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (server idempotency) → PR 2 (upload queue rework) → PR 3 (nuevo-reporte.js infra) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (resolved before this apply run) |

Decision needed before apply: No (resolved: stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Sequence-backed `id_local`/`numero_registro` + idempotent `iniciar_reporte` | PR 1 | `pytest reportes/tests/test_idempotencia.py reportes/tests/test_views.py -k "id_local or numero_registro or redirect_es_seguible"` | Django test client + real Postgres test DB (`--reuse-db`) | `migrate reportes 0004`, revert `views.py::iniciar_reporte` |
| 2 | `offline-db.js` + fetch-based `paso-offline.js` (pendiente/fallo, retry banner) | PR 2 | No automated JS runner — Manual DevTools script (task 4.x) | Manual: Chrome DevTools, live dev server, Network ▸ Offline/Slow 3G | Revert `paso-offline.js`, `offline-db.js`, `paso.html` script tag |
| 3 | `nuevo-reporte.js` (forward-looking `id_local` client generation, no host template yet) | PR 3 | N/A — no host page exists yet (D7); verify only via injected `data-nuevo-reporte` form | Manual: inject test form in DevTools console, inspect Dexie `nuevos` store | Delete `nuevo-reporte.js`; no other file depends on it |

## Phase 1: Server Migration (Foundation)

- [x] 1.1 Add `RunSQL(CREATE SEQUENCE IF NOT EXISTS reportes_numero_registro_seq, reverse_sql=DROP SEQUENCE IF EXISTS reportes_numero_registro_seq)` in `reportes/migrations/0005_id_local_numero_registro.py`.
- [x] 1.2 In the same migration, `AddField("reporte", "id_local", models.UUIDField(unique=True, editable=False, db_default=Func(function="gen_random_uuid")))`.
- [x] 1.3 In the same migration, `AddField("reporte", "numero_registro", models.BigIntegerField(unique=True, editable=False, db_default=Func(Value("reportes_numero_registro_seq"), function="nextval")))`, ordered after `id_local` per design's migration ordering.
- [x] 1.4 Update `reportes/models.py::Reporte` with matching `id_local`/`numero_registro` field declarations (D1/D2).
- [x] 1.5 Run `python manage.py migrate reportes` against the Postgres test DB and confirm no errors; run `python manage.py migrate reportes 0004` to confirm reverse SQL drops cleanly.

## Phase 2: Server-Side Idempotency (TDD)

- [x] 2.1 RED: write `test_create_asigna_numero_registro_sin_refresh` in `reportes/tests/test_idempotencia.py` (asserts `numero_registro` set without `refresh_from_db()`).
- [x] 2.2 RED: write `test_numero_registro_avanza_por_secuencia` (strict `>` across two creates).
- [x] 2.3 RED: write `test_numero_registro_es_unico` (manual duplicate raises `IntegrityError`).
- [x] 2.4 RED: write `test_id_local_unico_a_nivel_bd` (duplicate `id_local` raises `IntegrityError` inside `transaction.atomic()`).
- [x] 2.5 RED: write `test_id_local_por_defecto_es_distinto_por_fila` (two DB-default creates differ).
- [x] 2.6 GREEN: confirm 2.1-2.5 pass against the Phase 1 migration/model (should already pass — DB-level behavior).
- [x] 2.7 RED: write `test_post_nuevo_repetido_mismo_id_local_no_duplica` in `reportes/tests/test_idempotencia.py` (same `id_local` POSTed twice → `count()==1`, identical `Location`, identical `numero_registro`).
- [x] 2.8 RED: write `test_post_nuevo_sin_id_local_sigue_funcionando`, `test_id_local_invalido_devuelve_400`, `test_id_local_de_otro_usuario_devuelve_400`, `test_id_local_de_otro_tipo_devuelve_400`.
- [x] 2.9 GREEN: rewrite `reportes/views.py::iniciar_reporte` to parse `id_local` from `request.POST`, fall back to `uuid.uuid4()`, wrap `get_or_create(id_local=..., creador=request.user, defaults={...})` in `transaction.atomic()`, catch `IntegrityError` → `HttpResponseBadRequest`, and check `reporte.tipo_id != tipo.id` → 400 per the design interface contract.
- [x] 2.10 GREEN: run all Phase 2 tests, confirm pass.
- [x] 2.11 RED: write `test_paso_post_redirect_es_seguible` in `reportes/tests/test_views.py` (302 then `follow=True` lands 200).
- [x] 2.12 GREEN: confirm 2.11 passes (no view change expected; documents existing redirect contract the fetch client depends on).
- [x] 2.13 RED: write `test_sesion_expirada_no_rompe_idempotencia` (POST with `id_local=X` → `client.logout()` → POST X again asserts 302 to `LOGIN_URL` and unchanged `count()` → `force_login` → POST X again asserts same `pk`/`numero_registro`, `count()==1`).
- [x] 2.14 GREEN: confirm 2.13 passes against 2.9's implementation; REFACTOR `iniciar_reporte` for clarity if needed.

## Phase 3: Upload Queue — Shared Dexie Schema + Fetch Submit

- [x] 3.1 Create `reportes/static/reportes/offline-db.js` with the single `version(2).stores({ borradores: "[reporteId+seccionId], reporteId, estado", nuevos: "codigoTipo" })` declaration (D5).
- [x] 3.2 Add `<script src="{% static 'reportes/offline-db.js' %}">` before `paso-offline.js` in `reportes/templates/reportes/paso.html`.
- [x] 3.3 Rewrite `paso-offline.js` submit handler: replace `form.submit()` with `fetch(form.action, {method:"POST", body:new FormData(form), credentials:"same-origin", redirect:"follow"})`.
- [x] 3.4 Implement outcome branching: `response.ok`/`response.redirected` → delete Dexie row, `location.assign(response.url)`; final URL `/login/` → `estado:"fallo"`, `ultimoError:"sesion_expirada"`; HTTP >= 400 → `estado:"fallo"`, `intentos++`; network error/`!navigator.onLine` → `estado:"pendiente"`, `intentos++`.
- [x] 3.5 Add `pendiente`/`fallo` state fields (`intentos`, `ultimoError`) to the Dexie draft row per the state machine table in design.md.
- [x] 3.6 Render inline retry banner via `form.insertAdjacentElement("beforebegin", …)` (mirrors #9's restore prompt) showing attempt count and a "Reintentar" button.
- [x] 3.7 Wire "Reintentar" to re-serialize the *current* form and re-run the fetch submit (step 3.3), transitioning back to `enviando`.
- [x] 3.8 Update `reconciliar()` to restore `pendiente`/`fallo` rows on page load and re-render the banner with existing values.

## Phase 4: Manual Verification (No Automated JS Coverage — Documented Limitation)

- [ ] 4.1 DevTools script step 1: fetch submit path — single `fetch` POST then `document` GET of next step; `borradores` row for previous step is gone.
- [ ] 4.2 DevTools script step 2-4: Network ▸ Offline submit → `pendiente` banner + `intentos:1`; Reintentar while offline → `intentos:2`; Reintentar after reconnect → success, row deleted.
- [ ] 4.3 DevTools script step 5: stop dev server → `fallo` state; restart, Reintentar → success.
- [ ] 4.4 DevTools script step 6: clear `sessionid` cookie mid-draft, submit → final URL `/login/`, row `fallo` with `valores` intact; re-login → banner restores; Reintentar succeeds.
- [ ] 4.5 DevTools script step 7: inject a `data-nuevo-reporte` form, confirm `nuevos[codigoTipo].idLocal` persists across a failed POST and a page reload, and a fresh UUID is generated only after success clears the row.
- [ ] 4.6 DevTools script step 8: double-click start under Slow 3G throttling → exactly one `Reporte` row in Django admin, one `numero_registro`.

## Phase 5: `nuevo-reporte.js` (Forward-Looking Infra for #12)

- [ ] 5.1 Create `reportes/static/reportes/nuevo-reporte.js`: on `DOMContentLoaded`, query `form[data-nuevo-reporte][data-codigo-tipo]`; no-op (`if (!form) return;`) when absent, mirroring `paso-offline.js`'s defensive opening.
- [ ] 5.2 Implement `crypto.randomUUID()` generation persisted to `Dexie.nuevos[codigoTipo]` BEFORE the first POST, reusing the stored UUID on subsequent loads/retries.
- [ ] 5.3 Inject a hidden `<input type="hidden" name="id_local">` populated from the persisted UUID before submit.
- [ ] 5.4 On `response.redirected` success, delete the `Dexie.nuevos[codigoTipo]` row and `location.assign(response.url)`.
- [ ] 5.5 Document in code comments that this ships with no host template (D7) and is verified only via an injected test form until #12 lands.

## Phase 6: Cleanup / Documentation

- [ ] 6.1 Update `openspec/changes/sincronizacion-numero-registro/design.md` Open Questions: confirm Postgres ≥13 (already verified — gen_random_uuid safe, mark resolved).
- [ ] 6.2 Add a short README/comment note in `reportes/static/reportes/offline-db.js` explaining the shared schema contract for future scripts.
- [ ] 6.3 Run full `pytest reportes/` suite and confirm no regressions in existing `test_post_nuevo_crea_un_reporte` and other pre-existing tests.

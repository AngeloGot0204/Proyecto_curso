# Apply Progress: Sincronización y asignación de número de registro

**PR scope**: PR 1 of 3 — `tasks.md` Phase 1 (migration) + Phase 2 (server idempotency). Chain strategy: `stacked-to-main`. Client upload-queue rework (Phase 3/4) and `nuevo-reporte.js` (Phase 5) are explicitly OUT of scope for this apply batch (PR 2/3).

## Completed Tasks

### Phase 1: Server Migration (Foundation) — all complete
- [x] 1.1 `RunSQL` sequence `reportes_numero_registro_seq` (forward + reverse SQL)
- [x] 1.2 `AddField id_local` — `UUIDField(unique=True, editable=False, db_default=Func(function="gen_random_uuid"))`
- [x] 1.3 `AddField numero_registro` — `BigIntegerField(unique=True, editable=False, db_default=Func(Value("reportes_numero_registro_seq"), function="nextval"))`, ordered after `id_local`
- [x] 1.4 `reportes/models.py::Reporte` updated with matching field declarations
- [x] 1.5 `migrate reportes` (forward) and `migrate reportes 0004` (reverse) both confirmed clean against the real Postgres 18.6 (Neon) database, then re-applied forward to leave the DB in final state

### Phase 2: Server-Side Idempotency (TDD) — all complete
- [x] 2.1-2.5 RED: model-level tests for `numero_registro`/`id_local` DB-default behavior
- [x] 2.6 GREEN: confirmed passing against Phase 1 migration/model (DB-level, no Python code needed)
- [x] 2.7-2.8 RED: view-level idempotency/validation tests (`iniciar_reporte`)
- [x] 2.9 GREEN: rewrote `reportes/views.py::iniciar_reporte` — `id_local` parsed from POST (fallback `uuid.uuid4()`), `get_or_create(id_local=..., creador=request.user, defaults={...})` inside `transaction.atomic()`, `IntegrityError` → 400, `tipo_id` mismatch → 400
- [x] 2.10 GREEN: all Phase 2 tests pass
- [x] 2.11-2.12 RED/GREEN: `test_paso_post_redirect_es_seguible` added to `test_views.py`, passes unchanged (documents existing redirect contract)
- [x] 2.13-2.14 RED/GREEN: `test_sesion_expirada_no_rompe_idempotencia` passes against 2.9's implementation; no further refactor needed — code is already clear

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `reportes/migrations/0005_id_local_numero_registro.py` | Created | `RunSQL` sequence + two `AddField` ops, in design-mandated order |
| `reportes/models.py` | Modified | Added `id_local` (UUIDField) and `numero_registro` (BigIntegerField) to `Reporte`, both with `db_default` |
| `reportes/views.py` | Modified | `iniciar_reporte` rewritten to idempotent `get_or_create` per design's Interfaces/Contracts |
| `reportes/tests/test_idempotencia.py` | Created | 12 tests: scenarios 1-10, 12 (model + view level) |
| `reportes/tests/test_views.py` | Modified | Added `test_paso_post_redirect_es_seguible` (scenario 11) |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.4 | N/A (migration/model) | — | N/A (new fields) | N/A | ✅ Verified via `migrate` + full suite | N/A | N/A |
| 2.1 | `test_idempotencia.py::test_create_asigna_numero_registro_sin_refresh` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.2 | `test_idempotencia.py::test_numero_registro_avanza_por_secuencia` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.3 | `test_idempotencia.py::test_numero_registro_es_unico` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.4 | `test_idempotencia.py::test_id_local_unico_a_nivel_bd` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.5 | `test_idempotencia.py::test_id_local_por_defecto_es_distinto_por_fila` | Integration | N/A (new file) | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.7 | `test_idempotencia.py::test_post_nuevo_repetido_mismo_id_local_no_duplica` | Integration | ✅ 115/115 (baseline before view rewrite) | ✅ Written | ✅ Passed | ✅ Covered by 2.8's four companion scenarios | ➖ None needed |
| 2.8 | `test_idempotencia.py::{test_post_nuevo_sin_id_local_sigue_funcionando, test_id_local_invalido_devuelve_400, test_id_local_de_otro_usuario_devuelve_400, test_id_local_de_otro_tipo_devuelve_400}` | Integration | ✅ (same baseline) | ✅ Written | ✅ Passed | ✅ 4 distinct code paths (no-id_local, invalid, other-user, other-tipo) | ➖ None needed |
| 2.11 | `test_views.py::test_paso_post_redirect_es_seguible` | Integration | ✅ (existing `paso` tests unaffected) | ✅ Written | ✅ Passed | ➖ Single scenario (documents existing contract) | ➖ None needed |
| 2.13 | `test_idempotencia.py::test_sesion_expirada_no_rompe_idempotencia` | Integration | ✅ (same baseline) | ✅ Written | ✅ Passed | ➖ Single end-to-end scenario (3-phase: create, expired retry, re-login retry) | ✅ Reviewed `iniciar_reporte` — already minimal/clear, no refactor needed |

### Test Summary
- **Total tests written**: 13 (12 in `test_idempotencia.py` + 1 in `test_views.py`)
- **Total tests passing**: 13/13 (this batch); 128/128 full `reportes/` suite
- **Layers used**: Integration (13, Django test client + real Postgres test DB via `--reuse-db`)
- **Approval tests** (refactoring): None — `iniciar_reporte` was rewritten, not behavior-preserving-refactored (design explicitly changes create → get_or_create semantics; the 4 backwards-compatibility scenarios in 2.8/2.11 serve the same protective purpose as approval tests would)
- **Pure functions created**: 0 (view logic; `get_or_create` + `IntegrityError` handling requires DB access by nature)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_idempotencia.py reportes/tests/test_views.py -k "id_local or numero_registro or redirect_es_seguible"` — all new/targeted tests pass (verified as part of full-suite run below; the full suite is the authoritative confirmation since Neon DB round-trips make isolated re-runs redundant with the just-completed full run) |
| Runtime harness command/scenario and exact result | `./.venv/Scripts/python.exe -m pytest reportes/ -q` against real Postgres 18.6 (Neon, `test_reportes_dev`) — **128 passed in 466.45s (0:07:46)**, 0 failed. Also ran `manage.py migrate reportes --skip-checks` (forward, OK) then `manage.py migrate reportes 0004 --skip-checks` (reverse, OK) then re-applied forward — both directions clean against the real dev DB. |
| Rollback boundary | `git checkout -- reportes/models.py reportes/views.py reportes/tests/test_views.py`, `rm reportes/migrations/0005_id_local_numero_registro.py reportes/tests/test_idempotencia.py`, then `manage.py migrate reportes 0004` if the migration was applied to a shared DB. No other file in this PR depends on `id_local`/`numero_registro` yet (Phase 3-5 client work is out of scope for this PR). |

## Deviations from Design

None — implementation matches design.md exactly, including field types, `db_default` expressions, migration operation ordering, and the `iniciar_reporte` interface contract pseudocode (design's "Interfaces / Contracts" section maps almost verbatim to the final `views.py` code).

One clarification made during implementation: design's Testing Strategy leaves scenario 12 (`test_sesion_expirada_no_rompe_idempotencia`)'s file unspecified beyond "unless noted" (only scenario 11 explicitly names `test_views.py`). Placed it in `test_idempotencia.py`, consistent with the default rule and with tasks.md 2.13 grouping it under the same file as the rest of Phase 2's idempotency tests.

## Issues Found

- **Pre-existing, unrelated environment issue**: `manage.py` (any subcommand, including plain `migrate`) currently fails Django's system checks with `4_0.E001: CSRF_TRUSTED_ORIGINS setting must start with a scheme`, due to a misconfigured `.env`/`.env.local` value unrelated to this change. Worked around locally with `--skip-checks` to verify the migration; `pytest-django` is unaffected because it does not run Django's full system-check suite. This is out of scope for this PR but should be flagged to the user/maintainer — worth a follow-up fix (correct `CSRF_TRUSTED_ORIGINS` to include a scheme, e.g. `https://...`).
- Two early full-suite test runs produced spurious `psycopg.errors.DeadlockDetected` failures on `tipos_reporte_tipodereporte_codigo_key` — root-caused to two concurrent `pytest` invocations (my own background-command overlap while diagnosing a slow first run against the remote Neon DB) racing on the same reused test database. Not a code defect. A clean, single, non-concurrent full-suite run confirmed **128/128 passing** with zero failures — this is the run recorded above and in this file's Work Unit Evidence.

## Remaining Tasks (out of scope for this PR — PR 2/3)

- [ ] Phase 3: Upload Queue — `offline-db.js`, fetch-based `paso-offline.js` rewrite, retry banner (PR 2)
- [ ] Phase 4: Manual Verification (DevTools scripts) (PR 2)
- [ ] Phase 5: `nuevo-reporte.js` forward-looking infra (PR 3)
- [ ] Phase 6: Cleanup/Documentation (6.1 design.md Open Question resolution, 6.2 offline-db.js README note, 6.3 final full-suite confirmation) — 6.3 is effectively already satisfied by this PR's 128/128 run, but formally belongs to whichever PR lands last per the original task grouping.

## Workload / PR Boundary

- Mode: stacked PR slice (chain strategy: `stacked-to-main`)
- Current work unit: Unit 1 — "Sequence-backed `id_local`/`numero_registro` + idempotent `iniciar_reporte`" (PR 1 of 3)
- Boundary: starts from the pre-existing `Reporte` model (no `id_local`/`numero_registro`) and `iniciar_reporte`'s bare `.create()`; ends with the full migration + idempotent view + 13 passing tests, fully independent of any client-side (JS) changes in PR 2/3
- Estimated review budget impact: migration (~48 lines) + models.py (+18 lines) + views.py (+~35 net lines changed) + 2 test files (~230 lines, mostly new tests) ≈ 330 changed lines — within the 400-line budget for this slice alone (the original ~550-650 estimate covered all 3 PRs combined)

## Status

18/18 assigned tasks (Phase 1 + Phase 2) complete. Ready for `sdd-verify`, or for `sdd-apply` to continue with PR 2 (Phase 3/4) in a later batch.

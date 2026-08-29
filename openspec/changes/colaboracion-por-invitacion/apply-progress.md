# Apply Progress: Colaboración por invitación y edición abierta

## Scope of this batch (cumulative — PR 1 + PR 2 + PR 3)

- PR 1 (per orchestrator instruction: already merged to main): Phase 1 — Foundation (models + migration 0004 + `permisos.py`).
- PR 2 (per orchestrator instruction: already merged to main; `tasks.md` Phase 2 checkboxes were already `[x]` on entry to this batch): Phase 2 — `guardar_valor` refactor (audit trail + FIFO-30).
- **PR 3 (this batch)**: Phase 3 — widen `paso`/`revision` access, narrow `generar`
  access, via `views.py::_reporte_accesible` shim using `permisos.tiene_acceso`.
  `cerrar_reporte` stays creator-only, unchanged.
- Phase 4 (invite/participantes views) is explicitly NOT implemented in this batch —
  reserved for PR 4.

## Mode

Strict TDD (RED → GREEN → REFACTOR), enforced per `openspec/config.yaml` (`strict_tdd: true`).

## Completed Tasks (Phase 1)

- [x] 1.1 (RED) `reportes/tests/test_permisos.py` — 4 scenarios (creator, invited participant, stranger, anonymous)
- [x] 1.2 `ParticipacionEnReporte` model in `reportes/models.py`
- [x] 1.3 `CambioDeValor` model in `reportes/models.py`
- [x] 1.4 `Generacion` docstring fixed ("any authenticated user" → "creator or invited participant")
- [x] 1.5 Migration `reportes/migrations/0004_participacion_cambiodevalor.py` (2× CreateModel with inline constraints; deps `0003_vistobueno_generacion` + `swappable_dependency(AUTH_USER_MODEL)`)
- [x] 1.6 (GREEN) `reportes/permisos.py::tiene_acceso(reporte, usuario) -> bool`
- [x] 1.7 (REFACTOR) Confirmed `permisos.py` imports only `reportes.models` — no HTTP/Django-view imports
- [x] 1.8 `participacion_factory(db, usuario_factory)` fixture added to `reportes/tests/conftest.py`

## Completed Tasks (Phase 2 — carried over, per orchestrator: already merged to main)

- [x] 2.1–2.13 `guardar_valor` audit trail + FIFO-30 refactor in `reportes/valores.py` and `reportes/tests/test_valores.py` (see PR 2 apply-progress; `tasks.md` Phase 2 already marked complete on entry to this batch).

## Completed Tasks (Phase 3 — this batch)

- [x] 3.1 (RED) `test_paso_participante_invitado_accede` — invited participant B requests `paso` → 200
- [x] 3.2 (RED) `test_paso_no_invitado_autenticado_da_404` — non-invited authenticated user C requests `paso` → 404
- [x] 3.3 (RED) `test_get_revision_participante_invitado_accede` — invited participant B requests `revision` → 200
- [x] 3.4 (RED) `test_get_revision_no_invitado_da_404` — non-invited user C requests `revision` → 404
- [x] 3.5 (RED) `test_generar_participante_invitado_es_exitoso` — invited participant B POSTs `generar` → 200, `Generacion.usuario == B`
- [x] 3.6 (RED) `test_generar_no_participante_devuelve_404` — non-participant C POSTs `generar` → 404, no `Generacion` row
- [x] 3.7 `test_generar_no_creador_tambien_puede_generar` removed, replaced by 3.5 + 3.6 (design's identified reversal — split, not silently deleted)
- [x] 3.8 Confirmed `test_paso_reporte_de_otro_usuario_da_404` and `test_get_revision_reporte_de_otro_usuario_da_404` still pass unchanged (stranger stays neither creator nor participant)
- [x] 3.9 (RED) `test_cerrar_reporte_participante_invitado_devuelve_404` — invited non-creator B POSTs `cerrar_reporte` → 404, no `VistoBueno` created
- [x] 3.10 (GREEN) `_reporte_accesible(reporte_id, usuario)` shim added to `reportes/views.py` per design D1
- [x] 3.11 (GREEN) `paso` view switched to `_reporte_accesible`
- [x] 3.12 (GREEN) `revision` view switched to `_reporte_accesible`
- [x] 3.13 (GREEN) `generar` view switched to `_reporte_accesible` (narrowed from any-authenticated-user)
- [x] 3.14 Confirmed `cerrar_reporte` keeps its strict `get_object_or_404(Reporte, pk=…, creador=request.user)`, unchanged, does not use `_reporte_accesible`
- [x] 3.15 `reportes/views.py` module docstring updated (creator-only D9 language → creator-or-participant, with the `cerrar_reporte`/`invitar` carve-out noted)
- [x] 3.16 `sesion_de_invitado` fixture added, local to `test_views.py`, mirrors `sesion_de_creador`
- [x] 3.17 Ran all Phase 3 tests plus full `reportes/` suite and full project suite — all pass (see Work Unit Evidence)

## Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `reportes/models.py` | Modified | Added `ParticipacionEnReporte` (UniqueConstraint reporte+usuario) and `CambioDeValor` models; fixed `Generacion` docstring |
| `reportes/migrations/0004_participacion_cambiodevalor.py` | Created | `makemigrations reportes --skip-checks`, then renamed from Django's default alphabetical name to match design's file name; content unchanged (2× `CreateModel`, constraint declared inline via model `Meta.constraints`) |
| `reportes/permisos.py` | Created | `tiene_acceso(reporte, usuario) -> bool` — pure predicate, mirrors `valores.py`/`validacion.py` |
| `reportes/tests/test_permisos.py` | Created | 4 tests: creator, invited participant, stranger, anonymous |
| `reportes/tests/conftest.py` | Modified | Added `participacion_factory` fixture |
| `reportes/views.py` | Modified (PR 3) | Added `_reporte_accesible(reporte_id, usuario)` shim; switched `paso`, `revision`, `generar` to it; updated module + view docstrings (D9 → creator-or-participant); `cerrar_reporte` left untouched |
| `reportes/tests/test_views.py` | Modified (PR 3) | Added `sesion_de_invitado` fixture; added `test_paso_participante_invitado_accede`, `test_paso_no_invitado_autenticado_da_404`, `test_get_revision_participante_invitado_accede`, `test_get_revision_no_invitado_da_404`, `test_cerrar_reporte_participante_invitado_devuelve_404`; replaced `test_generar_no_creador_tambien_puede_generar` with `test_generar_participante_invitado_es_exitoso` + `test_generar_no_participante_devuelve_404` |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1–1.8 | `reportes/tests/test_permisos.py` | Unit (Django ORM) | ✅ 8/8 (`test_models.py` baseline, pre-change) | ✅ Written — failed with `ModuleNotFoundError: No module named 'reportes.permisos'` (right reason: production code absent) | ✅ Passed — 4/4 after `permisos.py` + `participacion_factory` created | ✅ 4 cases (creator no-row, invited participant, stranger, anonymous) covering all spec scenarios for this task | ✅ Clean — no HTTP import leak, predicate stays pure |
| 3.1–3.4, 3.9 | `reportes/tests/test_views.py` | Integration (Django test client + Postgres) | ✅ 34/34 (`test_views.py` full-file baseline, pre-change) | ✅ Written — ran with `-k "invitado or no_participante or participante"` before implementing the shim: `test_paso_participante_invitado_accede` and `test_get_revision_participante_invitado_accede` failed `404 == 200` (right reason: `paso`/`revision` still creator-only); `test_paso_no_invitado_autenticado_da_404`, `test_get_revision_no_invitado_da_404`, and `test_cerrar_reporte_participante_invitado_devuelve_404` passed trivially against the unmodified creator-only views (a non-invited/invited-but-non-creator user was already 404'd by the old `creador=request.user` filter — correct behavior pre-existed for those three scenarios, so only the widen-side (200-for-participant) assertions were true RED) | ✅ Passed — same filtered run after `_reporte_accesible` added and `paso`/`revision` switched: both previously-red assertions now pass, the three trivial-pass assertions remain passing (regression-proof for `cerrar_reporte`'s non-widening and the stranger-404 cases) | ✅ Multiple scenarios per requirement: creator-or-participant success case AND non-invited-user 404 case for both `paso` and `revision`, plus the `cerrar_reporte` non-widening case | ➖ None needed — shim is a 4-line pure fetch-check-404 function, no duplication to remove |
| 3.5–3.7 | `reportes/tests/test_views.py` | Integration | ✅ (same baseline) | ✅ Written — `test_generar_no_participante_devuelve_404` failed `200 == 404` (right reason: `generar` had no access restriction yet); `test_generar_participante_invitado_es_exitoso` passed trivially pre-change (any authenticated user could already generate) — confirms the split test correctly isolates the ADDED restriction from the PRESERVED non-creator-can-generate behavior | ✅ Passed — both green after `generar` switched to `_reporte_accesible` | ✅ 2 cases: invited-participant-succeeds vs. non-participant-denied, replacing the single reversed test per design's explicit instruction | ➖ None needed |

### Test Summary
- **Total tests written**: 4 (`test_permisos.py`, PR 1) + 8 (`test_views.py`, PR 3: `test_paso_participante_invitado_accede`, `test_paso_no_invitado_autenticado_da_404`, `test_get_revision_participante_invitado_accede`, `test_get_revision_no_invitado_da_404`, `test_generar_participante_invitado_es_exitoso`, `test_generar_no_participante_devuelve_404`, `test_cerrar_reporte_participante_invitado_devuelve_404`, plus the `sesion_de_invitado` fixture) = 12 new tests total across both batches
- **Total tests passing**: 4/4 `test_permisos.py`; 40/40 `test_views.py` (34 pre-existing + 6 new, one net test removed via the 3.5/3.6 split of the reversed test); 101/101 full `reportes/` app suite; 242/242 full project suite (see Work Unit Evidence)
- **Layers used**: Unit (4, `test_permisos.py`), Integration (36, `test_views.py` — Django test client + real Postgres via `--reuse-db`)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Pure functions created**: 2 total (`tiene_acceso` in PR 1; `_reporte_accesible` in PR 3 — HTTP-adjacent, not pure, but a thin single-purpose fetch/check shim matching the existing `_seccion_por_id`/`_url_paso` pattern)

## Work Unit Evidence (PR 3 — this batch)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_views.py -q -k "paso or revision or generar or cerrar"` → 36 passed, 4 deselected in 175.16s |
| Runtime harness command/scenario and exact result | `pytest reportes/tests/test_views.py reportes/tests/test_permisos.py -q` → 44 passed in 194.01s; `pytest reportes/ -q` (full app suite) → 101 passed in 357.22s; `pytest -q` (full project suite, all apps) → 242 passed in 481.76s |
| Rollback boundary | Revert the access-check hunks in `reportes/views.py` only (`_reporte_accesible` addition, the `paso`/`revision`/`generar` one-line swaps to it, and the docstring updates) plus the corresponding test additions/replacement in `reportes/tests/test_views.py` (`sesion_de_invitado` fixture, the 7 new/replaced test functions). `reportes/models.py`, `reportes/permisos.py`, and `reportes/valores.py` are untouched by this batch — fully isolated, self-contained revert that does not affect PR 1/PR 2 work. |

## Work Unit Evidence (PR 1)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest reportes/tests/test_permisos.py -v` → 4 passed in 14.77s |
| Runtime harness command/scenario and exact result | `pytest reportes/ -q` (full app suite, real Postgres via `--reuse-db`) → 87 passed in 209.41s |
| Rollback boundary | Revert `reportes/migrations/0004_participacion_cambiodevalor.py` (or `manage.py migrate reportes 0003`), `reportes/permisos.py`, `reportes/tests/test_permisos.py`, and the `ParticipacionEnReporte`/`CambioDeValor` additions to `reportes/models.py`; revert the `participacion_factory` fixture and `Generacion` docstring hunk in `conftest.py`/`models.py`. No other file in the repo imports `permisos.py` or the new models yet — fully isolated, self-contained revert. |

## Deviations from Design

- Migration filename: Django's `makemigrations` auto-named the file
  `0004_cambiodevalor_participacionenreporte.py` (alphabetical model order).
  Renamed to `0004_participacion_cambiodevalor.py` to match design/tasks —
  content (operations, dependencies) is unaffected by the rename.
- Design's D2 prose mentions `AddConstraint` as a separate migration
  operation; Django 5.2 instead emits the `UniqueConstraint` inline inside
  `CreateModel`'s `options={'constraints': [...]}` since the constrained
  model is newly created in the same migration (no separate ALTER TABLE
  needed). Semantically identical — same DB-level constraint, same
  `makemigrations --check` clean result.

## Issues Found

None.

## Remaining Tasks (Phase 4–5 — NOT this batch)

- [ ] Phase 4: Invite action and participantes view (tasks 4.1–4.16)
- [ ] Phase 5: Full suite verification + `makemigrations --check` (tasks 5.1–5.3) — 5.1 already confirmed in this batch (242/242 full project suite passing) as a byproduct; 5.2 was already confirmed clean in PR 1; 5.3 (threat-matrix N/A confirmation) belongs to the final PR sign-off

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main per orchestrator instruction)
- Current work unit: Unit 3 — "Widen `paso`/`revision`, narrow `generar` via `_reporte_accesible`" (per tasks.md Suggested Work Units table)
- Boundary: starts from the state after PR 1 + PR 2 (models, `permisos.py`, `guardar_valor` audit/FIFO all in place) and ends at task 3.17 — no touch to `models.py`, `permisos.py`, `valores.py`, `urls.py`, or templates; PR 4 (invite/participantes) is untouched
- Estimated review budget impact: 2 files changed (`reportes/views.py`, `reportes/tests/test_views.py`), well under the 400-line budget — `git diff --stat` shows 68 lines changed in `views.py` and 114 in `test_views.py` (source diff only; `tasks.md` checkbox updates are process bookkeeping, not reviewed code)

## Key Learnings

1. Django 5.2's `makemigrations` inlines a newly-created model's `UniqueConstraint` into `CreateModel`'s `options`, not a separate `AddConstraint` op, when the constrained table is new in the same migration.
2. `manage.py makemigrations` requires `--skip-checks` in this environment because `.env`'s `DJANGO_CSRF_TRUSTED_ORIGINS` placeholder value fails Django 4.0's scheme-prefix system check — unrelated to this change, pre-existing local dev config gap, `pytest-django` does not hit the same check path.
3. `tiene_acceso`'s defensive `is_authenticated` branch needed `django.contrib.auth.models.AnonymousUser` in the test, not a plain `None`, to exercise the real attribute the production code reads.
4. Widening a creator-only 404 to creator-or-participant only produces true RED on the "widen" side of each pair (participant-succeeds); the "still-denied" side (stranger/non-invited/non-creator-participant) already passed pre-change since the old strict `creador=request.user` filter already rejected them — both sides still need explicit test coverage as regression proof, even the trivially-passing one.
5. `reporte_factory()`'s default `creador=usuario_factory()` collides on `Usuario.username` with any other fixture in the same test that also calls `usuario_factory()`/`cliente_autenticado` with default args (both default to `"usuario_test"`) — always pass an explicit `username` when a test combines `reporte_factory` with `cliente_autenticado` or a second `usuario_factory()` call, mirroring the existing `test_paso_reporte_de_otro_usuario_da_404` pattern.

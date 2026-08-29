# Apply Progress: Colaboración por invitación y edición abierta

## Scope of this batch

PR 1 of 4 — Phase 1 only (Foundation: models + migration 0004 + `permisos.py`).
Phases 2–4 (guardar_valor refactor, access widening, invite/participantes views) are
explicitly NOT implemented in this batch — reserved for PR 2/3/4.

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

## Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `reportes/models.py` | Modified | Added `ParticipacionEnReporte` (UniqueConstraint reporte+usuario) and `CambioDeValor` models; fixed `Generacion` docstring |
| `reportes/migrations/0004_participacion_cambiodevalor.py` | Created | `makemigrations reportes --skip-checks`, then renamed from Django's default alphabetical name to match design's file name; content unchanged (2× `CreateModel`, constraint declared inline via model `Meta.constraints`) |
| `reportes/permisos.py` | Created | `tiene_acceso(reporte, usuario) -> bool` — pure predicate, mirrors `valores.py`/`validacion.py` |
| `reportes/tests/test_permisos.py` | Created | 4 tests: creator, invited participant, stranger, anonymous |
| `reportes/tests/conftest.py` | Modified | Added `participacion_factory` fixture |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1–1.8 | `reportes/tests/test_permisos.py` | Unit (Django ORM) | ✅ 8/8 (`test_models.py` baseline, pre-change) | ✅ Written — failed with `ModuleNotFoundError: No module named 'reportes.permisos'` (right reason: production code absent) | ✅ Passed — 4/4 after `permisos.py` + `participacion_factory` created | ✅ 4 cases (creator no-row, invited participant, stranger, anonymous) covering all spec scenarios for this task | ✅ Clean — no HTTP import leak, predicate stays pure |

### Test Summary
- **Total tests written**: 4 (`test_permisos.py`)
- **Total tests passing**: 4/4 focused; 87/87 full `reportes/` suite (see Work Unit Evidence)
- **Layers used**: Unit (4, DB-backed via `pytest.mark.django_db`)
- **Approval tests** (refactoring): None — no refactoring tasks in this batch
- **Pure functions created**: 1 (`tiene_acceso`)

## Work Unit Evidence

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

## Remaining Tasks (Phases 2–5 — NOT this batch)

- [ ] Phase 2: `guardar_valor` refactor — audit trail + FIFO-30 (tasks 2.1–2.13)
- [ ] Phase 3: Widen `paso`/`revision`, narrow `generar` via `_reporte_accesible` (tasks 3.1–3.17)
- [ ] Phase 4: Invite action and participantes view (tasks 4.1–4.16)
- [ ] Phase 5: Full suite verification + `makemigrations --check` (tasks 5.1–5.3) — 5.2 already confirmed clean in this batch as a byproduct; 5.1/5.3 belong to the final PR

## Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main per orchestrator instruction)
- Current work unit: Unit 1 — "Migration 0004 + `permisos.py::tiene_acceso`" (per tasks.md Suggested Work Units table)
- Boundary: starts from zero (first apply run for this change) and ends at task 1.8 — no touch to `valores.py`, `views.py`, `urls.py`, or templates
- Estimated review budget impact: ~5 files changed (2 new, 3 modified), well under the 400-line budget; models.py addition ~60 lines, migration ~46 lines, permisos.py ~19 lines, test_permisos.py ~50 lines, conftest.py fixture ~14 lines — roughly 190 changed lines, matching the tasks.md unit-1 estimate

## Key Learnings

1. Django 5.2's `makemigrations` inlines a newly-created model's `UniqueConstraint` into `CreateModel`'s `options`, not a separate `AddConstraint` op, when the constrained table is new in the same migration.
2. `manage.py makemigrations` requires `--skip-checks` in this environment because `.env`'s `DJANGO_CSRF_TRUSTED_ORIGINS` placeholder value fails Django 4.0's scheme-prefix system check — unrelated to this change, pre-existing local dev config gap, `pytest-django` does not hit the same check path.
3. `tiene_acceso`'s defensive `is_authenticated` branch needed `django.contrib.auth.models.AnonymousUser` in the test, not a plain `None`, to exercise the real attribute the production code reads.

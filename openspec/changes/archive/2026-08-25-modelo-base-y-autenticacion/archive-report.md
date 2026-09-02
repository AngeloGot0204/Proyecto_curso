# Archive Report: Base Model and Authentication (backlog #1)

> Engram: `sdd/modelo-base-y-autenticacion/archive-report` (observation 47)

**Archival Date**: 2026-08-25

## Status
**PASS WITH WARNINGS → ARCHIVED**

All work complete. No blocking issues. Non-critical residual warnings recorded for future hardening.

## Final Verification (Re-run at Archive Time)

```
.venv/Scripts/pytest.exe -q
17 passed in 29.59s
Exit code: 0

.venv/Scripts/python.exe manage.py check
System check identified no issues (0 silenced).
Exit code: 0

git status
On branch main
nothing to commit, working tree clean
```

## Test Suite
- **Total tests**: 17 passing (exit code 0)
- **Model layer**: 8 tests (strict RED→GREEN)
- **Constraint bypass tests**: 2 tests (WARNING 3 closure, commit eed7016)
- **Auth flow layer**: 7 tests
- **Build**: Django `manage.py check` clean (0 issues, exit code 0)

## Commits
- **602afbc** (root): `feat(usuarios): add custom Usuario model and session authentication` — 46 files, 2840 insertions
- **eed7016**: `test(usuarios): cover usuario_superuser_es_administrador constraint` — added 2 constraint-bypass tests
- **1b9fa85**: `chore: ignore local SDD artifact export under docs/` — added `docs/` to `.gitignore`

## Spec Compliance
- **Requirements**: 6/6 ✅
- **Scenarios**: 13/13 (11 full compliance, 2 partial per spec scope) ✅
- **Blockers**: 0
- **Critical findings**: 0

## Residual Warnings (Non-Critical)

### WARNING 1: Session-lifetime scenarios lack simulated-clock test
Settings assertion only; no freezegun boundary test. Candidate for future hardening session-boundary pass.

### WARNING 2: Phase 6 auth-flow tests authored alongside views
Process deviation (not strict RED-first), but assertion quality verified real. Document for future discipline.

### WARNING 3: usuario_superuser_es_administrador CheckConstraint (**CLOSED**)
Fixed by commit eed7016. Suite: 15 → 17 tests.

## Deliverables
- Django 5.2.17 scaffold with custom `Usuario(AbstractUser)` model
- `rol` field with administrador/usuario choices
- Automatic `is_staff` derivation from `rol` (two-layer enforcement: save() + CheckConstraints)
- Session-based login/logout with 7-day cookie lifetime
- Role-gated `/admin` access
- 17-test verification suite (model + constraint + auth-flow)
- pytest + pytest-django infrastructure with Neon dev database

## Success Criteria Met
- ✅ `migrate` runs clean on Neon dev branch
- ✅ Administrador can log in to `/admin` (is_staff automatic)
- ✅ Usuario can log in to `/login` but not `/admin/`
- ✅ Session persists 7 days (`SESSION_COOKIE_AGE = 604800`)
- ✅ `.env`/`.env.example`/`.gitignore` in place; no secrets committed

## Dependency Notes for Future Changes
- `AUTH_USER_MODEL` is locked to `usuarios.Usuario` — no second custom user model
- App decisions must branch on `user.es_administrador` property, not `is_staff` or `is_superuser`
- Session-lifetime control is Django-guaranteed; offline behavior (items #9/#10) handles draft preservation on expiry
- Neon dev branch is test database for all items; local PostgreSQL can be swapped via `.env` (no code change)

## Living Spec
The delta spec from this change has been merged into the living spec for the usuarios domain: Engram `spec/usuarios` (observation 48).

## Cycle Closure
The SDD cycle for backlog item #1 (modelo-base-y-autenticacion) is **complete and archived**. Ready for the next change.

**Next**: Begin `sdd-propose` for backlog item #2 (Deployment & Production Infrastructure).

# Tasks: Base Model and Authentication (backlog #1)

> Engram: `sdd/modelo-base-y-autenticacion/tasks` (observation 40)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~465 authored (excludes ~121 generated: `manage.py`, `asgi.py`/`wsgi.py`, `apps.py`, `0001_initial.py`) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR A (~321 lines): scaffold + `Usuario` model + `0001_initial` + pytest runner -> PR B (~147 lines): auth views/templates/tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes

> **Resolved.** The user chose a **single PR** with `size:exception`. The split
> below is recorded for reference but is not used; no chain strategy was
> collected. See [06-decisions.md](06-decisions.md).

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| A | Scaffold, `Usuario` model, first migration, pytest runner | PR 1 | `python -m pytest usuarios/tests/test_models.py` | `python manage.py migrate` + `createsuperuser` against Neon dev branch | Delete created files, reset Neon schema (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) — model cannot be deferred, so this unit is not independently revertible without a schema reset |
| B | Auth views, templates, login/logout, role-gated admin | PR 2 | `python -m pytest usuarios/tests/test_login.py` | Manual: log in as each role, hit `/admin/`, POST logout | Delete `usuarios/{views,urls}.py`, 3 templates, revert `config/urls.py` include — no migration involved |

## Phase 1: Git Init & Pre-flight

- [x] 1.1 Verify `git rev-parse --show-toplevel` resolves to the project root before any git command (threat matrix: repo selection).
- [x] 1.2 `git init`; write `.gitignore` (`.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `db.sqlite3`, `.claude/settings.local.json`); stage it before `.env` exists.
- [x] 1.3 `git remote add origin https://github.com/AngeloGot0204/Proyecto_curso.git` — no push.
- [x] 1.4 Verify: `git ls-files .env` returns empty AND `git status --porcelain` shows `.env` untracked (threat matrix: commit state, executable assertion).

## Phase 2: Scaffold, Env, Deps

- [x] 2.1 `python -m venv .venv`; write `requirements.txt` + `requirements-dev.txt` per design decision 2; `pip install -r requirements-dev.txt`.
- [x] 2.2 `django-admin startproject config .`; `python manage.py startapp usuarios`.
- [x] 2.3 Write `.env.example` (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`); create local gitignored `.env` with real Neon dev values.
- [x] 2.4 Edit `config/settings.py`: dotenv load, `require_env()`, `dj_database_url`, `INSTALLED_APPS += usuarios`, **`AUTH_USER_MODEL = "usuarios.Usuario"`**, `TEMPLATES["DIRS"]`, `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`, `SESSION_COOKIE_AGE = 604800`.
- [x] 2.5 Edit `config/urls.py`: `admin/` route only (usuarios include added Phase 5).
- [x] 2.6 Write `pytest.ini` (`DJANGO_SETTINGS_MODULE`, `--reuse-db`, `python_files`, `norecursedirs`); verify `python -m pytest --collect-only` runs clean — runner must exist before Phase 3 tests.

## Phase 3: Usuario Model — RED

- [x] 3.1 Write `usuarios/tests/conftest.py` + `test_models.py` (failing, no model yet): default `rol=usuario` (spec: Usuario model provides rol field); `full_clean()` rejects invalid `rol` (rol rejects invalid values); `rol=administrador` sets `is_staff=True` (Setting rol to administrador grants admin access automatically); downgrade revokes `is_staff` (Reverting rol to usuario does not silently preserve staff access); unchanged `administrador` save preserves `is_staff`, never touches `is_superuser` (Existing manual is_staff grant is not silently overridden); `QuerySet.update()` on both `CheckConstraint`s raises `IntegrityError`, each wrapped in its own `transaction.atomic()`.

## Phase 4: Usuario Model — GREEN

- [x] 4.1 Write `usuarios/models.py`: `Rol(TextChoices)`, `Usuario(AbstractUser)`, `save()` override (superuser ⇒ `rol=administrador`; `is_staff` derived), `Meta.constraints` (`usuario_rol_implica_is_staff`, `usuario_superuser_es_administrador`), `es_administrador` property.
- [x] 4.2 Pre-flight: confirm `usuarios/migrations/` has only `__init__.py` and the Neon dev branch has no pre-existing tables (reset schema if not).
- [x] 4.3 `python manage.py makemigrations usuarios` -> `0001_initial.py`; inspect it targets `usuarios_usuario`, not `auth_user`.
- [x] 4.4 **One-shot gate**: `python manage.py migrate`. If this ever runs before 4.1–4.3 complete, the only recovery is resetting the Neon branch (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`), not deleting local files.
- [x] 4.5 `python manage.py createsuperuser`; verify `rol=administrador` and `is_staff=True` with no manual fix (spec: Django-admin access gated by role).
- [x] 4.6 Write `usuarios/admin.py`: `UsuarioAdmin(UserAdmin)`, `rol` in fieldsets, `is_staff` in `readonly_fields`.
- [x] 4.7 `python -m pytest --create-db`; confirm all Phase 3 tests pass.

## Phase 5: Auth Views & Templates

- [x] 5.1 Write `usuarios/views.py`: minimal `@login_required` `inicio` view rendering `templates/inicio.html` (scope guard: no report logic; item #12 replaces it).
- [x] 5.2 Write `usuarios/urls.py`: `login/` -> `LoginView`, `logout/` -> `LogoutView`, `""` -> `inicio`.
- [x] 5.3 Edit `config/urls.py`: add `include("usuarios.urls")` at `""`.
- [x] 5.4 Write `templates/base.html` (minimal blocks); `templates/registration/login.html` (`csrf_token`, `form.non_field_errors`, `form.as_p`, submit, static "Solicita tu cuenta al administrador" note); `templates/inicio.html` (username + logout as `<form method="post">` with `{% csrf_token %}` — Django 5 `LogoutView` requires POST, not a link).

## Phase 6: Auth Flow — RED then GREEN

- [x] 6.1 RED: `usuarios/tests/test_login.py` (all failing): valid login redirects past login (Successful login); wrong password re-renders form, no session (Failed login with wrong credentials); inactive account fails, no session (Login rejected for inactive account); POST logout invalidates session, next protected request redirects to login (Logout ends the session); `rol=administrador` reaches `/admin/` (Administrador user can access Django admin); `rol=usuario` denied `/admin/` (Usuario role is denied Django admin access); `settings.SESSION_COOKIE_AGE == 604800` (Session persists within the 7-day window / expires after 7 days).
- [x] 6.2 GREEN: confirm Phase 5 views/urls/templates satisfy 6.1; run `python -m pytest` — full suite green.

## Phase 7: Wrap-up

- [x] 7.1 Update `sdd/proyecto/testing-capabilities`: runner now exists, command `python -m pytest` (`--create-db` after model changes).
- [x] 7.2 Confirm root planning docs (`PRD.md`, `TECH-DESIGN.md`, etc.) remain tracked as-is in the first commit; no `git push` performed (decision 8 — not authorized).

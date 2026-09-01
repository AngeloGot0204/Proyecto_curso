# Proposal: Base Model and Authentication

> Engram: `sdd/modelo-base-y-autenticacion/proposal` (observation 36)

## Intent

This is the first implementable change for "Generador de Reportes de Campo" — a greenfield project with no code yet. It lays the Django project scaffold and the custom `Usuario` model that every later backlog item (#2–#14) depends on. `AUTH_USER_MODEL` must be correct before the first migration, since swapping it afterward is highly disruptive. Success looks like: an admin-created account can log in via session auth, the role convention (`rol` vs `is_staff`) is fixed and documented, and later items can FK to `Usuario` without rework.

## Scope

### In Scope

- Minimal Django scaffold: `manage.py`, `config/settings.py` (single file, not a package), `config/urls.py`, dependency manifest.
- PostgreSQL via a Neon **development** branch, connection string from `.env` (with `.env.example` and `.gitignore`); enough wiring for `makemigrations`/`migrate` to run.
- `usuarios` app: `Usuario(AbstractUser)` + `rol` (`administrador`/`usuario`), `AUTH_USER_MODEL = "usuarios.Usuario"`, first migration.
- `usuarios/admin.py`: register `Usuario`; enforce `rol == administrador ⇒ is_staff = True` (not manual toggling) — e.g. via `save()` override or a `pre_save` signal, decided in design.
- Login/logout via Django's stock `LoginView`/`LogoutView` + one minimal server-rendered login template (S-01). Username-based login (Django default); admin assigns the username on account creation.
- `SESSION_COOKIE_AGE = 604800` (7 days) per ADR-0005 / RESOLUCION-ADVERSARIAL #10.
- Bootstrap of the very first administrator account.

### Out of Scope

- Offline-tolerant session behavior (ADR-0005's offline half) — items #9, #10.
- Deployment/prod infra: Vercel, prod env vars, Neon prod branch, Vercel Blob — item #2.
- Any report-domain model (`TipoDeReporte`, `Reporte`, `ValorDeReporte`, etc.) — items #3+.
- Custom admin UI for report types (S-14) — item #13.
- Git repository initialization — project is not currently a git repo; recommend doing this as a small prerequisite step at the start of `sdd-apply` for this change (not deferred to #2), since committing scaffold code needs version control from the outset.
- Self-service password reset (email-based `PasswordResetView`) — S-13 password reset is covered by admin setting a new password directly in `django.contrib.admin`, no email backend needed in this change.

## Capabilities

### New Capabilities

- `usuarios`: custom user model with role, session-based auth, login/logout, Django-admin user management.

### Modified Capabilities

None (greenfield).

## Approach

Custom `Usuario(AbstractUser)` with explicit `rol` field (Approach 1 from exploration), `AUTH_USER_MODEL` set before the first migration, registered in `django.contrib.admin`. `is_staff`/`is_superuser` remain Django-admin-access flags; `rol` is the app-level permission flag. The two are kept consistent by enforcing `rol == administrador ⇒ is_staff = True` in code (not manual), documented explicitly so item #13 doesn't guess. Postgres/Neon dev branch is used from day one (not SQLite) because item #10 needs a real DB sequence for report registration numbers, and running two DB engines across dev/prod invites environment-specific bugs — cost accepted: local dev needs network access to Neon.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `manage.py`, `config/settings.py`, `config/urls.py` | New | Django project scaffold |
| `.env`, `.env.example`, `.gitignore` | New | Environment/secrets handling |
| `requirements.txt` | New | Django + `psycopg` + `python-dotenv` (or equivalent) |
| `usuarios/models.py` | New | `Usuario(AbstractUser)` + `rol` |
| `usuarios/admin.py` | New | Admin registration + role/`is_staff` consistency enforcement |
| `usuarios/views.py`, `usuarios/urls.py` | New | Login/logout wiring |
| `templates/usuarios/login.html` | New | S-01 login screen |
| `usuarios/migrations/0001_initial.py` | New (generated) | First migration, `AUTH_USER_MODEL` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `AUTH_USER_MODEL` set incorrectly before first migration | Low (caught by design review) | Set it in settings before running `makemigrations` for the first time; verify no migration exists yet |
| `rol`/`is_staff` drift if not enforced in code | Medium | Enforce in `save()`/signal, document convention for item #13 |
| Local dev requires Neon network access | Medium (workflow friction) | Document `.env` setup in README/design; confirm Neon free-tier dev branch is provisioned before apply |
| No test runner exists yet | Medium | This change is the natural place to introduce pytest + pytest-django; do not assume a runner exists — set it up as part of scaffold |
| Proposal size near 400-line review budget | Medium | Flag for `sdd-tasks` to forecast; consider splitting scaffold vs. `usuarios` app into two review-sized units if needed |

## Rollback Plan

Entire change is additive (new project, no existing code to break). Rollback = delete the created files/migration and drop the Neon dev branch tables (or discard the branch). No production data at risk since prod infra doesn't exist yet (item #2).

## Dependencies

- A Neon account/project with a development branch provisioned, and its connection string available for `.env`. No prod branch needed yet.

## Success Criteria

- [ ] `python manage.py migrate` runs clean against the Neon dev branch with `usuarios.Usuario` as `AUTH_USER_MODEL`.
- [ ] An admin-created user with `rol=administrador` can log in to `/admin` (is_staff enforced automatically).
- [ ] An admin-created user with `rol=usuario` can log in via `/login` but cannot access `/admin`.
- [ ] Session persists for 7 days (`SESSION_COOKIE_AGE`).
- [ ] `.env`/`.env.example`/`.gitignore` in place; no secrets committed.

## Proposal question round

These questions surfaced while drafting scope. All four were answered by the user during the session — see [06-decisions.md](06-decisions.md) for the settled answers.

1. **Bootstrap of the first administrator**: since there's no self-registration, how should the very first `administrador` account be created — `createsuperuser`, a data migration, or a one-off management command?
2. **Git initialization**: should `git init` + first commit happen as a prerequisite step inside this change's `sdd-apply`, or does it belong to a separate, earlier housekeeping step outside SDD?
3. **Test runtime setup**: should pytest + pytest-django be installed and configured as part of this change, given Strict TDD is currently disabled project-wide due to no runner existing?
4. **Review budget split**: this change's estimated size is close to the 400-line budget. Is a single PR acceptable for this foundational scaffold, or should it be split?

## Size Estimate

Rough authored changed-line estimate (additions, greenfield so no deletions): ~320–400 lines across settings, urls, models, admin, views, templates, `.env`/`.gitignore`, and requirements. The generated `0001_initial.py` migration (~40–60 lines) is excluded from the authored-risk count per the review-budget convention but included in snapshot identity. This sits close to the 400-line review budget — `sdd-tasks` should re-forecast precisely and flag chaining if it crosses the threshold.

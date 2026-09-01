# Session Decisions

> Engram: `sdd/modelo-base-y-autenticacion/decisions` (37),
> `sdd/modelo-base-y-autenticacion/delivery` (41),
> `sdd/modelo-base-y-autenticacion/django-version` (42)

Decisions the user confirmed during the SDD session. Later phases treat these as
settled: they are not re-opened or re-litigated.

## Session preflight

| Setting | Value |
|---|---|
| Execution mode | `interactive` |
| Artifact store | `engram` |
| Delivery strategy | `ask-on-risk`, later resolved to `exception-ok` |
| Review budget | 400 changed lines |

## Product and technical decisions

1. **Model**: custom `Usuario(AbstractUser)` with an explicit `rol` field
   (`administrador` / `usuario`); `AUTH_USER_MODEL = "usuarios.Usuario"` set
   before the first migration.
2. **Admin role**: `rol == administrador` implies `is_staff = True`, enforced in
   code, not by manual toggling. One single administrator class. S-13 (account
   creation, password reset, suspension via `is_active`) is served by the stock
   Django admin site; no custom user-admin screen in this change.
3. **Login identifier**: `username` (Django default). No email login, no custom
   auth form for the identifier.
4. **Database**: PostgreSQL from day one via a Neon development branch,
   connection string from `.env`. Not SQLite. Rationale: backlog item #10 needs a
   real DB sequence for the report registration number, and running two engines
   across dev and prod invites environment-specific bugs. Accepted cost: local
   development requires network access to Neon.
5. **Settings**: a single `config/settings.py` reading environment variables from
   `.env`. Not a `config/settings/` package.
6. **Session**: `SESSION_COOKIE_AGE = 604800` (7 days), per ADR-0005 and
   RESOLUCION-ADVERSARIAL #10.
7. **First admin account**: Django's stock `manage.py createsuperuser`, run
   manually once. No data migration, no custom management command. The design's
   `save()` derivation means no manual `rol` follow-up is needed.
8. **Version control**: this change runs `git init`, adds a `.gitignore`
   excluding `.env`, and configures the remote
   `https://github.com/AngeloGot0204/Proyecto_curso.git`. **Pushing is not
   authorized** and no push step exists anywhere in the change.
9. **Test runner**: `pytest` + `pytest-django` installed in this change, with
   tests covering the `Usuario` model and the login flow. This enables Strict TDD
   for later backlog items.

## Delivery

The tasks forecast reported ~465 authored lines against a 400-line budget and
recommended two chained PRs (Slice A ~321, Slice B ~147). The user reviewed the
forecast and chose a **single PR with `size:exception`**.

Rationale recorded: solo developer, greenfield repository with zero commits, no
second reviewer. The review budget exists to protect reviewer focus, and there is
no other reviewer here.

The irreversible-gate risk does **not** disappear with that choice: the `migrate`
step still requires `AUTH_USER_MODEL` to be correct beforehand.

## Django version — a correction worth recording

The design specified **Django 5.2 LTS**. Mid-session the orchestrator overrode
this with **6.2**, claiming 6.2 was the current LTS. That claim was **false**.

- The orchestrator had read Django's documentation from the project's `main`
  branch, which contains release notes for the **in-development** 6.2, including
  its future LTS designation, and mistook them for a released version.
- The apply agent refused to substitute a version on its own and stopped with
  `No matching distribution found for Django==6.2`.
- Verification against the **PyPI JSON API** (the package index, not the docs)
  established the real state: latest stable **6.1**, current LTS **5.2**
  (5.2.17 published), and no 6.2 at all.

**Final pin: `Django>=5.2.8,<6.0`** — the design's original choice, with the
floor raised because Python 3.14 support landed in 5.2.8 and this machine runs
Python 3.14.6.

Three related facts, verified independently and unaffected by the version error:

| Item | Correct | Wrong but common |
|---|---|---|
| Check constraints | `CheckConstraint(condition=Q(...))` | `check=Q(...)` — deprecated in 5.1, removed in 6.0 |
| PostgreSQL driver | `psycopg[binary]` >= 3.1.12 | `psycopg2-binary` |
| Minimum PostgreSQL | 15+ (Django 6.1 dropped 14) | 13/14 |

**The lesson, recorded deliberately:** version facts must be verified against the
package index, not against documentation. Documentation built from a development
branch describes what is being built, not what can be installed. A confidently
stated wrong fact changed a real decision, and only the apply agent's refusal to
improvise caught it before it reached code.

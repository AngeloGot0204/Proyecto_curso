# Exploration: Modelo base y autenticación (backlog #1)

> Engram: `sdd/modelo-base-y-autenticacion/explore` (observation 35)

## Current State

Greenfield project. No code exists yet — only PRD.md, TECH-DESIGN.md, adrs/, BACKLOG.md at project root. This is the first SDD change; it must lay the Django scaffold that every later backlog item (#2-#14) builds on.

## What ADR-0005 decides

- Auth mechanism: Django's built-in session/cookie auth (`django.contrib.auth`), NOT token-based (JWT rejected — no decoupled frontend per ADR-0001, single Django deployment).
- Login/password reset/permission plumbing: use Django's stock views/forms, no custom auth backend.
- Account management: admin creates accounts via `django.contrib.admin` (no self-registration, ever — PRD explicit).
- Session duration: `SESSION_COOKIE_AGE = 604800` (7 days) — explicit setting decision from RESOLUCION-ADVERSARIAL #10, deliberately no PIN/extra local lock.
- Each device keeps its own independent session (PC and mobile are separate sessions for the same user — nothing to build, it's inherent to cookie-based sessions).
- **"Offline-tolerant session" behavior is NOT implemented in this item.** ADR-0005 describes: if a device has a previously-valid cached session, the app opens and lets the user keep working on local data without re-verifying credentials; real session validation happens **at sync time**; if the session expired while offline, the app asks to log in again but **never discards the local draft**. This depends on the offline/IndexedDB layer and the sync endpoint, which are backlog items #9 and #10 (explicitly listed there: "sesión expirada no descarta borrador"). Item #1's only obligation toward this is setting `SESSION_COOKIE_AGE` correctly and making sure login views don't have side effects that could be mistaken for draft-destroying behavior — actual tolerant/offline logic is out of scope here.

## Usuario model requirements (from PRD)

- Two roles only: `administrador` and `usuario`. No auto-registration.
- Admin: creates/manages user accounts, resets passwords, suspends accounts (S-13), manages report types (S-14 — but S-14 is a custom app screen per TECH-DESIGN, not raw Django admin — this matters for how "admin role" is represented, see below).
- Usuario: fills out and generates reports.
- No extra profile fields mentioned in PRD/TECH-DESIGN beyond role — `Reporte.creado_por` and `ValorDeReporte.autor`/`CambioDeValor` (later items) will FK to this Usuario model, so it must exist as `settings.AUTH_USER_MODEL` before those migrations exist.

## Django scaffolding implied by ADR-0001

- Single Django project (monolith), server-rendered wizard later (item #5) — no DRF, no separate API app needed now (DRF is explicitly deferred to "if a native app is ever needed").
- `django.contrib.admin` will cover most of S-13 (user admin) per ADR-0005's own consequence — confirms admin app must be enabled and Usuario registered in `admin.py`.
- Effort split ~85% Python / 15% JS confirms no frontend build pipeline; templates are server-rendered Django templates.
- Critical, easy-to-miss constraint: **`AUTH_USER_MODEL` must point at the custom Usuario model from the very first migration.** Swapping the user model after any migration exists is highly disruptive in Django. This item is the only place in the whole backlog where that decision can be made cheaply.
- DB choice for local dev during this item: TECH-DESIGN specifies Postgres/Neon, but that's wired up in item #2 (depends on #1). Item #1 needs *a* working DB for `makemigrations`/`migrate` (SQLite is the pragmatic default for local dev until #2 lands) — should be flagged as an open decision for sdd-propose, not resolved here.
- Settings split (base/dev/prod) is a judgment call: given single-developer team and TECH-DESIGN's bias toward simplicity, a single `settings.py` now (split later in item #2 when Vercel/Neon env vars appear) avoids premature structure, but a `config/settings/` package from day one avoids a churn-y refactor later. Present as a tradeoff, not a foregone conclusion.

## Affected areas (files to be created — none exist yet)

- `manage.py`, `config/settings.py` (or `config/settings/`), `config/urls.py` — project scaffold.
- `usuarios/models.py` — `Usuario(AbstractUser)` with a `rol` field (choices: `administrador`/`usuario`).
- `usuarios/admin.py` — register `Usuario` in `django.contrib.admin` (covers create/reset-password/suspend via `is_active`).
- `usuarios/views.py` + `urls.py` — login/logout views (can be Django's built-in `LoginView`/`LogoutView`, minimal custom templates).
- `templates/usuarios/login.html` — server-rendered login screen (S-01).
- `requirements.txt` (or `pyproject.toml`) — Django + minimal deps.

## Approaches

### 1. Custom `Usuario(AbstractUser)` with explicit `rol` field

Subclass `AbstractUser`, add `rol = CharField(choices=[admin, usuario])`, set `AUTH_USER_MODEL = "usuarios.Usuario"` immediately. `is_staff`/`is_superuser` stay reserved for Django-admin site access; `rol` is the app-level permission flag used in custom views (item #13's S-14 screen, `ParticipacionEnReporte`, etc.).

- **Pros:** minimal custom code, keeps Django's battle-tested auth/admin machinery, clean separation between "can use django-admin" and "is app administrator," easy to query/filter by role in app code.
- **Cons:** two overlapping admin concepts (`is_staff` vs `rol=administrador`) need a documented convention so they don't drift (e.g., decide "administrador role always implies is_staff=True").
- **Effort:** Low.

### 2. Default `django.contrib.auth.User` + Django Groups/Permissions for roles

No custom user model, model "administrador"/"usuario" as two Groups.

- **Pros:** zero custom model code, fully stock Django.
- **Cons:** PRD/TECH-DESIGN model explicitly names `Usuario` as an entity with a `rol` field (see TECH-DESIGN's data model table) — diverges from the agreed data model; Groups are a weaker fit for a single mutually-exclusive role field; harder to add role-specific fields later (would require a profile model anyway, defeating the simplicity gain).
- **Effort:** Low, but contradicts TECH-DESIGN's stated data model.

### 3. Fully custom `AbstractBaseUser` + custom manager

Total control over the user model.

- **Pros:** maximum flexibility (custom login field, etc.).
- **Cons:** significant extra code (manager, forms, admin integration) for zero PRD requirement — over-engineered for "email/username + password + 2 roles."
- **Effort:** Medium-High, unjustified given requirements.

## Recommendation

Approach 1: `Usuario(AbstractUser)` with an explicit `rol` field, `AUTH_USER_MODEL` set from the first migration, registered in `django.contrib.admin`. This is the smallest change that satisfies ADR-0005 and PRD while leaving `is_staff`/`is_superuser` available for Django-admin-site access control, and gives later items (`ParticipacionEnReporte`, `creado_por`, `autor` FKs) a stable target. Session settings (`SESSION_COOKIE_AGE = 604800`) should be configured now; the offline-tolerant session *behavior* itself belongs to items #9/#10, not this one.

## Risks

- `AUTH_USER_MODEL` is irreversible once any migration is applied — must be correct in the very first commit of this item.
- Ambiguity between `is_staff` (Django admin access) and `rol=administrador` (app-level permission) must be resolved explicitly in sdd-propose/sdd-design, or later items (#13 admin screens) will guess inconsistently.
- Local dev DB choice (SQLite vs jumping straight to Postgres) is undecided — item #2 (Vercel/Neon) depends on #1, so #1 must pick something workable without blocking on infra.
- Scope creep risk: it would be easy to over-build offline-session-tolerance logic here; ADR-0005's offline behavior is explicitly owned by items #9/#10 and should stay out of this item's tasks.
- Settings-file structure (single file vs `config/settings/` package) is a minor but real fork that affects how painlessly item #2 wires in Vercel/Neon env vars later.

## Ready for Proposal

Yes. Recommend sdd-propose scope this item as: custom `Usuario` model + `AUTH_USER_MODEL` wiring, Django admin registration, login/logout views+templates, `SESSION_COOKIE_AGE` setting, and a minimal project scaffold (settings/urls/manage.py) — explicitly excluding offline session-tolerance logic (#9/#10) and infra/deploy config (#2).

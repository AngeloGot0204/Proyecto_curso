# usuarios Specification

> Engram: `sdd/modelo-base-y-autenticacion/spec` (observation 38)

## Purpose

Defines the custom `Usuario` model, the `rol`/`is_staff` invariant, and session-based authentication (login, logout, session lifetime, Django-admin access) for the greenfield "Generador de Reportes de Campo" project. This is a new capability — no existing behavior to modify.

## Out of Scope (non-goals)

- Offline-tolerant session behavior (ADR-0005 offline half: caching, deferred credential validation, draft preservation on expiry) — backlog items #9/#10. This spec only fixes `SESSION_COOKIE_AGE`.
- Deployment, Vercel, production infrastructure, Vercel Blob — backlog item #2.
- Any report-domain model (`TipoDeReporte`, `DefinicionDeTipo`, `Reporte`, `ValorDeReporte`, `Adjunto`, etc.) — items #3 onward.
- Custom admin screens for report types (S-14) — item #13.
- Self-service password reset (email-based) — S-13 password reset is admin-driven via `django.contrib.admin`.
- Custom user-admin screen — S-13 account creation/reset/suspension is served entirely by the stock Django admin site.

## Requirements

### Requirement: Usuario model

The system MUST define `Usuario(AbstractUser)` in the `usuarios` app with an explicit `rol` field restricted to `administrador` or `usuario`, and MUST set `AUTH_USER_MODEL = "usuarios.Usuario"` before the first migration is generated.

#### Scenario: Usuario model provides rol field

- GIVEN the `usuarios` app's first migration has been applied
- WHEN a `Usuario` instance is created with `rol="usuario"`
- THEN the instance persists with `rol` equal to `"usuario"`
- AND the instance inherits all `AbstractUser` fields (`username`, `password`, `is_active`, `is_staff`, `is_superuser`, etc.)

#### Scenario: rol rejects invalid values

- GIVEN the `Usuario` model's `rol` field is a choice field with only `administrador` and `usuario` as valid choices
- WHEN a `Usuario` is saved with a `rol` value outside that set
- THEN model validation MUST reject the save (`full_clean()` raises `ValidationError`)

### Requirement: rol/is_staff invariant

The system MUST enforce, in code, that `rol == "administrador"` implies `is_staff = True`. This enforcement MUST NOT rely on manual toggling by an admin operator, and MUST apply consistently whenever `rol` changes.

#### Scenario: Setting rol to administrador grants admin access automatically

- GIVEN a `Usuario` with `rol="usuario"` and `is_staff=False`
- WHEN an admin operator changes `rol` to `"administrador"` and saves
- THEN the saved instance has `is_staff=True`
- AND this happens without the operator separately checking the "staff status" checkbox

#### Scenario: Reverting rol to usuario does not silently preserve staff access

- GIVEN a `Usuario` with `rol="administrador"` and `is_staff=True`
- WHEN an admin operator changes `rol` to `"usuario"` and saves
- THEN the saved instance has `is_staff=False`
- AND the user immediately loses Django-admin access on next request

#### Scenario: Existing manual is_staff grant is not silently overridden for administrador

- GIVEN a `Usuario` with `rol="administrador"`
- WHEN the record is saved with no change to `rol`
- THEN `is_staff` MUST remain `True`
- AND `is_superuser` (a separate, independently managed flag) MUST NOT be modified by this enforcement

### Requirement: Login via session authentication

The system MUST provide a login screen (S-01) using Django's stock `LoginView`, authenticating by `username` (Django default identifier; no email-based login).

#### Scenario: Successful login

- GIVEN a `Usuario` exists with `is_active=True` and a known username/password
- WHEN the user submits correct credentials on the login form
- THEN the system creates an authenticated session
- AND redirects the user past the login screen

#### Scenario: Failed login with wrong credentials

- GIVEN a `Usuario` exists with `is_active=True`
- WHEN the user submits an incorrect password
- THEN authentication MUST fail
- AND the login form MUST re-render with a generic invalid-credentials error
- AND no session MUST be created

#### Scenario: Login rejected for inactive account

- GIVEN a `Usuario` exists with `is_active=False`
- WHEN the user submits correct credentials for that account
- THEN authentication MUST fail
- AND no session MUST be created
- AND the response MUST NOT reveal whether the account exists versus being merely wrong credentials beyond Django's standard inactive-account messaging

### Requirement: Logout

The system MUST provide logout via Django's stock `LogoutView`.

#### Scenario: Logout ends the session

- GIVEN a user has an authenticated session
- WHEN the user triggers logout
- THEN the session MUST be invalidated
- AND a subsequent request to a login-required view MUST redirect to the login screen

### Requirement: Session lifetime

The system MUST set `SESSION_COOKIE_AGE = 604800` (7 days) per ADR-0005 / RESOLUCION-ADVERSARIAL #10.

#### Scenario: Session persists within the 7-day window

- GIVEN a user logged in and the session cookie was issued at time T
- WHEN the user returns with the same session cookie before T + 7 days
- THEN the session MUST remain valid without requiring re-authentication

#### Scenario: Session expires after 7 days

- GIVEN a session cookie issued at time T
- WHEN a request arrives with that cookie at or after T + 7 days
- THEN the session MUST be treated as expired
- AND the user MUST be required to log in again to access protected views

Note: this requirement covers only the cookie lifetime setting. Offline-tolerant behavior on expiry (deferred validation, draft preservation) is explicitly out of scope — see Non-goals.

### Requirement: Django-admin access gated by role

The system MUST restrict `/admin` access using Django's standard `is_staff` gate, which is kept consistent with `rol` per the rol/is_staff invariant requirement above.

#### Scenario: Administrador user can access Django admin

- GIVEN a `Usuario` with `rol="administrador"` (and therefore `is_staff=True`) and `is_active=True`
- WHEN that user logs in and navigates to `/admin`
- THEN the Django admin site MUST be accessible
- AND the `Usuario` model MUST be registered and manageable from it (create accounts, reset passwords, toggle `is_active` for suspension)

#### Scenario: Usuario role is denied Django admin access

- GIVEN a `Usuario` with `rol="usuario"` (and therefore `is_staff=False`)
- WHEN that user logs in and navigates to `/admin`
- THEN the Django admin site MUST deny access (redirect to login or show a permission-denied response)

## Dependency Note

This spec assumes `AUTH_USER_MODEL` is set correctly before the first migration; no later change may introduce a second custom user model or bypass this one, since backlog items #2–#14 depend on FK-ing to `Usuario`.

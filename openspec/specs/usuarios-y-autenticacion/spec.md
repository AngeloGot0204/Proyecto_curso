# Usuarios y Autenticación Specification

## Purpose

Defines the custom `Usuario` model, the `rol`/`is_staff` invariant, session-based authentication (login, logout, session lifetime), and the in-app user administration screen (S-13) through which an administrator creates accounts, edits roles, resets passwords and suspends users. Backlog item #1.

## Out of Scope (non-goals)

- Offline-tolerant session behavior (cached credentials, offline login) — not implemented; see ADR-0005.
- Self-service registration: this app has no sign-up. Account creation is admin-driven only.
- Email-based self-service password reset: S-13 password reset is an administrator setting a new password directly.
- Any report-domain model or screen — see the `reportes-modelo`, `wizard-captura` and related capabilities.

## Requirements

### Requirement: Usuario Model With Rol Field

The system MUST define `Usuario(AbstractUser)` in the `usuarios` app with an explicit `rol` field restricted to `administrador` or `usuario`, and MUST set `AUTH_USER_MODEL = "usuarios.Usuario"` before the first migration is generated.

The model MUST expose an `es_administrador` property returning whether `rol` equals `administrador`, used as the single role predicate across the codebase.

#### Scenario: Usuario model provides rol field

- GIVEN the `usuarios` app's first migration has been applied
- WHEN a `Usuario` instance is created with `rol="usuario"`
- THEN the instance persists with `rol` equal to `"usuario"`
- AND the instance inherits all `AbstractUser` fields (`username`, `password`, `is_active`, `is_staff`, `is_superuser`)

#### Scenario: rol rejects invalid values

- GIVEN the `Usuario` model's `rol` field is a choice field with only `administrador` and `usuario` as valid choices
- WHEN a `Usuario` is saved with a `rol` value outside that set
- THEN model validation MUST reject the save (`full_clean()` raises `ValidationError`)

### Requirement: rol/is_staff Invariant

The system MUST enforce, in code, that `rol == "administrador"` implies `is_staff = True`, applied on every `save()` so it never depends on an operator toggling a checkbox.

The invariant MUST be backstopped at the database level by `CheckConstraint`s: one asserting `rol=administrador` implies `is_staff=True` (and its negation), and one asserting `is_superuser=True` implies `rol=administrador`.

A superuser MUST always resolve to `rol=administrador` — the single documented case where a flag overrides `rol`.

#### Scenario: Setting rol to administrador grants staff access automatically

- GIVEN a `Usuario` with `rol="usuario"` and `is_staff=False`
- WHEN `rol` is changed to `"administrador"` and saved
- THEN the saved instance has `is_staff=True`

#### Scenario: Reverting rol to usuario removes staff access

- GIVEN a `Usuario` with `rol="administrador"` and `is_staff=True`
- WHEN `rol` is changed to `"usuario"` and saved
- THEN the saved instance has `is_staff=False`

#### Scenario: Superuser is always administrador

- GIVEN a `Usuario` saved with `is_superuser=True` and `rol="usuario"`
- WHEN the instance is saved
- THEN `rol` becomes `administrador` and `is_staff` becomes `True`

#### Scenario: Database rejects an inconsistent row

- GIVEN a write that bypasses `save()` (raw SQL or `QuerySet.update`)
- WHEN it would persist `rol="administrador"` with `is_staff=False`
- THEN the `usuario_rol_implica_is_staff` constraint MUST reject the write

### Requirement: Login Via Session Authentication

The system MUST provide a login screen (S-01) using Django's stock `LoginView`, authenticating by `username` (no email-based login). Authentication requires connectivity — there is no offline login path.

#### Scenario: Successful login

- GIVEN a `Usuario` exists with `is_active=True` and a known username/password
- WHEN the user submits correct credentials on the login form
- THEN the system creates an authenticated session
- AND redirects the user to the `inicio` landing route

#### Scenario: Failed login with wrong credentials

- GIVEN a `Usuario` exists with `is_active=True`
- WHEN the user submits an incorrect password
- THEN authentication MUST fail, the form MUST re-render with a generic invalid-credentials error, and no session MUST be created

#### Scenario: Login rejected for suspended account

- GIVEN a `Usuario` exists with `is_active=False`
- WHEN the user submits correct credentials for that account
- THEN authentication MUST fail and no session MUST be created

### Requirement: Logout

The system MUST provide logout via Django's stock `LogoutView`, reachable from the shared navigation sidebar.

#### Scenario: Logout ends the session

- GIVEN a user has an authenticated session
- WHEN the user triggers logout
- THEN the session MUST be invalidated
- AND a subsequent request to a login-required view MUST redirect to the login screen

### Requirement: Session Lifetime

The system MUST set `SESSION_COOKIE_AGE = 604800` (7 days) per ADR-0005.

#### Scenario: Session persists within the 7-day window

- GIVEN a session cookie issued at time T
- WHEN the user returns with the same cookie before T + 7 days
- THEN the session MUST remain valid without re-authentication

#### Scenario: Session expires after 7 days

- GIVEN a session cookie issued at time T
- WHEN a request arrives with that cookie at or after T + 7 days
- THEN the session MUST be treated as expired and the user MUST log in again

### Requirement: Admin-Role-Gated User Administration

The system MUST serve user administration (S-13) as in-app screens under `/usuarios/`, gated by the shared `solo_administradores` decorator. The decorator MUST apply `login_required` outermost so an anonymous request redirects to login before `es_administrador` is read, and MUST raise `PermissionDenied` (403) for an authenticated non-administrator.

Every S-13 view — list, create, edit, reset password, suspend — MUST be gated this way.

#### Scenario: Administrator reaches the user list

- GIVEN an authenticated `Usuario` with `rol="administrador"`
- WHEN the user requests `/usuarios/`
- THEN the response is 200 and lists user accounts

#### Scenario: Non-administrator is denied

- GIVEN an authenticated `Usuario` with `rol="usuario"`
- WHEN the user requests any `/usuarios/` administration route
- THEN the response is 403 and the view body never executes

#### Scenario: Anonymous request redirects to login

- GIVEN an unauthenticated visitor
- WHEN they request any `/usuarios/` administration route
- THEN the response redirects to `LOGIN_URL`

### Requirement: User List With Search and Pagination

The user list MUST support a `?q=` search filtering by `username` (case-insensitive substring) and MUST paginate at 20 rows per page, ordered by `username`. An invalid or out-of-range `?page=` MUST be clamped to a valid page rather than raising.

#### Scenario: Search narrows the list

- GIVEN users `ana`, `andres` and `bruno` exist
- WHEN an administrator requests `/usuarios/?q=an`
- THEN only `ana` and `andres` appear

#### Scenario: Out-of-range page is clamped

- GIVEN fewer than 20 users exist
- WHEN an administrator requests `/usuarios/?page=99`
- THEN the response is 200 showing the last available page

### Requirement: Account Creation By Administrator

The system MUST let an administrator create an account (username, password, `rol`). This is the only account-creation path — there is no self-registration.

#### Scenario: Administrator creates an account

- GIVEN an administrator on the create-user form
- WHEN they submit a valid username, password and rol
- THEN a `Usuario` is persisted, a success flash message is shown, and the response redirects to the user list

### Requirement: Role Editing

The system MUST let an administrator edit an existing user's `rol`. Changing `rol` MUST propagate to `is_staff` through the model invariant.

#### Scenario: Administrator promotes a user

- GIVEN a `Usuario` with `rol="usuario"`
- WHEN an administrator saves the edit form with `rol="administrador"`
- THEN the user's `rol` is `administrador` and `is_staff` is `True`

### Requirement: Administrator-Driven Password Reset

The system MUST let an administrator set a new password for any user without knowing the previous one, applying it via `set_password` so the stored value stays hashed.

#### Scenario: Administrator resets a password

- GIVEN an administrator on the reset-password form for a target user
- WHEN they submit a valid new password
- THEN the target user's password is replaced with its hash
- AND the target user can authenticate with the new password

### Requirement: Account Suspension Toggle

The system MUST let an administrator suspend or reactivate an account by toggling `is_active` through a POST-only route following the POST/Redirect/GET pattern.

An administrator MUST NOT be able to suspend their own account: that request MUST be rejected with an error flash message and no state change, because it would lock the acting administrator out of every `solo_administradores` screen with no self-service way back in. Reactivation is always permitted, and suspending a different administrator is unrestricted.

#### Scenario: Administrator suspends another user

- GIVEN an active `Usuario` who is not the requesting administrator
- WHEN the administrator POSTs to the suspend route for that user
- THEN `is_active` becomes `False`, a success message is shown, and the response redirects to the user list

#### Scenario: Suspended user is reactivated

- GIVEN a `Usuario` with `is_active=False`
- WHEN an administrator POSTs to the suspend route for that user
- THEN `is_active` becomes `True`

#### Scenario: Self-suspension is blocked

- GIVEN an authenticated administrator
- WHEN they POST to the suspend route for their own account
- THEN `is_active` remains `True`, an error flash message is shown, and the response redirects to the user list

### Requirement: Django Admin Registration Kept for Recovery

The system MUST keep `Usuario` registered in the Django admin site as a recovery surface, gated by Django's standard `is_staff` check (kept consistent with `rol` by the model invariant). The registration MUST expose `rol` as editable and MUST render `is_staff` read-only, since `save()` derives it from `rol` and would silently overwrite a direct edit.

#### Scenario: Administrador user can access Django admin

- GIVEN a `Usuario` with `rol="administrador"` and `is_active=True`
- WHEN that user navigates to `/admin`
- THEN the Django admin site is accessible and `Usuario` is manageable from it

#### Scenario: Usuario role is denied Django admin access

- GIVEN a `Usuario` with `rol="usuario"` (and therefore `is_staff=False`)
- WHEN that user navigates to `/admin`
- THEN the Django admin site MUST deny access

## Dependency Note

`AUTH_USER_MODEL` MUST stay set to `usuarios.Usuario`: every other capability foreign-keys to it (`Reporte.creador`, `ValorDeReporte.autor`, `VistoBueno.usuario`, `ParticipacionEnReporte.usuario`, `CambioDeValor.autor`, `Adjunto.autor`, `Generacion.usuario`).

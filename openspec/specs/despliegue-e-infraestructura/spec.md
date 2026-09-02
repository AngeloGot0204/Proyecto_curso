# Despliegue e Infraestructura Specification

## Purpose

Defines the deployed, HTTPS-reachable production environment for "Generador de Reportes de Campo" on Vercel + Neon (Postgres) + Vercel Blob, per ADR-0009. Infrastructure and configuration, not application logic. Backlog item #2.

## Out of Scope (non-goals)

- A settings module split (`base.py`/`production.py`).
- HSTS preload submission to the browser preload list (`vercel.app` is a public suffix this project cannot submit).
- A one-year `SECURE_HSTS_SECONDS`; deferred until a real domain and real users exist.
- Custom domain and DNS (Vercel's default `<project>.vercel.app` only).
- Staging environment; backup/restore or rollback tooling for the Neon production branch; Neon's per-preview branch integration; Django-level connection pooling (`pool` option).

## Verification Kind Legend

- **Automatable** — a real, code-level assertion (settings value, fail-loud boot behavior, `check --deploy` exit code).
- **Manual (live)** — requires a real deployed URL and a human check; cannot be scripted into the test suite honestly.
- **Manual (console)** — a provisioning fact confirmed by the user in a provider console (Vercel/Neon/Blob).

## Requirements

### Requirement: HTTPS Reachability

The deployed application MUST be reachable over HTTPS at Vercel's default `<project>.vercel.app` domain, with no custom domain configured.

#### Scenario: Deployed app answers over HTTPS (Manual, live)

- GIVEN a completed Vercel deployment of `main`
- WHEN a human requests `https://<project>.vercel.app/login`
- THEN the response MUST succeed with a valid TLS certificate and no protocol errors

### Requirement: Static File Serving via WhiteNoise

Vercel does not serve `/static/` from `outputDirectory` the way it does for static-site frameworks — confirmed empirically on this project's live app: `STATIC_ROOT` set, `collectstatic` run at build time (127 files copied), and two independent `vercel.json` `outputDirectory` configurations attempted, yet every `/static/` request still reached the WSGI function and returned Django's own 404.

The system MUST set `STATIC_ROOT` and serve static assets via WhiteNoise from inside the WSGI function, independent of Vercel's routing.

#### Scenario: STATIC_ROOT is configured with WhiteNoise serving it (Automatable)

- GIVEN `config/settings.py` is imported
- THEN `STATIC_ROOT` MUST be set to a non-null path
- AND `whitenoise.middleware.WhiteNoiseMiddleware` MUST be present in `MIDDLEWARE`
- AND `STORAGES["staticfiles"]["BACKEND"]` MUST be a WhiteNoise storage class

#### Scenario: Static assets are actually served on the live domain (Manual, live)

- GIVEN a completed deployment
- WHEN a human requests a known static asset URL (e.g. admin CSS) on the live domain
- THEN it MUST return 200 with the expected content type, served by WhiteNoise, not a 404

### Requirement: Neon Pooled Endpoint With CONN_MAX_AGE=0

The deployed app MUST connect to Neon via its pooled (`-pooler`) endpoint, and `DATABASES["default"]["CONN_MAX_AGE"]` MUST equal `0`, because each serverless invocation is short-lived and persistent connections would exhaust the pool.

#### Scenario: Settings enforce CONN_MAX_AGE=0 (Automatable)

- GIVEN `config/settings.py` is imported with any valid `DATABASE_URL`
- THEN `DATABASES["default"]["CONN_MAX_AGE"]` MUST equal `0`

#### Scenario: Production DATABASE_URL targets the pooled endpoint (Manual, console)

- GIVEN the Vercel Production environment variables
- THEN `DATABASE_URL` MUST use Neon's `-pooler` hostname

### Requirement: ALLOWED_HOSTS Fails Loud

`ALLOWED_HOSTS` MUST be read via `require_env()`, with no default value, consistent with `DJANGO_SECRET_KEY`/`DATABASE_URL`.

#### Scenario: Boot fails when DJANGO_ALLOWED_HOSTS is missing (Automatable)

- GIVEN the `DJANGO_ALLOWED_HOSTS` environment variable is unset
- WHEN Django settings are loaded
- THEN loading MUST raise `ImproperlyConfigured` rather than falling back to a default host list

### Requirement: CSRF Trust for the Deployment Origin

`CSRF_TRUSTED_ORIGINS` MUST include the deployment's HTTPS origin so authenticated POSTs succeed in production.

#### Scenario: CSRF_TRUSTED_ORIGINS is configured for the deployed origin (Automatable)

- GIVEN `config/settings.py` is imported with a production-like `DJANGO_ALLOWED_HOSTS`/origin env var
- THEN `CSRF_TRUSTED_ORIGINS` MUST contain a matching `https://` origin
- Note: this only proves the setting's presence and shape, not that Django actually accepts the POST — see the live scenario below.

#### Scenario: Login POST succeeds against the deployed origin (Manual, live)

- GIVEN a completed deployment and a valid `Usuario` account
- WHEN a human submits the login form on `https://<project>.vercel.app/login`
- THEN the POST MUST NOT be rejected with a CSRF verification failure

### Requirement: HTTPS Detection Behind Vercel's Proxy

`SECURE_PROXY_SSL_HEADER` MUST be set so `request.is_secure()` is correct behind Vercel's TLS-terminating proxy.

#### Scenario: SECURE_PROXY_SSL_HEADER is set (Automatable)

- GIVEN `config/settings.py` is imported
- THEN `SECURE_PROXY_SSL_HEADER` MUST equal `("HTTP_X_FORWARDED_PROTO", "https")`
- Note: a wrong value does not raise — it silently misreports `request.is_secure()`. This scenario proves presence only, not correctness.

#### Scenario: request.is_secure() is correct on a real HTTPS request (Manual, live)

- GIVEN a completed deployment
- WHEN a human performs a real HTTPS request and inspects behavior gated on `request.is_secure()`
- THEN the app MUST treat the request as secure, with no CSRF or cookie anomalies traceable to a misdetected scheme

### Requirement: HTTPS-Only Transport Hardening

Transport-security settings MUST derive from an explicit, fail-loud, strictly-parsed `DJANGO_HTTPS_ONLY` flag, so the application never infers its environment.

#### Scenario: Missing DJANGO_HTTPS_ONLY fails loud (Automatable)

- GIVEN the `DJANGO_HTTPS_ONLY` environment variable is unset
- WHEN Django settings are loaded
- THEN loading MUST raise `ImproperlyConfigured`

#### Scenario: Malformed DJANGO_HTTPS_ONLY is rejected, not coerced (Automatable)

- GIVEN `DJANGO_HTTPS_ONLY` is set to a value other than exactly `True` or `False` (e.g. `true`, `1`, `yes`, empty string)
- WHEN Django settings are loaded
- THEN loading MUST raise `ImproperlyConfigured` naming the variable
- Note: this closes the dangerous typo direction, where a naive boolean cast would silently disable every protection in production.

#### Scenario: DJANGO_HTTPS_ONLY=True hardens transport (Automatable)

- GIVEN `DJANGO_HTTPS_ONLY="True"`
- THEN `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and `SECURE_SSL_REDIRECT` MUST all be `True`
- AND `SECURE_HSTS_SECONDS` MUST equal `3600` and `SECURE_HSTS_INCLUDE_SUBDOMAINS` MUST be `True`

#### Scenario: DJANGO_HTTPS_ONLY=False leaves local development unaffected (Automatable)

- GIVEN `DJANGO_HTTPS_ONLY="False"`
- THEN `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and `SECURE_SSL_REDIRECT` MUST all be `False`
- AND `SECURE_HSTS_SECONDS` MUST equal `0`, so plain-HTTP local development is unaffected

#### Scenario: HSTS preload refusal is deliberate and pinned (Automatable)

- GIVEN `config/settings.py` is imported
- THEN `SECURE_HSTS_PRELOAD` MUST be `False`
- AND `security.W021` MUST be present in `SILENCED_SYSTEM_CHECKS`
- Note: `vercel.app` is a public suffix this project does not own and can never submit to the browser preload list; this pins the refusal so a future contributor cannot "fix" the warning by enabling preload.

#### Scenario: Deployed app carries hardened transport headers and cookies with no redirect loop (Manual, live)

- GIVEN a completed deployment with `DJANGO_HTTPS_ONLY=True`
- WHEN a human inspects the response to a live HTTPS request
- THEN the response MUST carry `Strict-Transport-Security` with `includeSubDomains` and no `preload` token
- AND the session and CSRF cookies MUST carry `Secure`
- AND the page MUST load as a single `200`, with no redirect loop (a `301` chain to the same HTTPS URL indicates a misconfigured `SECURE_PROXY_SSL_HEADER`)

#### Scenario: DJANGO_HTTPS_ONLY is set correctly per environment (Manual, console)

- GIVEN the Vercel dashboard, with the `DJANGO_HTTPS_ONLY` value revealed (not assumed) for each environment
- THEN Production and Preview MUST show exactly `True`
- AND Development MUST show exactly `False`

### Requirement: Explicitly Pinned Python Version

The Python version MUST be pinned explicitly in a committed `.python-version`
file, so development and production run the same interpreter and the choice is
visible rather than derived.

Without that file, Vercel resolves the version from `requires-python` in
`pyproject.toml` by taking the **lower bound** of the range. That makes the
deployed interpreter a side effect of how the range is written: lowering the
floor to widen compatibility would silently move production to an older
interpreter, with no diff that looks like a deployment change.

Django 5.2 supports Python 3.10 through 3.14; this project runs 3.12. Changing
it is a deliberate decision requiring its own verification, not an inherited
consequence of a dependency range.

#### Scenario: Version is pinned in the repository

- GIVEN the repository
- WHEN it is inspected
- THEN a committed `.python-version` file names the exact deployed version

#### Scenario: Build uses the pinned version

- GIVEN a Vercel deployment
- WHEN its build log is inspected
- THEN the Python version it reports matches `.python-version`

### Requirement: Manual, Developer-Triggered Migrations

Database schema changes MUST be applied to the Neon production branch by an explicit developer-run `manage.py migrate`. Migrations MUST NOT run inside a request handler and MUST NOT run as an automatic build step.

#### Scenario: No build-step or request-time migration exists (Automatable)

- GIVEN the repository's build configuration (`vercel.json`, `pyproject.toml` build scripts) and application views
- THEN none MUST invoke `manage.py migrate` or call Django's migration executor automatically

#### Scenario: Developer applies migrations before relying on new schema (Manual, console)

- GIVEN a deploy that depends on new migrations
- WHEN the developer runs `python manage.py migrate` against the Neon production branch
- THEN the production branch schema MUST match the deployed code's expectations

### Requirement: Vercel Blob as the Default File Storage Backend

Vercel's serverless functions run on a read-only filesystem except `/tmp`, so Django's `FileSystemStorage` cannot persist uploads in production. A Vercel Blob store MUST be provisioned with its access token wired as `BLOB_READ_WRITE_TOKEN`, and `STORAGES["default"]` MUST resolve to `config.storage.VercelBlobStorage` in production.

The backend selection MUST be gated on `not DEBUG`, never on the mere presence of `VERCEL`/`BLOB_READ_WRITE_TOKEN`: `vercel env pull` copies those into a local `.env` for convenience, so a development machine can have them set while still running on a writable filesystem.

The store holds uploaded files only — `TipoDeReporte.plantilla`, `TipoDeReporte.logo`, `DefinicionDeTipo.archivo_yaml` and `Adjunto.archivo`. Generated `.xlsx` documents are streamed to the requester and never persisted (see `generacion-documento`).

#### Scenario: Production resolves to the Blob backend (Automatable)

- GIVEN `config/settings.py` is imported with `DEBUG=False`
- THEN `STORAGES["default"]["BACKEND"]` MUST be `config.storage.VercelBlobStorage`

#### Scenario: Development uses the local filesystem (Automatable)

- GIVEN `config/settings.py` is imported with `DEBUG=True`
- THEN `STORAGES["default"]["BACKEND"]` MUST be `django.core.files.storage.FileSystemStorage`
- AND this MUST hold even when `BLOB_READ_WRITE_TOKEN` is present in the environment

#### Scenario: Blob store exists and its token is wired (Manual, console)

- GIVEN the Vercel project dashboard
- THEN a Blob store MUST exist and be linked to the project
- AND `BLOB_READ_WRITE_TOKEN` MUST be set in the relevant Vercel environment(s)

### Requirement: Preview Deployments Share the Neon Dev Branch

Vercel preview deployments MUST use the existing Neon dev branch's `DATABASE_URL`, with no per-preview branch provisioning.

#### Scenario: A preview deployment builds and connects successfully (Manual, console)

- GIVEN a non-`main` branch pushed to the repository
- WHEN Vercel builds a preview deployment
- THEN the build MUST succeed and the preview's `DATABASE_URL` MUST resolve to the Neon dev branch

### Requirement: Authentication Behavior Holds in Production

Login/logout/role-gating behavior defined in `usuarios-y-autenticacion` MUST continue to hold on the deployed application. This capability does not modify that behavior.

#### Scenario: Full auth round-trip on the deployed app (Manual, live)

- GIVEN a completed deployment with a seeded `administrador` and a seeded `usuario` account
- WHEN a human logs in as each account and as an unauthenticated visitor
- THEN the `administrador` MUST reach `/admin/`, the `usuario` MUST be denied `/admin/`, and the unauthenticated visitor MUST be redirected to `/login`

### Requirement: Secrets Handling

`DJANGO_DEBUG` MUST be false in the production environment, and no secret value MUST appear in the repository.

#### Scenario: DEBUG is false by default and check --deploy passes (Automatable)

- GIVEN `DJANGO_DEBUG` is unset and a production-like `DJANGO_ALLOWED_HOSTS`/`DATABASE_URL` are set
- WHEN `manage.py check --deploy --fail-level WARNING` runs
- THEN `DEBUG` MUST be `False`
- AND the command MUST exit `0`, reporting no issues at WARNING or above

#### Scenario: No secret values are committed (Automatable)

- GIVEN `.gitignore` and `.env.example`
- THEN `.env` MUST be gitignored
- AND `.env.example` MUST contain only placeholder values, never a real secret

#### Scenario: Production secrets are set only in the Vercel dashboard (Manual, console)

- GIVEN the Vercel Production environment
- THEN `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` and `BLOB_READ_WRITE_TOKEN` MUST each be set there, not committed to the repository

## Dependency Note

This capability does not restate or modify `usuarios-y-autenticacion`; it only asserts that authentication behavior continues to hold once deployed. Any future change to authentication belongs to that spec, not this one.

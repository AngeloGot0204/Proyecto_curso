# despliegue-e-infraestructura Specification

> Engram: `sdd/despliegue-e-infraestructura/spec`
>
> **Revision 2 — amendment.** Design revision 2 (Engram #53) resolved the user's tenth
> decision (Engram #54): the four `manage.py check --deploy` transport-security warnings
> (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS) are in scope
> for this item, driven by an explicit, fail-loud `DJANGO_HTTPS_ONLY` flag rather than
> environment inference. This revision adds the "HTTPS-only transport hardening"
> requirement and its seven scenarios (verbatim from the design's Required Spec
> Amendment), tightens the "Secrets handling" `check --deploy` scenario to name
> `--fail-level WARNING` explicitly, and updates the totals accordingly. The
> "Manual, developer-triggered migrations" and "Vercel Blob provisioned but unconsumed"
> automatable scenarios already carried the narrowed wording the design confirms
> (no build step runs migrations / no code consumes the Blob token) and needed no change.

## Purpose

Defines the deployed, HTTPS-reachable production environment for "Generador de Reportes de Campo" on Vercel + Neon (Postgres) + Vercel Blob, per ADR-0009. This is a new capability (infrastructure/configuration, not application logic) — no existing behavior to modify. Production is a demo with disposable data; no real field users yet (time-bound assumption, see proposal).

## Out of Scope (non-goals)

- Sentry/observability (#14), attachment upload code (#11), report-type logo upload (#13), any report-domain model (#3+).
- Offline/service-worker implementation (#9/#10).
- A settings module split (`base.py`/`production.py`).
- HSTS preload submission to the browser preload list (`vercel.app` is a public suffix this project cannot submit).
- A one-year `SECURE_HSTS_SECONDS`; deferred until a real domain and real users exist.
- Retrofitting the strict `require_bool_env` parsing onto `DJANGO_DEBUG`.
- Custom domain and DNS (Vercel's default `<project>.vercel.app` only).
- Staging environment; backup/restore or rollback tooling for the Neon production branch; Neon's per-preview branch integration; Django-level connection pooling (`pool` option).

## Verification Kind Legend

- **Automatable** — a real, code-level assertion (settings value, fail-loud boot behavior, `check --deploy` exit code).
- **Manual (live)** — requires a real deployed URL and a human check; cannot be scripted into the test suite honestly.
- **Manual (console)** — a provisioning fact confirmed by the user in a provider console (Vercel/Neon/Blob).

## Requirements

### Requirement: HTTPS reachability

The deployed application MUST be reachable over HTTPS at Vercel's default `<project>.vercel.app` domain, with no custom domain configured in this item.

#### Scenario: Deployed app answers over HTTPS (Manual, live)
- GIVEN a completed Vercel deployment of `main`
- WHEN a human requests `https://<project>.vercel.app/login`
- THEN the response MUST succeed with a valid TLS certificate and no protocol errors

### Requirement: Static file serving via WhiteNoise

Revision 3 (superseded from "without WhiteNoise"). Empirical deployment evidence on
this session's live app: `STATIC_ROOT` set, `collectstatic` run at build time (127
files copied), and two independent `vercel.json` `outputDirectory` configurations
attempted — every `/static/` request still reached the WSGI function and returned
Django's own 404, never Vercel's static hosting. The system MUST set `STATIC_ROOT`
and serve static assets via WhiteNoise from inside the WSGI function, independent of
Vercel's routing.

#### Scenario: STATIC_ROOT is configured with WhiteNoise serving it (Automatable)
- GIVEN `config/settings.py` is imported
- THEN `STATIC_ROOT` MUST be set to a non-null path
- AND `whitenoise.middleware.WhiteNoiseMiddleware` MUST be present in `MIDDLEWARE`
- AND `STORAGES["staticfiles"]["BACKEND"]` MUST be a WhiteNoise storage class

#### Scenario: Static assets are actually served on the live domain (Manual, live)
- GIVEN a completed deployment
- WHEN a human requests a known static asset URL (e.g. admin CSS) on the live domain
- THEN it MUST return 200 with the expected content type, served by WhiteNoise, not a 404

### Requirement: Neon pooled endpoint with CONN_MAX_AGE=0

The deployed app MUST connect to Neon via its pooled (`-pooler`) endpoint, and `DATABASES["default"]["CONN_MAX_AGE"]` MUST equal `0`.

#### Scenario: Settings enforce CONN_MAX_AGE=0 (Automatable)
- GIVEN `config/settings.py` is imported with any valid `DATABASE_URL`
- THEN `DATABASES["default"]["CONN_MAX_AGE"]` MUST equal `0`

#### Scenario: Production DATABASE_URL targets the pooled endpoint (Manual, console)
- GIVEN the Vercel Production environment variables
- THEN `DATABASE_URL` MUST use Neon's `-pooler` hostname, confirmed by the user in the Vercel dashboard

### Requirement: ALLOWED_HOSTS fails loud

`ALLOWED_HOSTS` MUST be read via `require_env()`, with no default value, consistent with `DJANGO_SECRET_KEY`/`DATABASE_URL`.

#### Scenario: Boot fails when DJANGO_ALLOWED_HOSTS is missing (Automatable)
- GIVEN the `DJANGO_ALLOWED_HOSTS` environment variable is unset
- WHEN Django settings are loaded
- THEN loading MUST raise `ImproperlyConfigured` rather than falling back to a default host list

### Requirement: CSRF trust for the deployment origin

`CSRF_TRUSTED_ORIGINS` MUST include the deployment's HTTPS origin so authenticated POSTs succeed in production.

#### Scenario: CSRF_TRUSTED_ORIGINS is configured for the deployed origin (Automatable)
- GIVEN `config/settings.py` is imported with a production-like `DJANGO_ALLOWED_HOSTS`/origin env var
- THEN `CSRF_TRUSTED_ORIGINS` MUST contain a matching `https://` origin
- Note: this only proves the setting's presence and shape, not that Django actually accepts the POST — see the live scenario below.

#### Scenario: Login POST succeeds against the deployed origin (Manual, live)
- GIVEN a completed deployment and a valid `Usuario` account
- WHEN a human submits the login form on `https://<project>.vercel.app/login`
- THEN the POST MUST NOT be rejected with a CSRF verification failure

### Requirement: HTTPS detection behind Vercel's proxy

`SECURE_PROXY_SSL_HEADER` MUST be set so `request.is_secure()` is correct behind Vercel's TLS-terminating proxy.

#### Scenario: SECURE_PROXY_SSL_HEADER is set (Automatable)
- GIVEN `config/settings.py` is imported
- THEN `SECURE_PROXY_SSL_HEADER` MUST equal `("HTTP_X_FORWARDED_PROTO", "https")`
- Note: a wrong value does not raise — it silently misreports `request.is_secure()`. This scenario proves presence only, not correctness.

#### Scenario: request.is_secure() is correct on a real HTTPS request (Manual, live)
- GIVEN a completed deployment
- WHEN a human performs a real HTTPS request against the live domain and inspects behavior gated on `request.is_secure()` (e.g. secure-cookie handling)
- THEN the app MUST treat the request as secure, with no CSRF or cookie anomalies traceable to a misdetected scheme

### Requirement: HTTPS-only transport hardening

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

#### Scenario: DJANGO_HTTPS_ONLY is set correctly per environment in the Vercel dashboard (Manual, console)
- GIVEN the Vercel dashboard, with the `DJANGO_HTTPS_ONLY` value revealed (not assumed) for each environment
- THEN Production and Preview MUST show exactly `True`
- AND Development MUST show exactly `False`
- Note: `require_bool_env` proves the variable exists and parses; only this manual check proves which way it actually points in a dashboard the repository cannot see.

### Requirement: Manual, developer-triggered migrations

Database schema changes MUST be applied to the Neon production branch by an explicit developer-run `manage.py migrate`. Migrations MUST NOT run inside a request handler and MUST NOT run as an automatic build step.

#### Scenario: No build-step or request-time migration exists (Automatable)
- GIVEN the repository's build configuration (`vercel.json`, `pyproject.toml` build scripts, if any) and application views
- THEN none MUST invoke `manage.py migrate` or call Django's migration executor automatically

#### Scenario: Developer applies migrations before relying on new schema (Manual, console)
- GIVEN a deploy that depends on new migrations
- WHEN the developer runs `python manage.py migrate` against the Neon production branch before/after promoting that deploy
- THEN the production branch schema MUST match the deployed code's expectations

### Requirement: Vercel Blob provisioned but unconsumed

A Vercel Blob store MUST be provisioned for the project with its access token wired as an environment variable. No application code may consume it in this item.

#### Scenario: Blob store exists and its token is wired (Manual, console)
- GIVEN the Vercel project dashboard
- THEN a Blob store MUST exist and be linked to the project
- AND `BLOB_READ_WRITE_TOKEN` MUST be set in the relevant Vercel environment(s)

#### Scenario: No code consumes the Blob store (Automatable)
- GIVEN the repository's dependencies and application code
- THEN no `django-storages` Blob backend, upload view, or Blob SDK call MUST be present

### Requirement: Preview deployments share the Neon dev branch

Vercel preview deployments MUST use the existing Neon dev branch's `DATABASE_URL`, with no per-preview branch provisioning in this item.

#### Scenario: A preview deployment builds and connects successfully (Manual, console)
- GIVEN a non-`main` branch pushed to the repository
- WHEN Vercel builds a preview deployment
- THEN the build MUST succeed and the preview's `DATABASE_URL` MUST resolve to the Neon dev branch

### Requirement: Item #1 authentication behavior holds in production

Existing login/logout/role-gating behavior (see `spec/usuarios`) MUST continue to hold on the deployed application; this spec does not modify that behavior.

#### Scenario: Full auth round-trip on the deployed app (Manual, live)
- GIVEN a completed deployment with a seeded `administrador` and a seeded `usuario` account
- WHEN a human logs in as each account and as an unauthenticated visitor
- THEN the `administrador` MUST reach `/admin/`, the `usuario` MUST be denied `/admin/`, and the unauthenticated visitor MUST be redirected to `/login`

### Requirement: Secrets handling

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
- THEN `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, and `BLOB_READ_WRITE_TOKEN` MUST each be set there, not committed to the repository

## Dependency Note

This spec does not restate or modify `spec/usuarios` (Engram #48); it only asserts that item #1's behavior continues to hold once deployed. Any future change to authentication behavior belongs to that spec, not this one.

## Totals

12 requirements, 26 scenarios. Breakdown by verification kind: Automatable 14, Manual (live) 6, Manual (console) 6 (14 + 6 + 6 = 26).

Per-requirement scenario counts: HTTPS reachability 1, static 2, Neon 2, ALLOWED_HOSTS 1, CSRF 2, SSL header 2, HTTPS-only transport hardening 7, migrations 2, Blob 2, previews 1, item#1 auth 1, secrets 3 — sum 1+2+2+1+2+2+7+2+2+1+1+3 = 26.

Automatable count check: static 1, Neon 1, ALLOWED_HOSTS 1, CSRF 1, SSL header 1, transport hardening 5, migrations 1, Blob 1, secrets 2 — sum 1+1+1+1+1+5+1+1+2 = 14.

Manual (live) count check: HTTPS reachability 1, static 1, CSRF 1, SSL header 1, transport hardening 1, item#1 auth 1 — sum = 6.

Manual (console) count check: Neon 1, migrations 1, Blob 1, previews 1, transport hardening 1, secrets 1 — sum = 6.

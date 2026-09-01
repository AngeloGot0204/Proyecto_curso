# Observabilidad Specification

## Purpose

Make production failures durably searchable, alertable and traceable instead of
leaving them in stdout. Excel generation errors, invalid report-type
configuration and any unhandled Django exception must reach Sentry with enough
context to diagnose them, without adding an observability call at every site
that can fail. Backlog item #14, ADR-0008.

## Out of Scope (non-goals)

- Performance tracing, profiling or session replay: only exception capture.
- Frontend/JavaScript error capture — the offline layer's failures surface to
  the user through the queue, not through Sentry.
- Alerting rules, dashboards, retention and quotas: those are configured in the
  Sentry project, not in this repository.
- Structured business metrics or analytics.

## Requirements

### Requirement: Sentry Initialization Is Optional and Fails Soft

The system MUST read the Sentry DSN from a plain optional `SENTRY_DSN`
environment variable and MUST NOT use the fail-loud `require_env()` pattern
that `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` and
`DJANGO_HTTPS_ONLY` use.

`sentry_sdk.init()` MUST be called only when a DSN is present. Missing
observability is not a reason to refuse to boot: a developer without a Sentry
project MUST be able to run the application normally, and production activates
capture the moment the DSN is configured.

#### Scenario: Settings import cleanly without a DSN

- GIVEN `SENTRY_DSN` is unset
- WHEN Django settings are imported
- THEN the import succeeds and `sentry_sdk.init()` is not called

#### Scenario: Settings import cleanly with a DSN

- GIVEN `SENTRY_DSN` holds a valid DSN
- WHEN Django settings are imported
- THEN the import succeeds and `sentry_sdk.init()` is called with that DSN

### Requirement: Environment Tagging From Vercel

Captured events MUST be tagged with the deployment environment, read from
Vercel's natively exposed `VERCEL_ENV`, defaulting to `development` when
absent. This MUST NOT require a Sentry-specific Vercel integration.

Without this, production, preview and local events land in one undifferentiated
stream and an alert cannot tell a real incident from a preview experiment.

#### Scenario: Production events are tagged as production

- GIVEN `VERCEL_ENV` is `production`
- WHEN Sentry is initialized
- THEN its `environment` is `production`

#### Scenario: Local events default to development

- GIVEN `VERCEL_ENV` is unset
- WHEN Sentry is initialized
- THEN its `environment` is `development`

### Requirement: Capture Without Call-Site Changes

Exception capture MUST work through the SDK's `DjangoIntegration` and its
default `LoggingIntegration`, with no custom logging configuration.

Existing `logger.exception(...)` calls MUST be captured as-is, and no call site
may be required to import `sentry_sdk` or call `capture_exception` explicitly.
This keeps the application code free of observability plumbing and means a
future `logger.exception` is captured automatically, without anyone remembering
to wire it.

The two current capture points are:

- `reportes/views.py::generar` — a `ProblemaDeGeneracion` while building the
  `.xlsx`, which the user sees as a flash message rather than a raw 500.
- `tipos_reporte/generador.py` — an attachment that cannot be decoded and is
  skipped so it never fails the whole document.

#### Scenario: Generation failure is captured

- GIVEN Sentry is initialized and a report whose generation raises `ProblemaDeGeneracion`
- WHEN a user requests generation
- THEN the exception is captured by Sentry
- AND the user still receives the flash message and redirect, never a raw 500

#### Scenario: Undecodable attachment is captured without failing generation

- GIVEN a report carrying an attachment that cannot be decoded as an image
- WHEN the document is generated
- THEN the exception is captured, that attachment is skipped, and the document is still produced

#### Scenario: Unhandled exception is captured

- GIVEN Sentry is initialized
- WHEN a view raises an unhandled exception
- THEN `DjangoIntegration` reports it with its request context

#### Scenario: No call site imports the SDK

- GIVEN the application code under `reportes/`, `tipos_reporte/` and `usuarios/`
- WHEN it is inspected for observability plumbing
- THEN no module calls `sentry_sdk.capture_exception` or configures logging for Sentry

### Requirement: No Personally Identifiable Information Sent

The SDK MUST be initialized with `send_default_pii=False`, so request bodies,
cookies and user identifiers are not shipped to a third-party service by
default.

Captured reports carry field values from real field operations, so the default
MUST stay closed: widening it is a deliberate decision, never an inherited one.

#### Scenario: PII is not sent by default

- GIVEN Sentry is initialized
- WHEN its configuration is inspected
- THEN `send_default_pii` is `False`

### Requirement: Secret Handling for the DSN

`SENTRY_DSN` MUST be set only in the deployment environment and MUST NOT be
committed. `.env.example` MUST document it as an optional placeholder.

#### Scenario: DSN is not committed

- GIVEN the repository
- WHEN it is inspected
- THEN no real `SENTRY_DSN` value appears, and `.env.example` lists it empty

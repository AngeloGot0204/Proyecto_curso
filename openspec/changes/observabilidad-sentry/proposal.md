# Proposal: Observabilidad (Sentry)

Implements BACKLOG.md item #14. References ADR-0008 (resilience/observability).

## Intent

Production exception failures — Excel generation errors (`ProblemaDeGeneracion` and
subclasses), invalid report-type config, and any unhandled Django exception — are
currently only visible via stdlib `logger.exception` calls, which are not durably
searchable, alertable, or traceable in production on Vercel. ADR-0008 mandates
`sentry-sdk` integration for exception capture with trace, affected user, view, and
error grouping, but zero integration exists today. This change wires Sentry so
production errors become observable without requiring code changes at existing
call sites.

## Scope

### In Scope
- Add `sentry-sdk` dependency to `requirements.txt`/`pyproject.toml`.
- Wire `sentry_sdk.init()` in `config/settings.py`:
  - `dsn=os.environ.get("SENTRY_DSN")` — optional; `init()` is only called when a
    DSN is present, so local/dev environments without `SENTRY_DSN` work unaffected
    (deliberately NOT using the existing `require_env()` fail-loud pattern).
  - `environment=os.environ.get("VERCEL_ENV", "development")` — reuses Vercel's
    natively exposed `VERCEL_ENV`, no Sentry-specific Vercel integration needed.
  - `send_default_pii=False` — honors ADR-0008's own caution about PII capture.
- Rely on `sentry_sdk`'s `DjangoIntegration` (auto-enabled) to capture unhandled
  exceptions, and its default `LoggingIntegration` to auto-capture the existing
  `logger.exception` call in `reportes/views.py::generar` (backlog #7) — zero
  call-site changes needed there.
- A minimal test confirming `settings.py` does not crash whether `SENTRY_DSN` is
  set or absent (import/startup safety, not a live-network smoke test).

### Out of Scope
- "Sincronización" error capture — no sync code exists yet (backlog #10 not
  built); this is a forward-looking no-op, revisit when #10 lands.
- Custom alerting rules or dashboards — Sentry UI/project configuration, not code.
- Performance monitoring / tracing sample rates — ADR-0008 only asks for
  exception capture, not APM.
- Setting the actual `SENTRY_DSN` value in Vercel — noted as a deployment step
  below, not implemented in code.

## Capabilities

### New Capabilities
- `observabilidad-errores`: Sentry SDK initialization and automatic exception
  capture (unhandled exceptions + existing `logger.exception` calls) across
  environments, gated by optional `SENTRY_DSN` configuration.

### Modified Capabilities
None.

## Approach

Config-only change in `config/settings.py`: call `sentry_sdk.init()` conditionally
when `SENTRY_DSN` is present, using `DjangoIntegration` (default-enabled) plus the
default `LoggingIntegration`. No changes to `reportes/views.py` or any view code —
the existing `logger.exception` call already integrates for free once the SDK is
initialized. Strict TDD: write a settings-import test first (asserts no exception
raised with and without `SENTRY_DSN` in the environment) before adding the
`sentry_sdk.init()` call.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `requirements.txt` / `pyproject.toml` | Modified | Add `sentry-sdk` dependency |
| `config/settings.py` | Modified | Add conditional `sentry_sdk.init()` |
| `reportes/tests/test_settings.py` (new) | New | Assert settings import doesn't crash with/without `SENTRY_DSN` |
| `reportes/views.py::generar` | None | No code change; existing `logger.exception` auto-captured |
| Vercel project env vars | Deployment step | Add `SENTRY_DSN` (Secret, production) — not code |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Backlog #14's AC references "sincronización" capture that has no code to instrument | Med | Explicitly scoped out with a note to revisit when backlog #10 lands |
| PII leakage via default Sentry capture | Low | `send_default_pii=False` set explicitly per ADR-0008 caution |
| Missing/misconfigured `SENTRY_DSN` in Vercel silently disables capture | Med | DSN-presence check test + explicit deployment step callout; app remains functional either way (optional, not fail-loud) |

## Rollback Plan

Revert the `config/settings.py` diff and remove `sentry-sdk` from
`requirements.txt`/`pyproject.toml`. Because initialization is conditional and
additive, no migrations or data changes are involved; rollback is a pure code
revert with no follow-up cleanup.

## Dependencies

- `sentry-sdk` PyPI package.
- A Sentry project + DSN must exist and be set as `SENTRY_DSN` (Secret) in Vercel
  for production capture to activate; app functions without it.

## Success Criteria

- [ ] `sentry-sdk` installed and `sentry_sdk.init()` wired in `config/settings.py`.
- [ ] App starts successfully with `SENTRY_DSN` unset (local/dev unaffected).
- [ ] Test suite includes a passing settings-import test covering both DSN-present
      and DSN-absent cases.
- [ ] No changes required in `reportes/views.py::generar` — its `logger.exception`
      call is captured automatically once Sentry is initialized.

# Exploration: Observabilidad (Sentry) — Backlog #14

## Current State

**ADR-0008**'s Sentry decision is a single sentence: *"Integrar `sentry-sdk` en Django para capturar excepciones en producción, con traza, usuario afectado, vista implicada y agrupación de errores repetidos."* No DSN/sample-rate/environment-separation detail specified. One warning: `send_default_pii` "debe evaluarse antes de activarse" — PII scrubbing is an open decision, not a spec.

**Zero integration today** — confirmed: `config/settings.py` has no `sentry_sdk` references; `requirements.txt`/`pyproject.toml` don't include `sentry-sdk`.

**"Generación y sincronización" is partially aspirational.** ADR-0008's own context says sync failures are already covered by ADR-0004 (queue, manual retry, idempotency); ADR-0008 covers three remaining failure modes: `.xlsx` generation failure, invalid tipo-de-reporte config, lack of production visibility. `grep -r "sincroniz"` across `*.py` returns nothing — no sync code surface exists (backlog #10 not built). The real, concrete integration point today is only generation:

```python
# reportes/views.py:305-310
try:
    buffer = generador.generar_reporte(reporte.definicion, valores)
except ProblemaDeGeneracion:
    logger.exception(
        "Fallo al generar el documento del reporte #%s", reporte.id
    )
```

`generar()`'s docstring literally says: *"logged via stdlib `logger.exception`, Sentry-ready but not wired"*. `ProblemaDeGeneracion` is the base class of `PlantillaIlegible`/`ValoresIncompletos`.

**Vercel + Sentry**: the official marketplace integration is primarily documented for JS/Next.js — auto-injects `SENTRY_ORG`/`SENTRY_PROJECT`/`SENTRY_AUTH_TOKEN`/`NEXT_PUBLIC_SENTRY_DSN`, derives environment from `VERCEL_ENV` with `vercel-` prefix. For a Django/Python project those JS-specific vars don't directly apply. Pragmatic path: own `SENTRY_DSN` var (Secret type), following `DATABASE_URL`'s existing pattern, reading `VERCEL_ENV` (natively exposed by Vercel, no Sentry integration required) for `sentry_sdk.init(environment=...)`.

**Credential management** — should follow `settings.py`'s existing `require_env()` pattern (fail-loud), though DSN could reasonably be optional (dev/local without Sentry) — a design decision, not resolved by the ADR.

**Cost/free tier** — informational: ADR-0008 itself states the free plan "cubre holgadamente el volumen de este proyecto."

**Testability** — `sentry_sdk.init()` is config-only, minimal testable surface. What COULD be tested: a Django system check/startup assertion about `SENTRY_DSN`, a smoke-test view that deliberately raises (manual, not CI, needs real network), or extracting init logic into a pure testable function. No `test_settings.py` exists today.

**Logging/conventions** — no custom `LOGGING` dict in `settings.py` (Django default). This means `sentry_sdk`'s default `LoggingIntegration` (breadcrumbs at INFO+, events at ERROR+) would automatically capture `generar()`'s `logger.exception` with zero call-site changes, and Sentry's Django integration also independently captures unhandled exceptions.

## Affected Areas
- `requirements.txt`/`pyproject.toml` — add `sentry-sdk`.
- `config/settings.py` — `sentry_sdk.init()` wiring.
- No changes needed to `reportes/views.py::generar` — `logger.exception` is already the correct integration point.
- Vercel env vars — new `SENTRY_DSN` (Secret), read `VERCEL_ENV` (already available).

## Recommendation
Proceed to `sdd-propose` with a narrow scope: (a) `sentry-sdk` dependency + `settings.py` wiring, DSN optional (dev/local without Sentry works fine), (b) environment via `VERCEL_ENV`, (c) `send_default_pii=False` by default (honors the ADR's warning), (d) explicitly descope "sincronización" error capture as forward-looking/no-op (no code exists to capture), (e) no changes to `reportes/views.py::generar` — its `logger.exception` is already the correct integration point.

## Open Decisions (must be settled in proposal)
1. DSN optional (dev/local runs fine without Sentry) vs required (fail-loud like other env vars)?
2. `send_default_pii` — leave `False` (ADR's own caution) or enable?

## Risks
- Backlog #14's AC mentions "sincronización" but no sync code exists to instrument — risk of misaligned expectations if read as a blocking requirement; it's a no-op for now, revisit when #10 lands.
- PII handling remains an open ADR decision — must be settled at design time.
- No automated test surface for SDK init beyond a possible startup check.

## Key Learnings
1. ADR-0008's Sentry decision is a single sentence with no DSN/sample-rate/environment detail — implementation freedom is wide.
2. The only real, concrete Sentry integration point today is `reportes/views.py::generar`'s existing `logger.exception` call — no sync code surface exists yet (backlog #10 not built).
3. Vercel's official Sentry marketplace integration targets JS/Next.js env var conventions; a Django project should use its own `SENTRY_DSN` var following the `DATABASE_URL` pattern, reading Vercel's natively-exposed `VERCEL_ENV`.
4. Django's default logging config means Sentry's `LoggingIntegration` would auto-capture the existing `logger.exception` call with zero call-site changes.

**Next**: sdd-propose

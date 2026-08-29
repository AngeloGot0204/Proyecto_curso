# Apply Progress: Observabilidad (Sentry)

Status: **All tasks complete (4/4 phases, 16/16 checklist items)**.

## Summary

Wired `sentry-sdk` into `config/settings.py`, gated on the optional
`SENTRY_DSN` environment variable (plain `os.environ.get`, not
`require_env()` — DSN stays optional so local/dev works unaffected). No
changes to `reportes/views.py`; the existing `logger.exception` call in
`generar()` is auto-captured by the SDK's default `LoggingIntegration` once
initialized.

## TDD Cycle (strict TDD, RED confirmed before implementation)

1. **RED**: Added `reportes/tests/test_settings.py` (two cases: import with
   `SENTRY_DSN` unset, and with `SENTRY_DSN` set to a dummy DSN, each via
   `importlib.reload(config.settings)`), then added the `sentry_sdk` import
   and conditional `sentry_sdk.init()` call to `config/settings.py` *before*
   installing the package. Ran `pytest reportes/tests/test_settings.py` and
   confirmed it failed for the right reason:
   `ImportError: No module named 'sentry_sdk'`.
2. **GREEN**: Added `sentry-sdk>=2.0,<3` to `requirements.txt` and
   `pyproject.toml`, installed it into `.venv`, re-ran the test — both cases
   passed.
3. **REFACTOR / Verification**: Ran the full project test suite twice.
   - First attempt (concurrent/overlapping background pytest invocations
     against the shared remote Neon `test_reportes_dev` database) produced
     48 failed / 197 passed / 12 errors, all `UniqueViolation`/leftover-data
     symptoms — caused by running multiple `--reuse-db` sessions against the
     same physical test database at once, not by this change.
   - Clean, single, serial re-run with `--create-db` (fresh test schema):
     **257 passed, 0 failed, in 557.37s**. Confirms no regressions from the
     Sentry wiring.
   - Confirmed `reportes/views.py` has zero diff (`git diff reportes/views.py`
     is empty) — `generar()`'s `logger.exception` call is untouched.
   - `python manage.py check` (SENTRY_DSN unset) surfaces one **pre-existing,
     unrelated** local warning: `4_0.E001` on `DJANGO_CSRF_TRUSTED_ORIGINS`
     in the local `.env` (missing an `http(s)://` scheme). This is a local
     dev `.env` content issue, not caused by this change — `config/settings.py`
     itself does not touch `CSRF_TRUSTED_ORIGINS`, and the full test suite
     (which does not depend on `manage.py check`) confirms settings import
     succeeds cleanly with `SENTRY_DSN` unset.

## Files changed

- `config/settings.py` — added `sentry_sdk` + `DjangoIntegration` import,
  `_sentry_dsn = os.environ.get("SENTRY_DSN")`, conditional
  `sentry_sdk.init(dsn=..., environment=os.environ.get("VERCEL_ENV", "development"), integrations=[DjangoIntegration()], send_default_pii=False)`.
- `requirements.txt` — added `sentry-sdk>=2.0,<3`.
- `pyproject.toml` — added `sentry-sdk>=2.0,<3` to `[project].dependencies`.
- `reportes/tests/test_settings.py` (new) — settings import/startup safety
  test, both DSN-present and DSN-absent cases.
- `reportes/views.py` — **untouched**, as required by scope.

## Pending user action item (manual, cannot be done by the agent)

**A maintainer must, after merge:**
1. Create a Sentry project (or reuse an existing org's project) and obtain
   its DSN.
2. In the Vercel project dashboard → **Settings → Environment Variables**,
   add `SENTRY_DSN` as a **Secret**-type variable scoped to the
   **Production** environment (following the same pattern as
   `DATABASE_URL`/`DJANGO_SECRET_KEY`).
3. No action needed for `VERCEL_ENV` — it is natively provided by Vercel at
   runtime and requires no additional configuration; `config/settings.py`
   already reads it via `os.environ.get("VERCEL_ENV", "development")`.

Until `SENTRY_DSN` is set in Vercel, the app continues to function normally
(Sentry capture stays inactive/no-op) — this is by design (optional DSN, not
fail-loud).

## Deviations from design

None. Implementation matches `proposal.md`'s Approach section exactly:
config-only change, `DjangoIntegration` + default `LoggingIntegration`,
`send_default_pii=False`, `VERCEL_ENV`-derived environment, zero
`reportes/views.py` changes.

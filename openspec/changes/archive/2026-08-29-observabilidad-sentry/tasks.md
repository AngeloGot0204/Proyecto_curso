# Tasks: Observabilidad (Sentry)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~50-70 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Wire `sentry-sdk` dep + conditional `init()` in `config/settings.py`, covered by settings-import test | PR 1 | `pytest reportes/tests/test_settings.py` | `python manage.py check` with/without `SENTRY_DSN` set | Revert `config/settings.py` diff + remove `sentry-sdk` from `requirements.txt`/`pyproject.toml`; no migrations/data involved |

## Phase 1: RED — Failing Test First

- [x] 1.1 Create `reportes/tests/test_settings.py` with two cases: (a) reload/import Django settings with `SENTRY_DSN` unset in `os.environ` — assert no exception raised; (b) same with `SENTRY_DSN` set to a dummy DSN string — assert no exception raised. Use `importlib.reload(settings)` or a subprocess/`django.setup()` re-entry pattern isolated per test.
- [x] 1.2 Run `pytest reportes/tests/test_settings.py` and confirm it fails — reason must be `ModuleNotFoundError: sentry_sdk` (or equivalent import error), not an unrelated failure. If it fails for a different reason, fix the test setup before proceeding.

## Phase 2: GREEN — Implementation

- [x] 2.1 Add `sentry-sdk` to `requirements.txt`.
- [x] 2.2 Add `sentry-sdk` to `pyproject.toml` dependencies.
- [x] 2.3 In `config/settings.py`, import `sentry_sdk` and `sentry_sdk.integrations.django.DjangoIntegration`.
- [x] 2.4 In `config/settings.py`, add: `_sentry_dsn = os.environ.get("SENTRY_DSN")` (plain `os.environ.get`, NOT `require_env()` — DSN stays optional).
- [x] 2.5 In `config/settings.py`, gate `sentry_sdk.init(dsn=_sentry_dsn, environment=os.environ.get("VERCEL_ENV", "development"), integrations=[DjangoIntegration()], send_default_pii=False)` behind `if _sentry_dsn:`. Do not pass a custom `LoggingIntegration` — rely on the SDK default so `logger.exception` in `reportes/views.py::generar` is auto-captured with zero call-site changes.
- [x] 2.6 Run `pytest reportes/tests/test_settings.py` and confirm both cases now pass (GREEN).

## Phase 3: REFACTOR / Verification

- [x] 3.1 Run full test suite (`pytest`) to confirm no regressions from the settings change.
- [x] 3.2 Manually confirm `python manage.py check` succeeds with `SENTRY_DSN` unset (local/dev unaffected).
- [x] 3.3 Confirm no changes were made to `reportes/views.py` — `generar()`'s existing `logger.exception` call remains untouched, per proposal scope.

## Phase 4: Deployment Documentation (Manual — Post-Merge)

- [x] 4.1 Add a short note (README or deployment doc, per project convention) stating: after merge, a maintainer must create a Sentry project, obtain its DSN, and set `SENTRY_DSN` as a **Secret**-type environment variable in the Vercel project settings (production environment) — this is a manual action outside agent/code scope, no Sentry account access available to the agent.
- [x] 4.2 Note in the same doc that `VERCEL_ENV` is natively provided by Vercel and requires no additional configuration.

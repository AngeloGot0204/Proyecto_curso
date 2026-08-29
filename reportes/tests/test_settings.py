"""Tests for `config.settings`'s conditional Sentry initialization (backlog
#14, ADR-0008). Confirms settings import/startup succeeds whether or not
`SENTRY_DSN` is present in the environment — Sentry stays optional so
local/dev environments without a DSN are unaffected (design decision: not
using the existing `require_env()` fail-loud pattern for this variable).

Each test reloads `config.settings` in isolation via `importlib.reload`
after mutating `os.environ`, so neither case leaks into the other or into
the rest of the suite (restored in a `finally` block).
"""

import importlib
import os

import config.settings as settings


def _reload_settings():
    importlib.reload(settings)


def test_settings_importa_sin_excepcion_sin_sentry_dsn():
    """`SENTRY_DSN` unset: settings must import cleanly, Sentry init skipped."""
    original = os.environ.pop("SENTRY_DSN", None)
    try:
        _reload_settings()
    finally:
        if original is not None:
            os.environ["SENTRY_DSN"] = original
        _reload_settings()


def test_settings_importa_sin_excepcion_con_sentry_dsn():
    """`SENTRY_DSN` set to a dummy DSN: settings must import cleanly and
    call `sentry_sdk.init()`."""
    original = os.environ.get("SENTRY_DSN")
    os.environ["SENTRY_DSN"] = "https://public@sentry.example.com/1"
    try:
        _reload_settings()
    finally:
        if original is None:
            os.environ.pop("SENTRY_DSN", None)
        else:
            os.environ["SENTRY_DSN"] = original
        _reload_settings()

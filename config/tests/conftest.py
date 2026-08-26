"""
Shared fixtures for `config/tests/`.

`config/settings.py` is a single environment-driven module (design decision
1). The `override_settings` / `settings` fixtures patch the already-resolved
settings object and never re-execute `settings.py`, so they cannot observe
`require_env()` raising or `require_bool_env()` rejecting a bad value. The
probe below runs the real file, top to bottom, under a controlled
environment, and observes what that execution actually produces.
"""

import importlib.util
from pathlib import Path

import pytest

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.py"


def _load_settings(monkeypatch, env):
    """Execute config/settings.py in a throwaway namespace under `env`.

    Two properties are load-bearing:

    - `sys.modules["config.settings"]` is never touched. `importlib.reload()`
      would poison `django.conf.settings`'s lazy wrapper for the rest of the
      test session, so a fresh module object is executed and returned instead.
    - `dotenv.load_dotenv` is monkeypatched to a no-op so the "unset variable"
      tests are decided only by `env`, never by the developer's own `.env`.
    """
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location(
        "config._settings_probe", SETTINGS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # deliberately NOT put in sys.modules
    return module


@pytest.fixture
def load_settings(monkeypatch):
    """Fixture wrapper around `_load_settings` bound to this test's monkeypatch."""

    def _load(env):
        return _load_settings(monkeypatch, env)

    return _load


# A production-like environment reused by several tests. The secret key is
# exactly 50 characters with high character variety on purpose: Django's
# security.W009 fires below 50 characters or fewer than 5 distinct
# characters, and A8 runs at --fail-level WARNING, so a short fixture key
# would fail that test for a reason unrelated to anything this change does.
PROD_ENV = {
    "DJANGO_SECRET_KEY": "x" * 26 + "yzYZ0123456789abcdefghij",  # 50 chars
    "DATABASE_URL": "postgresql://u:p@ep-demo-pooler.eu-central-1.aws.neon.tech/db",
    "DJANGO_ALLOWED_HOSTS": "example.vercel.app",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.vercel.app",
    "DJANGO_HTTPS_ONLY": "True",
    "DJANGO_DEBUG": None,  # deliberately absent
}

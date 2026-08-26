"""
Behavioral and value assertions over `config/settings.py`'s deployment
settings, exercised through the fresh-module-execution probe in
`conftest.py` (never `override_settings`, never `importlib.reload`).

Strict TDD honesty (design, "Strict TDD: which tests are written when"):

- Genuine behavioral RED: test_a3, test_a8_check_deploy_clean_at_warning_level,
  test_a12, test_a13 — each asserts a real failure the code must produce, not
  merely a name's presence.
- Weak name-absence RED: test_a1, test_a2, test_a4, test_a5, test_a10,
  test_a11, test_a14 — before the settings edit these fail with
  AttributeError/KeyError because the name is absent, not because a wrong
  value was asserted. A name-absence RED cannot distinguish "not written"
  from "written wrong", so it proves less than a behavioral RED. test_a11 is
  the most valuable of this group despite the weak RED: it is the only guard
  on local development (design 11.5).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.tests.conftest import PROD_ENV

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_a1_static_root_set_no_whitenoise(load_settings):
    """
    Spec: Static file serving without WhiteNoise (Automatable).
    Weak name-absence RED.
    """
    module = load_settings(PROD_ENV)

    assert str(module.STATIC_ROOT).endswith("staticfiles")
    assert not any("whitenoise" in mw.lower() for mw in module.MIDDLEWARE)
    assert not hasattr(module, "STORAGES")


def test_a2_conn_max_age_is_zero(load_settings):
    """
    Spec: Neon pooled endpoint with CONN_MAX_AGE=0 (Automatable).
    Weak name-absence RED.
    """
    module = load_settings(PROD_ENV)

    assert module.DATABASES["default"]["CONN_MAX_AGE"] == 0


def test_a3_missing_allowed_hosts_fails_loud(load_settings):
    """
    Spec: ALLOWED_HOSTS fails loud (Automatable).
    Genuine behavioral RED: today ALLOWED_HOSTS defaults instead of raising.
    """
    env = {**PROD_ENV, "DJANGO_ALLOWED_HOSTS": None}

    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        load_settings(env)


def test_a4_csrf_trusted_origins_from_env_default_empty(load_settings):
    """
    Spec: CSRF trust for the deployment origin (Automatable).
    Weak name-absence RED.
    """
    module = load_settings(PROD_ENV)
    assert "https://example.vercel.app" in module.CSRF_TRUSTED_ORIGINS

    env = {**PROD_ENV, "DJANGO_CSRF_TRUSTED_ORIGINS": None}
    module_unset = load_settings(env)
    assert module_unset.CSRF_TRUSTED_ORIGINS == []


def test_a5_secure_proxy_ssl_header_exact_tuple(load_settings):
    """
    Spec: HTTPS detection behind Vercel's proxy (Automatable).
    Weak name-absence RED — presence only, cannot prove behavior (design
    decision 4); ML-4/ML-6 are the only proof of behavior.
    """
    module = load_settings(PROD_ENV)

    assert module.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_a8_debug_is_false_under_prod_env(load_settings):
    """
    Spec: Secrets handling — DEBUG is False (Automatable).
    Regression guard, not RED-tested behavior: `DEBUG`'s defaulting comes
    from item #1 and is unchanged by this diff, so this assertion is
    vacuously green from the first run. No RED was manufactured for it.
    """
    module = load_settings(PROD_ENV)

    assert module.DEBUG is False


def test_a8_check_deploy_clean_at_warning_level():
    """
    Spec: Secrets handling — `check --deploy --fail-level WARNING` exits 0
    (Automatable, amended). Genuine behavioral RED, upgraded by Decision 11:
    before the settings edit, W004/W008/W012/W016 are all emitted under a
    production-like environment, so this fails today at WARNING level.

    The subprocess argument vector is a fixed literal list, `shell=True` is
    never used, `cwd` is derived from `__file__`, and `env` is built from an
    explicit dict so the developer's real DATABASE_URL/DJANGO_SECRET_KEY
    never reach the child. The fixture secret key is a synthetic literal,
    never a real key. `check --deploy` performs no database checks unless
    `--database` is passed, so no database connection is attempted.

    Unlike the `_load_settings` probe (which monkeypatches `load_dotenv` to a
    no-op), this is a *real* subprocess: `manage.py` calls the real
    `load_dotenv()`, which fills in any variable absent from `env` from the
    developer's own local `.env`. `PROD_ENV["DJANGO_DEBUG"]` is `None` to mean
    "absent" for the mocked probe, but a real local `.env` sets
    `DJANGO_DEBUG=True` for local development (design decision 9) — so, for
    this real subprocess only, `DJANGO_DEBUG` is set explicitly to `"False"`
    to make the check deterministic regardless of the developer's `.env`.
    """
    env = os.environ.copy()
    env.update({key: value for key, value in PROD_ENV.items() if value is not None})
    env["DJANGO_DEBUG"] = "False"

    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_a10_https_only_true_hardens_transport(load_settings):
    """
    Spec: HTTPS-only transport hardening — DJANGO_HTTPS_ONLY=True (Automatable).
    Weak name-absence RED.
    """
    module = load_settings(PROD_ENV)  # PROD_ENV already carries "True"

    assert module.SESSION_COOKIE_SECURE is True
    assert module.CSRF_COOKIE_SECURE is True
    assert module.SECURE_SSL_REDIRECT is True
    assert module.SECURE_HSTS_SECONDS == 3600
    assert module.SECURE_HSTS_INCLUDE_SUBDOMAINS is True


def test_a11_https_only_false_disables_transport_hardening(load_settings):
    """
    Spec: HTTPS-only transport hardening — DJANGO_HTTPS_ONLY=False (Automatable).
    Weak name-absence RED, but the most valuable test of this group: it is
    the only guard proving local development over plain HTTP stays unaffected
    (design 11.5) — without it, DJANGO_HTTPS_ONLY=True set locally would turn
    every request in usuarios/tests/test_login.py into a 301.
    """
    env = {**PROD_ENV, "DJANGO_HTTPS_ONLY": "False"}
    module = load_settings(env)

    assert module.SESSION_COOKIE_SECURE is False
    assert module.CSRF_COOKIE_SECURE is False
    assert module.SECURE_SSL_REDIRECT is False
    assert module.SECURE_HSTS_SECONDS == 0


def test_a12_missing_https_only_fails_loud(load_settings):
    """
    Spec: HTTPS-only transport hardening — unset DJANGO_HTTPS_ONLY (Automatable).
    Genuine behavioral RED: no value is safe in both environments (design
    11.2), so absence must raise, not default.
    """
    env = {**PROD_ENV, "DJANGO_HTTPS_ONLY": None}

    with pytest.raises(ImproperlyConfigured, match="DJANGO_HTTPS_ONLY"):
        load_settings(env)


@pytest.mark.parametrize("bad_value", ["true", "1", "yes", ""])
def test_a13_malformed_https_only_is_rejected(load_settings, bad_value):
    """
    Spec: HTTPS-only transport hardening — malformed DJANGO_HTTPS_ONLY
    (Automatable). Genuine behavioral RED and the strongest test in the
    change (design): it asserts a *rejection* of a plausible-looking value,
    which no stub implementation that merely defines the name can satisfy.
    The misspelling direction is dangerous here — "true" compared against
    the exact string "True" would silently disable every transport
    protection in production if not strictly parsed.
    """
    env = {**PROD_ENV, "DJANGO_HTTPS_ONLY": bad_value}

    with pytest.raises(ImproperlyConfigured, match="DJANGO_HTTPS_ONLY"):
        load_settings(env)


def test_a14_hsts_preload_refused_and_silenced(load_settings):
    """
    Spec: HTTPS-only transport hardening — preload refusal is deliberate and
    pinned (Automatable). Weak name-absence RED. Prevents a future
    contributor from "fixing" security.W021 by flipping preload on:
    vercel.app is a public suffix this project cannot submit to the preload
    list (design 11.3).
    """
    module = load_settings(PROD_ENV)

    assert module.SECURE_HSTS_PRELOAD is False
    assert "security.W021" in module.SILENCED_SYSTEM_CHECKS

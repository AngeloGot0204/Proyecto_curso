# Design: Deployment and Production Infrastructure (backlog #2)

> Engram: `sdd/despliegue-e-infraestructura/design` (observation 53)
>
> Inputs: proposal (#51), delta spec (#52 — 11 requirements, **19 scenarios**:
> Automatable 9 / Manual-live 5 / Manual-console 5), settled decisions (#50 — nine,
> all closed), exploration (#49), ADR-0009.
>
> **Revision 2.** The user answered this document's one open decision and chose the
> option it did not recommend: the four `check --deploy` warnings
> (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS) are
> **in scope for this item**. Resolved in **Decision 11**, which introduces an explicit
> `DJANGO_HTTPS_ONLY` discriminator rather than letting the application infer its
> environment. This revision also narrows the brittle hygiene assertions in A6/A7 and
> reconciles two platform assumptions against exploration findings (#49).
>
> **This revision requires a spec amendment.** Decision 11 adds one requirement and
> seven scenarios that spec #52 does not yet contain. Proposed wording is at the end of
> this document under *Required Spec Amendment*. `sdd-tasks` must not run against the
> current #52 counts.
>
> **Documentation freshness caveat.** This phase had no network or documentation tool
> available. Claims that depend on current platform behavior are either cited to #49
> (which did fetch official documentation) or marked **[verify-at-apply]** with their
> failure symptom and fallback, rather than asserted.

## Technical Approach

Item #1 shipped a single environment-driven `config/settings.py` with a fail-loud
`require_env()`. This change adds **twelve settings and two environment variables** to
that same module — nothing structural — and moves every remaining production fact into
the Vercel dashboard, where it is a per-environment *value*, never code.

The guiding rule: **the application must never infer which environment it is in.** There
is no `if PRODUCTION:` branch and no `if not DEBUG:` branch anywhere. Where a genuine
local-vs-production difference exists — and Decision 11 introduces the only one — the
application is **told**, through an explicit variable, rather than left to guess.
Production, Preview and local differ only in the values of `DATABASE_URL`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_HTTPS_ONLY` and
`DJANGO_DEBUG`. This is why no settings split and no `vercel.json` are introduced: both
would be places where an environment could be described twice and drift.

The whole diff to production code is this, in `config/settings.py`:

```python
def require_bool_env(name):
    """require_env() for a strict boolean. Rejects 'true', '1', 'yes'."""
    value = require_env(name)
    if value not in ("True", "False"):
        raise ImproperlyConfigured(
            f"{name} must be exactly 'True' or 'False', got {value!r}"
        )
    return value == "True"


ALLOWED_HOSTS = [h.strip() for h in require_env("DJANGO_ALLOWED_HOSTS").split(",")]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Vercel terminates TLS at its edge and forwards the original scheme in this
# header, so request.is_secure() is False without it — see Decision 4.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Is this deployment served exclusively over HTTPS? A deployment fact the app is
# told, never infers. No value is safe in both places, so it is fail-loud
# (Decision 11).
HTTPS_ONLY = require_bool_env("DJANGO_HTTPS_ONLY")

SESSION_COOKIE_SECURE = HTTPS_ONLY
CSRF_COOKIE_SECURE = HTTPS_ONLY
SECURE_SSL_REDIRECT = HTTPS_ONLY

# One hour, deliberately short: browsers cache HSTS, so it cannot be withdrawn
# from the server side (Decision 11).
SECURE_HSTS_SECONDS = 3600 if HTTPS_ONLY else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS_ONLY
SECURE_HSTS_PRELOAD = False

# security.W021 asks for SECURE_HSTS_PRELOAD. The browser preload list is keyed
# on registrable domains; vercel.app is a public suffix this project does not
# own, so the directive could never take effect. Silenced deliberately, with a
# reason — not ignored (Decision 11).
SILENCED_SYSTEM_CHECKS = ["security.W021"]

STATIC_ROOT = BASE_DIR / "staticfiles"

# Connection-per-request: Neon's pooler absorbs the churn (Decision 6).
DATABASES["default"]["CONN_MAX_AGE"] = 0
```

Everything else in this change is `.env.example`, tests, and manual console work.

## Architecture Decisions

### Decision 1: `config/settings.py` stays a single environment-driven module

**Choice.** No `base.py`/`production.py` split. One module, all variance through the
environment, exactly as item #1's decision 5 established.

| Option | Cost | Verdict |
|---|---|---|
| Single env-driven module *(chosen)* | Production-only values are invisible in code — you must read the Vercel dashboard to know them | **Chosen** |
| `config/settings/{base,production,local}.py` | `DJANGO_SETTINGS_MODULE` must now be set correctly in **four** places (Vercel Production, Vercel Preview, `pytest.ini`, `manage.py`/`wsgi.py`); Vercel's Django detection reads that variable, so a wrong value is a boot failure with a confusing message | Rejected |
| Single module + `if not DEBUG:` production block | Reintroduces the environment branch this design exists to avoid, and makes local runs structurally unable to exercise the production path | Rejected |

**Rationale.** The split only pays off when environments differ *structurally* —
different apps, different middleware, different backends. Here they differ only in
five string values. Paying a four-place synchronisation cost to express five strings is
a bad trade, and it is a trade a beginner pays repeatedly, every time a command is run
from a shell that forgot the variable.

**Consequence — how tests exercise production-like configuration.** This is the real
cost of the single module and it must be answered concretely, because the three obvious
mechanisms are not equivalent:

| Mechanism | Can it prove what this change adds? |
|---|---|
| `override_settings` / the `settings` fixture | **No.** It patches the already-resolved settings object; it never re-executes `settings.py`. It therefore cannot observe `require_env()` raising, cannot observe the `.split(",")` derivation, cannot observe `require_bool_env` rejecting a bad value, and would happily "pass" against a module that hardcodes the value. It proves nothing about the code this change writes. |
| A dedicated `config/settings_test_production.py` | **No** — and it actively harms. It is a second copy of the settings the test then asserts against itself; the production module could drift and the suite would stay green. It also contradicts Decision 1. |
| **Environment injection + fresh module execution** *(chosen)* | **Yes.** It runs the actual file, top to bottom, under a controlled environment, and observes what that execution produces — including exceptions. |

The mechanism, in `config/tests/conftest.py`:

```python
import importlib.util
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.py"

def _load_settings(monkeypatch, env):
    """Execute config/settings.py in a throwaway namespace under `env`."""
    # config/settings.py calls load_dotenv() at import. Neutralise it so the
    # result depends only on `env`, never on the developer's local .env file.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("config._settings_probe", SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)      # deliberately NOT put in sys.modules
    return module
```

Two non-obvious properties, both load-bearing:

- **`sys.modules["config.settings"]` is never touched.** `importlib.reload()` would have
  been the shorter route and is the wrong one: `django.conf.settings` lazily wraps that
  module object, so reloading it under a fake environment would poison every test that
  runs afterwards in the same session.
- **`load_dotenv` is disabled inside the probe.** Without this, the "unset variable"
  tests would be decided by whether the developer's own `.env` happens to contain the
  variable — green on one machine, red on another. `monkeypatch.setattr` on the `dotenv`
  module attribute works because `settings.py` does `from dotenv import load_dotenv`
  *during* the exec we control.

A companion fixture supplies the production-like environment reused by several tests:

```python
PROD_ENV = {
    "DJANGO_SECRET_KEY": "x" * 25 + "yzYZ0123456789abcdefghij",   # 50 chars, high entropy
    "DATABASE_URL": "postgresql://u:p@ep-demo-pooler.eu-central-1.aws.neon.tech/db",
    "DJANGO_ALLOWED_HOSTS": "example.vercel.app",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.vercel.app",
    "DJANGO_HTTPS_ONLY": "True",
    "DJANGO_DEBUG": None,          # deliberately absent
}
```

The secret key length is not cosmetic: Django's `security.W009` fires below 50
characters or fewer than 5 distinct characters, and test A8 now runs at
`--fail-level WARNING` (Decision 11), so a short fixture key would fail the test for a
reason unrelated to anything this change does.

### Decision 2: `ALLOWED_HOSTS` becomes fail-loud through the existing `require_env()`

**Choice.** `ALLOWED_HOSTS = [h.strip() for h in require_env("DJANGO_ALLOWED_HOSTS").split(",")]`
— same helper, same failure shape, as `DJANGO_SECRET_KEY` and `DATABASE_URL`.

The `.strip()` is new relative to item #1's line. Django compares the request host
against `ALLOWED_HOSTS` entries **exactly**; a value typed as `a.vercel.app, b.vercel.app`
in a dashboard field yields the entry `" b.vercel.app"`, which matches nothing and
produces a 400 with no hint as to why. One list comprehension removes an entire class of
dashboard-typo debugging.

**Exact behaviour when `DJANGO_ALLOWED_HOSTS` is missing.** `require_env` raises
`ImproperlyConfigured("Missing required environment variable: DJANGO_ALLOWED_HOSTS")` at
**module import** — i.e. during `django.setup()`, before any URL is resolved. That means
it fails *everything*, not just the web server:

| Entry point | Behaviour with the variable missing |
|---|---|
| `manage.py <any command>` | Traceback, `ImproperlyConfigured`, non-zero exit |
| `python -m pytest` | Fails at collection — `pytest.ini` sets `DJANGO_SETTINGS_MODULE` |
| Vercel runtime (`config.wsgi`) | Function boots, request returns 500 |
| Vercel **build** (`collectstatic`) | Build fails — see the open question below |

**Confirming this does not break local work.** It does break it, until one line is added,
and that is stated plainly rather than glossed: after this change
`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1` **must** be present in the developer's local
`.env`. `DJANGO_SECRET_KEY` and `DATABASE_URL` already live there, so the file exists and
the habit exists. The mitigating property is the failure mode: it is a named exception at
startup, not a silent 400 four steps later. `sdd-tasks` must sequence the `.env` edit **in
the same work unit as** the settings edit, never after it — between the two, the entire
suite is red for a reason unrelated to any test. Decision 11 adds a second required line
to the same edit.

`.env.example` documents the variable as required so the next person cloning the repo
gets the value, not the traceback.

### Decision 3: `CSRF_TRUSTED_ORIGINS` from its own variable, defaulting to empty

**Choice.** A dedicated `DJANGO_CSRF_TRUSTED_ORIGINS` variable, comma-separated, full
origins **including the scheme**, defaulting to `[]` when unset.

| Option | Verdict |
|---|---|
| Derive from `ALLOWED_HOSTS` (`f"https://{h}"`) | Rejected. The two settings use **different wildcard syntaxes** — `ALLOWED_HOSTS` takes `.vercel.app` (leading dot), `CSRF_TRUSTED_ORIGINS` takes `https://*.vercel.app` (explicit asterisk). Naive derivation produces `https://.vercel.app`, which is not a valid trusted origin and matches nothing. It fails exactly in the environment (Preview) where it would matter. |
| Own variable, default `[]` *(chosen)* | Empty is the **restrictive** direction, so it satisfies item #1's rule that only restrictive defaults are allowed. Local `http://` development is unaffected because Django's strict Origin check applies to requests it considers secure. |
| Hardcode the Vercel domain in `settings.py` | Rejected — puts a deployment fact in code and breaks the "app never infers its environment" rule. |

**Values per environment.**

| Vercel environment | `DJANGO_CSRF_TRUSTED_ORIGINS` |
|---|---|
| Production | `https://<vercel-project>.vercel.app` |
| Preview | `https://*.vercel.app` |
| Development / local | unset |

**Preview deployments: covered, conditionally, and the condition is stated.** Preview
hostnames contain a per-deployment hash, so no fixed origin can cover them. They are
covered **only if** the Preview environment variable is set to the wildcard above. If it
is left unset, preview GETs work and **every preview POST — including login — fails with
403 "CSRF verification failed"**. That is the plainly-stated failure, not a surprise to
discover later.

The wildcard trusts *every* `*.vercel.app` origin, including other tenants' projects.
This is **accepted for Preview only**, because Preview is a throwaway environment pointed
at the disposable Neon dev branch (decision 4 of #50). Production keeps the single exact
origin and never uses the wildcard. Same reasoning drives
`DJANGO_ALLOWED_HOSTS=.vercel.app` in Preview and the exact hostname in Production.

### Decision 4: `SECURE_PROXY_SSL_HEADER` is a hardcoded constant

**Choice.** `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, written
literally in `settings.py`, not read from the environment.

**Rationale.** Unlike the other five values, this one is not an environment fact — it is
a statement about the proxy in front of the app, and there is exactly one proxy (Vercel's
edge) for every deployed environment. Locally there is no proxy, the header is absent, and
Django falls back to the real request scheme, so the constant is correct in all four
contexts. Making it configurable would create another dashboard field whose only correct
value is the one already written here.

**Why it is needed at all, precisely.** Django builds the expected CSRF origin from
`request.scheme`, which derives from `is_secure()`. Behind Vercel's TLS termination the
raw connection is HTTP, so without this setting `is_secure()` is `False`, Django expects
an origin of `http://<host>`, the browser sends `https://<host>`, and the login POST is
rejected. This is why Decisions 3 and 4 are a **pair**: setting either one alone still
leaves login broken in production.

**Restated: a wrong value fails silently.** `SECURE_PROXY_SSL_HEADER` is never validated.
`("HTTP_X_FORWARDED_PROTOCOL", "https")`, `("X-Forwarded-Proto", "https")` (missing the
`HTTP_` prefix and wrong separator), or `("HTTP_X_FORWARDED_PROTO", "HTTPS")` (wrong case)
all import cleanly, raise nothing, log nothing, and make `is_secure()` return `False` for
every request forever. The automatable scenario asserts the literal tuple and **that is
all it can prove**; scenarios ML-4 and ML-6 below are the only things that prove behaviour.

> **Blast radius increased by Decision 11.** Before this revision, a wrong
> `SECURE_PROXY_SSL_HEADER` broke login POSTs. With `SECURE_SSL_REDIRECT = True` now in
> scope, a wrong value turns **the entire site into an infinite redirect loop** — see
> Decision 11's redirect-loop analysis. This setting was already the most
> silently-dangerous line in the change; it is now also the most consequential, which is
> what justifies giving it two independent live checks (ML-4 and ML-6) rather than one.

**Accepted residual risk.** This setting instructs Django to trust a client-supplied
header. It is safe only because Vercel's edge overwrites `X-Forwarded-Proto` on every
request, so a spoofed value cannot reach the application. If the app were ever exposed by
any path that bypasses that edge, the setting becomes a spoofing surface. ADR-0009 fixes
Vercel as the only entry point, so this is accepted and recorded, not mitigated.

### Decision 5: static files — `STATIC_ROOT` only; no WhiteNoise, no `vercel.json`

**Choice.**

| Setting | Value | Note |
|---|---|---|
| `STATIC_URL` | `'static/'` | **Unchanged.** Django normalises it to `/static/`. Not churned. |
| `STATIC_ROOT` | `BASE_DIR / "staticfiles"` | New. `.gitignore` already carries `/staticfiles/` — item #1 anticipated this exact path. |
| `STATICFILES_DIRS` | **not set** | No project-level `static/` directory exists; templates carry no assets (ADR-0001: no frontend framework). |
| `STORAGES` | **not overridden** | Django's default `StaticFilesStorage`. |
| WhiteNoise | **not added** | Per #49: on Vercel it only affects `vercel dev`; in production the CDN serves the files regardless. A dependency for zero production effect. |

With `STATIC_ROOT` set, `collectstatic` collects the Django admin's own CSS/JS — which is
precisely what the live static scenario observes, because `/admin/` is the only styled
surface this project currently has.

**Platform behaviour — verified by exploration, not assumed.** Exploration #49 (Q1)
fetched Vercel's official Python/Django documentation, dated **2026-07-24**, and recorded
two findings this decision rests on:

1. Vercel auto-detects `manage.py`, reads `DJANGO_SETTINGS_MODULE`, and resolves
   `WSGI_APPLICATION` into a single Vercel Function. **No `vercel.json` is required for
   the entrypoint.** This project already sets `WSGI_APPLICATION = 'config.wsgi.application'`.
2. When `STATIC_ROOT` is set with a supported storage backend, **Vercel runs
   `collectstatic` automatically during its own build** and serves the output from its CDN
   at `STATIC_URL`.

Both were open questions in revision 1 and are **downgraded to cited findings** here. The
citation is roughly one month old and #49 itself advises re-checking, so the contingency
below is retained as a fallback, not as an expected branch.

**`vercel.json`: explicitly NOT created by this change.** Not "probably not needed" — not
created. Three candidate reasons, each dismissed on the record:

| Candidate reason | Verdict |
|---|---|
| Declare the entrypoint | Not needed — finding 1 above. |
| Raise `maxDuration` | Not needed — the Hobby default is far beyond anything a login or an admin page needs. Items #14/#4 may revisit. |
| `excludeFiles` to shrink the bundle | Not needed — the project is a few hundred KB against a large Python function limit. Premature. |

> **Contingency, if finding 2 no longer holds.** *Symptom:* deployment succeeds but
> `/static/admin/css/base.css` returns 404 and `/admin/` renders unstyled (ML-2 fails).
> *Fallback:* create a minimal `vercel.json` declaring a build command that runs
> `python manage.py collectstatic --noinput` — roughly 8 lines. Test A6 is written in its
> narrowed form (below) precisely so this contingency does **not** require touching the
> test: A6 asserts that no build configuration runs `migrate`, not that no build
> configuration exists.

### Decision 6: one `DATABASE_URL`, different value per environment

**Choice.** `DATABASES["default"]["CONN_MAX_AGE"] = 0`, set explicitly on the parsed dict,
and pooled-vs-direct endpoint selection expressed **entirely in the value of the existing
`DATABASE_URL`**. No `DATABASE_URL_POOLED`, no second variable.

**Why one variable.** A second variable would require code to choose between them — and
code that chooses is code that can choose wrong, in a way that only manifests under
production load. Endpoint selection is a deployment fact, so it belongs in the
deployment's value. The application stays unable to tell the difference, per the guiding
rule.

**Why `CONN_MAX_AGE` is set explicitly rather than left to the library default.**
`dj_database_url.parse()` already defaults to `0`, so this line changes nothing
functionally today. It is written anyway for two reasons: a library default is exactly the
kind of silent fallback item #1's Decision 3 rejected `django-environ` over, and the
spec's automatable scenario asserts `CONN_MAX_AGE == 0` — an assertion that must be pinned
by our code, not by a transitive dependency's default that a minor version bump could
change.

**Why `0` and not a persistent connection.** Vercel function instances are recycled
non-deterministically, so a long `CONN_MAX_AGE` does not achieve reuse across genuinely
separate instances; it mostly holds connections open that nothing will reuse. Neon's
pooler is the component that absorbs connection churn, and stacking Django-level
persistence on top of it is the configuration both providers' guidance warns against.
Django 5.1+ native pooling (`"pool": True`) was considered and rejected for the same
reason: an in-process pool inside a process the platform recycles at will.

**Endpoint mapping.**

| Vercel environment | Neon branch | Endpoint | Used by |
|---|---|---|---|
| Production | **production** (new, created in this item) | pooled (`-pooler`) | Deployed app runtime |
| Preview | dev (existing) | pooled (`-pooler`) | Preview deployments |
| Development | dev (existing) | direct | `vercel env pull` / `vercel dev` |
| — (local `.env`) | dev (existing) | direct | `runserver`, `pytest` — unchanged from item #1 |
| — (one-off shell) | target branch | **direct** | `migrate`, `createsuperuser` — Decision 7 |

> **[verify-at-apply] Open question — pooled endpoint and migrations.** Decision 7 routes
> `migrate` through the **direct** endpoint. Neon's pooler runs in transaction mode, where
> session-scoped operations (advisory locks, `CREATE INDEX CONCURRENTLY`) are unavailable.
> Simple Django DDL very likely works through the pooler too, but "very likely" is not a
> basis for a beginner's first production migration. *Symptom if the direct endpoint is
> unavailable:* none — this is a deliberate belt-and-braces choice, not a workaround for a
> known failure.

### Decision 7: migrations are a manual, out-of-band shell procedure

**Choice.** The developer runs `migrate` from their own machine, with `DATABASE_URL`
overridden **for that shell session only**. Never from a view, never from a build.

**The mechanism that makes this safe** is a property of item #1's settings module:
`load_dotenv()` **does not override variables already present in `os.environ`**. Therefore
a `$env:DATABASE_URL` set in PowerShell wins over the `.env` file for that session, and
closing the window restores the ordinary local configuration with no file edit to forget
to revert. This is why the procedure below never touches `.env`.

**Exact procedure (Windows PowerShell, from the repository root, `main` branch).** Values
in angle brackets come from the Neon console.

```powershell
# 1. Make sure the migrations you are about to apply are generated and committed.
.venv\Scripts\python.exe manage.py makemigrations
git status                      # expect: clean, or new migration files to commit

# 2. Point THIS SHELL ONLY at the Neon production branch, DIRECT endpoint.
#    (The direct host is the one WITHOUT "-pooler" in it.)
$env:DATABASE_URL = "<neon production branch DIRECT connection string>"

# 3. Look before you leap: which migrations are unapplied over there?
.venv\Scripts\python.exe manage.py showmigrations
#    Expect [ ] next to anything not yet applied to production.

# 4. Apply them.
.venv\Scripts\python.exe manage.py migrate

# 5. Confirm.
.venv\Scripts\python.exe manage.py showmigrations
#    Expect [X] on every line, no [ ] anywhere.

# 6. Drop the override so the next command in this window uses .env again.
Remove-Item Env:DATABASE_URL
```

**First-deployment order** (this is the only time the order is unusual, because the app is
unusable without an account):

1. Create the Vercel project, the Neon **production** branch, and the Blob store (manual, console).
2. Set every Production environment variable (Decision 9's table, including
   `DJANGO_HTTPS_ONLY=True` from Decision 11).
3. Run steps 1–6 above against the production branch — this creates the schema.
4. In the same style of shell (`$env:DATABASE_URL` set to the production **direct** URL),
   run `.venv\Scripts\python.exe manage.py createsuperuser`. Item #1's model forces
   `rol=administrador` and `is_staff=True` with no follow-up.
5. Trigger the first deploy (push to `main`).
6. Run the manual checklist (MC-1 … MC-6, ML-1 … ML-6).

**Steady-state order.** Because production data is disposable (decision 5 of #50),
migrations are applied **before** promoting the deploy that needs them, with no
expand/contract ceremony. If a migration turns out to be wrong, the recovery is to reset
the Neon production branch, not to write a reverse migration.

**The guard that makes "never automatic" checkable.** No application code invokes the
migration machinery, and no build configuration runs `migrate`. Test A6 asserts both
mechanically — in its narrowed form, so that adding a `pyproject.toml` for an unrelated
reason, or adding the Decision 5 contingency `vercel.json`, does not fail an
infrastructure test.

### Decision 8: Vercel Blob — provisioned, wired, deliberately not required

**Choice.** Environment variable **`BLOB_READ_WRITE_TOKEN`**.

**Where it is declared.** In the **Vercel dashboard only**, and not typed by hand:
connecting a Blob store to the project (Storage → the store → Connect Project) makes
Vercel inject this variable into the selected environments itself. The name is chosen by
the platform, not by us, which is precisely why item #11 should expect to find it under
that name. `.env.example` gains a **commented** line documenting that it exists and is
currently unused, so the next reader is not left guessing.

**It must NOT go through `require_env()` — confirmed, not corrected.** The reasoning given
in the brief is right, and the underlying principle is worth naming so item #11 knows when
to change it: `require_env()` is for variables whose **absence causes silent wrongness**.
A missing `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` or `DJANGO_HTTPS_ONLY` produces an
app that is subtly insecure; failing loudly is strictly better. A missing
`BLOB_READ_WRITE_TOKEN` today produces *nothing at all*, because no line of code reads it.
Requiring it would break every local `manage.py` command and every `pytest` run in
exchange for zero protection — friction with no safety on the other side of the trade.

**The correct promotion moment** is item #11, in the same commit as the first line of code
that reads the token. At that instant absence starts causing a real failure, and
`require_env("BLOB_READ_WRITE_TOKEN")` becomes correct.

### Decision 9: secrets — per-environment values, placeholders in the repository

**Complete variable matrix.** "—" means *deliberately not set*.

| Variable | Vercel Production | Vercel Preview | Vercel Development | Local `.env` | `.env.example` |
|---|---|---|---|---|---|
| `DJANGO_SECRET_KEY` | unique production value | separate value | separate value | existing | placeholder text |
| `DATABASE_URL` | prod branch, **pooled** | dev branch, **pooled** | dev branch, direct | dev branch, direct | placeholder text |
| `DJANGO_ALLOWED_HOSTS` | `<vercel-project>.vercel.app` | `.vercel.app` | `localhost,127.0.0.1` | `localhost,127.0.0.1` | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<vercel-project>.vercel.app` | `https://*.vercel.app` | — | — | commented example |
| **`DJANGO_HTTPS_ONLY`** | **`True`** | **`True`** | **`False`** | **`False`** | **`False`** |
| `DJANGO_DEBUG` | **—** | **—** | `True` | `True` | `False` |
| `BLOB_READ_WRITE_TOKEN` | injected by Vercel | injected by Vercel | injected by Vercel | — | commented, unused |
| `TEST_DB_NAME` | — | — | — | optional | placeholder |

`DJANGO_HTTPS_ONLY` is the only new row; Decision 11 explains it. Note that it is
**required in every environment**, including local — it is fail-loud, so `—` is not an
option for it anywhere.

**Production `DJANGO_SECRET_KEY` must be a newly generated value**, not the one from
`.env` — the local key has been on a development machine and is not a production secret.
Generate it with:

```powershell
.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**How `DJANGO_DEBUG` is guaranteed false in production — three independent layers:**

1. **Parsing.** `os.environ.get("DJANGO_DEBUG", "False") == "True"` only enables debug for
   the exact string `True`. Absent, empty, `true`, `1`, `yes` and `TRUE` all evaluate to
   `False`. Every typo fails in the safe direction.
2. **Absence.** The variable is **not created at all** in the Vercel Production
   environment. A variable that does not exist cannot be flipped by accident; creating one
   set to `False` would only advertise a switch worth toggling.
3. **Assertion.** Test A8 loads the settings under a production-like environment with the
   variable unset and asserts `DEBUG is False`, and runs `manage.py check --deploy`, whose
   `W018` check independently flags a debug-enabled deployment.

**Why `DJANGO_DEBUG` keeps its default while `DJANGO_HTTPS_ONLY` does not.** They look
alike and are treated oppositely, deliberately: `DJANGO_DEBUG`'s default (`False`) is safe
in *every* environment, so a default can never loosen security. `DJANGO_HTTPS_ONLY` has no
value that is safe in both places — `False` is required locally and dangerous in
production. A variable with no globally-safe default must be explicit. See Decision 11.

**Nothing secret enters the repository.** `.env` is already covered by `.gitignore` (`.env`
plus `.env.*` with `!.env.example`), unchanged by this item. `.env.example` carries keys
and placeholder values only; test A9 asserts both mechanically.

### Decision 10: deployment tests live in `config/tests/`

**Choice.** A new `config/tests/` package, not `usuarios/tests/` and not a top-level
`tests/`.

| Option | Verdict |
|---|---|
| `config/tests/` *(chosen)* | Tests sit next to the module they test, which is exactly item #1's app-local convention applied to `config/`. `pytest.ini`'s `python_files = test_*.py` collects it with **no configuration change**; `config` does not need to be an installed app because pytest collects by path. |
| `usuarios/tests/` | Rejected — makes the users app the home of deployment configuration, and item #3's `reportes` app would face the same "where does this go?" question with a worse precedent. |
| Top-level `tests/` | Rejected — item #1 explicitly chose app-local tests to avoid a growing parallel tree. |

### Decision 11: transport hardening driven by an explicit `DJANGO_HTTPS_ONLY` flag

**Settled by the user**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
`SECURE_SSL_REDIRECT` and HSTS are in scope for this item. Revision 1 deferred them; that
deferral is withdrawn. What follows resolves *how*, not *whether*.

#### 11.1 The discriminator: one variable naming a deployment fact

The problem is real and was correctly identified: `SESSION_COOKIE_SECURE = True` on
`http://localhost` means the browser silently never sends the cookie — login appears to do
nothing, with no error anywhere. And `SECURE_SSL_REDIRECT = True` under `runserver` would
301 `http://127.0.0.1:8000` to `https://127.0.0.1:8000`, which nothing serves. So a
discriminator is unavoidable. The only question is whether it is *inferred* or *injected*.

| Option | Verdict |
|---|---|
| `if not DEBUG:` | **Rejected.** It is inference: it re-derives "am I in production?" from a variable that means something else. It also couples two unrelated axes — a developer who sets `DJANGO_DEBUG=False` locally to reproduce a template error would silently acquire secure cookies and an SSL redirect, and their login would break for a reason that has nothing to do with what they changed. |
| `DJANGO_SECURE_COOKIES` boolean, default off *(the direction suggested)* | **Rejected on naming and on the default**, not on shape. The shape — one injected boolean — is right and is adopted. But the name describes two of the four settings it drives, so a reader who sees `SECURE_SSL_REDIRECT = SECURE_COOKIES` is entitled to be confused, and a fifth HTTPS-dependent setting later would make the name actively wrong. The default is addressed in 11.2. |
| **`DJANGO_HTTPS_ONLY` boolean, fail-loud** *(chosen)* | **Chosen.** It names the **deployment fact** — "this deployment is served exclusively over HTTPS" — rather than any setting derived from it. All six settings below are strict consequences of that one fact, so one variable cannot express an incoherent state such as "secure cookies on, SSL redirect off". It stays correctly named if a seventh HTTPS-dependent setting is added later. |

This keeps the guiding rule intact in its strong form: the application still never
*infers* its environment. It is **told** one fact, as injected data, and derives
everything mechanically from it.

#### 11.2 Why it is `require_bool_env`, not a safe default

Applying this document's own stated principle — `require_env()` is for variables whose
absence causes **silent wrongness** — rather than taking the convenient route:

- **Absence in production causes exactly that.** With a default of `False`, forgetting the
  variable in the Vercel Production dashboard produces a site that works perfectly and is
  quietly missing every transport protection, indefinitely, with nothing anywhere
  reporting it.
- **Item #1's rule points the same way.** Its Decision 3 states that only variables whose
  default is the *restrictive* direction may have one. `DJANGO_HTTPS_ONLY=False` is the
  permissive direction in production. It therefore does not qualify for a default under
  the project's own existing rule.
- **Nothing else can catch it.** Test A8 can prove the settings module is *capable* of
  producing a hardened configuration; no test in this repository can prove the Vercel
  dashboard actually has the variable. Fail-loud at boot is the only mechanism that
  converts "forgot to set it" into an unmissable event — the first deploy 500s
  immediately and ML-1 catches it, instead of the site looking fine forever.

**Cost, stated exactly:** one additional line in the local `.env`
(`DJANGO_HTTPS_ONLY=False`), added in the same edit as Decision 2's line. Local
development then keeps working over plain HTTP with no further steps; `pytest` and
`manage.py` keep working unchanged.

**Strict parsing, and the hole it closes.** `require_env` catches *absence*. It does not
catch a **misspelled value** — and here the misspelling direction is dangerous, because
`DJANGO_HTTPS_ONLY=true` compared against `"True"` yields `False`, silently disabling
every protection in production. `require_bool_env` (7 lines, shown in Technical Approach)
rejects anything that is not exactly `True` or `False`:

```
ImproperlyConfigured: DJANGO_HTTPS_ONLY must be exactly 'True' or 'False', got 'true'
```

This is deliberately **not** retrofitted onto `DJANGO_DEBUG`. That variable's typo
direction is safe (`true` → `False` → debug off), retrofitting would change item #1's
established behaviour, and it would break any existing `.env` containing
`DJANGO_DEBUG=true`. Scope discipline: the strict helper is introduced for the variable
that needs it and applied only there.

#### 11.3 The exact settings, and the HSTS duration

```python
SESSION_COOKIE_SECURE = HTTPS_ONLY
CSRF_COOKIE_SECURE = HTTPS_ONLY
SECURE_SSL_REDIRECT = HTTPS_ONLY
SECURE_HSTS_SECONDS = 3600 if HTTPS_ONLY else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS_ONLY
SECURE_HSTS_PRELOAD = False
SILENCED_SYSTEM_CHECKS = ["security.W021"]
```

**`SECURE_HSTS_SECONDS = 3600` (one hour).** HSTS is the one setting here that a server
cannot fully retract: the browser caches the policy, so lowering it requires serving
`max-age=0` and waiting for every previous visitor to return before their cached policy
expires. A year-long `max-age` is the conventional production value and is the wrong
value *here*, for two reasons specific to this deployment:

1. The project does not own the domain. `<vercel-project>.vercel.app` is a name held only
   while the Vercel project exists. If this demo is torn down and the name is later
   released, a year-long HSTS policy would have been asserted on behalf of whoever holds
   that name next.
2. One hour is genuinely useful and fully self-healing. It protects a user across a
   working session, and any mistake — including a mistaken deployment — expires on its own
   within an hour with no intervention.

Raising it to `31536000` later is a one-line, deliberately-reviewed code change. That
friction is the correct amount for a header that is hard to withdraw.

**`SECURE_HSTS_INCLUDE_SUBDOMAINS = True` (when HTTPS-only).** Harmless and correct: no
subdomains of `<vercel-project>.vercel.app` exist, so it constrains nothing that exists,
and HSTS applies downward only — it cannot affect `vercel.app` itself or any sibling
project. It also closes Django's `security.W005`.

**`SECURE_HSTS_PRELOAD = False` — off, plainly.** This is a deliberate refusal, not an
oversight:

- The browser preload list is keyed on **registrable domains**. `vercel.app` is a public
  suffix owned by Vercel; this project controls only a subdomain of it and can never
  submit it to hstspreload.org. The `preload` directive on this host would therefore be a
  token no browser acts on.
- Setting it `True` would change nothing observable and would exist solely to silence
  Django's `security.W021`. Turning on a security flag in order to quiet a check, on a
  domain where the flag cannot function, is exactly the habit this design should not
  establish.
- Preload is also the genuinely irreversible part of HSTS — removal takes months and ships
  with browser releases.

**`SILENCED_SYSTEM_CHECKS = ["security.W021"]`** records that refusal in a form Django
understands, so the warning is *answered* rather than tolerated. It is unconditional and
inert locally, because W021 only fires when `SECURE_HSTS_SECONDS` is truthy, which it is
not when `HTTPS_ONLY` is `False`. Test A14 pins both halves so a future contributor cannot
"fix" the warning by flipping preload on.

#### 11.4 `SECURE_SSL_REDIRECT` and the redirect loop — why it is safe here

The classic failure is worth spelling out because it is catastrophic and easy to reach:
with `SECURE_SSL_REDIRECT = True` behind a TLS-terminating proxy and **no**
`SECURE_PROXY_SSL_HEADER`, `SecurityMiddleware` asks `request.is_secure()`, gets `False`
because the proxy-to-function hop is plain HTTP, and issues a 301 to `https://…`. The
browser follows it, the edge terminates TLS and forwards plain HTTP again, `is_secure()`
is `False` again, and the site is an infinite loop — `ERR_TOO_MANY_REDIRECTS` on every URL.

**What makes it safe here** is Decision 4, and only Decision 4:
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` makes `is_secure()` return
`True` for any request Vercel's edge received over TLS, so `SecurityMiddleware`
short-circuits and never redirects. `SecurityMiddleware` is already first in `MIDDLEWARE`,
and `is_secure()` consults `SECURE_PROXY_SSL_HEADER` directly on the request object, so
there is no middleware-ordering dependency to get wrong.

Two consequences recorded rather than glossed:

- **Decision 4's failure mode escalates from "login 403s" to "total outage."** That is the
  real price of accepting `SECURE_SSL_REDIRECT`, and it is why ML-1 and ML-6 both carry an
  explicit no-redirect-loop observable.
- **Its practical benefit on Vercel is close to nil**, because the edge already redirects
  HTTP to HTTPS before a request ever reaches the function; this setting should never
  actually fire in production. It is defence in depth and it closes `security.W008`. That
  is an honest accounting of a setting whose downside risk exceeds its expected effect on
  this specific platform — accepted because the user settled it, and made safe by the
  gate and by two live checks.

No `SECURE_REDIRECT_EXEMPT` is needed: the project has no health-check or ACME path that
must stay reachable over plain HTTP.

#### 11.5 Effect on item #1's existing test suite

`DJANGO_HTTPS_ONLY` is the one variable in this change that can break the **existing**
suite from `.env` alone. If it were set to `True` locally, `SECURE_SSL_REDIRECT` would
turn every request in `usuarios/tests/test_login.py` into a 301, and all seven auth tests
would fail with no obvious connection to the change. This is why `.env.example` ships
`False`, why the Development environment is `False`, and why test A11 exists — A11 is the
guard for local development, and is behaviourally the most valuable of the new pair even
though its RED phase is weak.

## Data Flow

Production request path, with the settings that make or break it marked:

```
Browser                Vercel edge                  Vercel Function        Neon
  │ GET https://<proj>.vercel.app/login
  │ ──── TLS ────────▶ terminates TLS
  │                    sets X-Forwarded-Proto: https
  │                    ──── plain HTTP ──────────▶ config.wsgi
  │                                                 │  SECURE_PROXY_SSL_HEADER
  │                                                 │  ⇒ is_secure() == True   ◀── D4
  │                                                 │  SecurityMiddleware:
  │                                                 │    already secure ⇒ NO redirect ◀── D11
  │                                                 │    adds Strict-Transport-Security
  │                                                 │  Host checked vs
  │                                                 │  ALLOWED_HOSTS           ◀── D2
  │                                                 │  LoginView
  │                                                 │  connect ──────────────▶ -pooler endpoint
  │                                                 │  disconnect (CONN_MAX_AGE=0)
  │ ◀───────────────── 200 + login form ────────────┘
  │ POST /login  Origin: https://<proj>.vercel.app
  │                    ──────────────────────────▶  CSRF: expected origin is built
  │                                                 from request.scheme (https,
  │                                                 thanks to D4) and matched
  │                                                 against CSRF_TRUSTED_ORIGINS ◀── D3
  │ ◀── 302 /  ·  Set-Cookie sessionid; Secure; HttpOnly          ◀── D11

  GET /static/admin/css/base.css
  │ ──────────────▶ served by the CDN from the build's collectstatic output
                    (STATIC_ROOT) — never reaches the function.   ◀── D5
```

The one line that turns this diagram into an outage:

```
SECURE_PROXY_SSL_HEADER wrong  ⇒  is_secure() False  ⇒  SECURE_SSL_REDIRECT fires
                               ⇒  301 to https  ⇒  edge forwards HTTP  ⇒  301 again  ⇒  ∞
```

Schema changes deliberately do **not** appear in the request diagram — that is the point
of Decision 7:

```
Developer's PowerShell ──$env:DATABASE_URL (direct)──▶ manage.py migrate ──▶ Neon prod branch
                                                                             ▲
   Vercel build ─── collectstatic only ─────────────────────────────────╳────┘
   Vercel Function ─── request handling only ───────────────────────────╳────┘
```

## File Changes

| File | Action | Description |
|---|---|---|
| `config/settings.py` | Modify | `require_bool_env()` helper; `ALLOWED_HOSTS` via `require_env()` + strip; add `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `HTTPS_ONLY` and its six derived transport settings, `SILENCED_SYSTEM_CHECKS`, `STATIC_ROOT`, `CONN_MAX_AGE = 0` |
| `.env.example` | Modify | Add `DJANGO_ALLOWED_HOSTS` and `DJANGO_HTTPS_ONLY` (both now required), `DJANGO_CSRF_TRUSTED_ORIGINS` (commented), `BLOB_READ_WRITE_TOKEN` (commented, unused) |
| `config/tests/__init__.py` | Create | Package marker |
| `config/tests/conftest.py` | Create | `_load_settings` probe + `PROD_ENV` fixture (Decision 1) |
| `config/tests/test_deployment_settings.py` | Create | Scenarios A1–A5, A8, A10–A14 |
| `config/tests/test_deployment_hygiene.py` | Create | Scenarios A6, A7, A9 |
| `.gitignore` | **No change** | `/staticfiles/` and `.env` already covered |
| `requirements.txt` / `requirements-dev.txt` | **No change** | No new dependency — no WhiteNoise, no storage backend, no Blob SDK |
| `vercel.json` | **Not created** | Decision 5. Its absence is *no longer asserted* — see the A6 narrowing |
| `pytest.ini` | **No change** | `config/tests/` is collected by the existing globs |

Local `.env` also needs `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1` **and**
`DJANGO_HTTPS_ONLY=False` — developer actions on a gitignored file, not repository
changes, but **blocking prerequisites** for the settings edit.

## Testing Strategy

### The automatable scenarios

Nine from spec #52 (A1–A9, two of them narrowed, one amended) plus five added by
Decision 11 (A10–A14).

| # | Scenario | Mechanism | Location |
|---|---|---|---|
| A1 | `STATIC_ROOT` non-null, no WhiteNoise | Probe; `STATIC_ROOT` ends with `staticfiles`; no `MIDDLEWARE` entry contains `whitenoise`; module defines no `STORAGES` | `test_deployment_settings.py` |
| A2 | `CONN_MAX_AGE == 0` | Probe with a `-pooler` `DATABASE_URL`; `DATABASES["default"]["CONN_MAX_AGE"] == 0` | `test_deployment_settings.py` |
| A3 | Unset `DJANGO_ALLOWED_HOSTS` ⇒ `ImproperlyConfigured` | `pytest.raises` around the probe with the key deleted and dotenv disabled | `test_deployment_settings.py` |
| A4 | `CSRF_TRUSTED_ORIGINS` contains the https origin | Probe with `DJANGO_CSRF_TRUSTED_ORIGINS=https://x.vercel.app`; assert membership; assert unset ⇒ `[]` | `test_deployment_settings.py` |
| A5 | `SECURE_PROXY_SSL_HEADER` exact tuple | Probe; `== ("HTTP_X_FORWARDED_PROTO", "https")` | `test_deployment_settings.py` |
| **A6** *(narrowed)* | No build step and no request handler runs migrations | For each of `vercel.json` and `pyproject.toml` **that exists**, assert the token `migrate` does not appear in its text; and assert no `.py` under `config/` or `usuarios/` (excluding `config/tests/`) references `call_command("migrate"` or `MigrationExecutor` | `test_deployment_hygiene.py` |
| **A7** *(narrowed)* | No code consumes the Blob token | `BLOB_READ_WRITE_TOKEN` appears in no `.py` file (excluding `.venv/` and this test); no `.py` references `vercel_blob` or `blob.vercel-storage.com`; the probed settings module overrides no `default` file-storage backend | `test_deployment_hygiene.py` |
| **A8** *(amended)* | `check --deploy` clean at WARNING; `DEBUG is False` | Probe under `PROD_ENV` asserts `DEBUG is False`; **plus** `subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"], env=…)` returncode `0`. A syntactically valid but unreachable `DATABASE_URL` is supplied — `check --deploy` performs no database checks unless `--database` is passed | `test_deployment_settings.py` |
| A9 | `.env` ignored, `.env.example` placeholder-only | `.gitignore` text contains `.env`; `.env.example` contains no `postgresql://user:pass@…` pattern and no `DJANGO_SECRET_KEY` value ≥ 40 characters | `test_deployment_hygiene.py` |
| **A10** *(new)* | `DJANGO_HTTPS_ONLY=True` ⇒ hardened | Probe; `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT` all `True`; `SECURE_HSTS_SECONDS == 3600`; `SECURE_HSTS_INCLUDE_SUBDOMAINS is True` | `test_deployment_settings.py` |
| **A11** *(new)* | `DJANGO_HTTPS_ONLY=False` ⇒ all off | Probe; the three flags all `False` and `SECURE_HSTS_SECONDS == 0`. **This is the guard for local development** — see 11.5 | `test_deployment_settings.py` |
| **A12** *(new)* | Unset `DJANGO_HTTPS_ONLY` ⇒ `ImproperlyConfigured` | `pytest.raises` around the probe with the key deleted | `test_deployment_settings.py` |
| **A13** *(new)* | Malformed `DJANGO_HTTPS_ONLY` ⇒ `ImproperlyConfigured` | Parametrised over `"true"`, `"1"`, `"yes"`, `""`; `pytest.raises(ImproperlyConfigured, match="DJANGO_HTTPS_ONLY")` | `test_deployment_settings.py` |
| **A14** *(new)* | Preload refusal is deliberate and pinned | Probe; `SECURE_HSTS_PRELOAD is False` **and** `"security.W021" in SILENCED_SYSTEM_CHECKS`. Prevents a future contributor from closing W021 by flipping preload on | `test_deployment_settings.py` |

### Why A6 and A7 were narrowed

Both previously asserted the **absence of a file** as a proxy for the property they
actually care about, which couples unrelated future decisions to an infrastructure test:

| Old assertion | What breaks it for no real reason | New assertion |
|---|---|---|
| `pyproject.toml` does not exist | The day a linter (ruff, black) is configured, an infrastructure test fails | If `pyproject.toml` exists, it declares no build step containing `migrate` |
| `vercel.json` does not exist | Decision 5's own `collectstatic` contingency would fail its own test | If `vercel.json` exists, its text contains no `migrate` |
| `requirements*.txt` mention no `django-storages`/`boto3`/`vercel` | A transitive or unrelated dependency trips it; and it only ever *proxied* for "no Blob code" | `BLOB_READ_WRITE_TOKEN` and the Blob SDK/endpoint appear in no `.py`; no `default` storage backend override |

The narrowed forms assert what the requirements mean — *no build step runs migrations*
and *no code consumes the Blob token* — and stay green through changes that have nothing
to do with either. The dependency-manifest assertion is dropped entirely rather than
narrowed, because the direct assertion supersedes it.

### Why A8 can now tighten to `--fail-level WARNING`

With Decision 11 in place, the four warnings that previously forced `ERROR` are closed:
`W004` (HSTS) and `W008` (`SECURE_SSL_REDIRECT`) by the HTTPS-only gate, `W012`
(`SESSION_COOKIE_SECURE`) and `W016` (`CSRF_COOKIE_SECURE`) likewise. `W005`
(`includeSubDomains`) is closed by 11.3, and `W021` (`preload`) is answered by
`SILENCED_SYSTEM_CHECKS` rather than left outstanding.

What remains under `PROD_ENV`, and why each is satisfied: `W018` (DEBUG) — variable
absent; `W020` (`ALLOWED_HOSTS`) — set; `W009` (weak `SECRET_KEY`) — the fixture key is 50
characters with high character variety, which is exactly why Decision 1 specifies it;
`W006` (`SECURE_CONTENT_TYPE_NOSNIFF`), `W019` (`X_FRAME_OPTIONS`), `W022`
(`SECURE_REFERRER_POLICY`) and `W023` (`SECURE_CROSS_ORIGIN_OPENER_POLICY`) — satisfied by
Django 5.2's own defaults, with nothing in this project overriding them.

**What the tightened A8 genuinely proves:** that under this exact environment Django's own
deployment checklist finds *no* issue at WARNING or above. That is materially stronger
than the `ERROR` version, which would have passed even if all four settings regressed. It
now fails if any of the six transport settings is removed or inverted, if `DEBUG` leaks
on, or if `ALLOWED_HOSTS` empties.

**What it still does not prove:** that the Vercel Production environment actually has
`DJANGO_HTTPS_ONLY=True`. `require_bool_env` proves the variable exists and parses; it
cannot prove which way it points in a dashboard this repository cannot see. Only MC-6 and
ML-6 prove that. It also does not prove a browser receives the cookies or the header —
that is ML-6.

**One deliberate brittleness, recorded so `sdd-verify` does not read it as a defect:** a
future Django minor release adding a new deployment warning will fail this test. That is
the intended signal, not a flaw; the response is to close the new warning or to silence it
with a written reason, never to widen `--fail-level` back.

> **[verify-at-apply] One cheap empirical check before pinning `WARNING`.** The
> enumeration above is reasoned from Django 5.2's documented deployment checks, not
> observed. `sdd-apply` must run `manage.py check --deploy` once under `PROD_ENV` and
> record the actual output **before** pinning `--fail-level WARNING`. If anything
> unexpected remains, either close it or add it to `SILENCED_SYSTEM_CHECKS` with a written
> reason in the same commit. Do not silently revert to `ERROR`.

### Strict TDD: which tests are written when, honestly

| Group | RED phase | Order |
|---|---|---|
| **A3, A12, A13** | **Genuine and behavioural.** A3: `ALLOWED_HOSTS` currently defaults, so the probe returns a value where the test demands an exception. A12: same shape for the new variable. **A13 is the strongest test in the change** — it asserts a *rejection* of `"true"`, which no amount of "the setting exists" can satisfy; it can only pass if `require_bool_env` really validates. | Write first, run, observe the failures, then edit `settings.py`. |
| **A8** *(reclassified)* | **Genuine and behavioural — upgraded by Decision 11.** In revision 1 this was a vacuously-green guard at `ERROR` level. At `WARNING` level it fails today, because `W004`/`W008`/`W012`/`W016` are all currently emitted under a production-like environment. It is now a real RED. | Write with the group above; it goes green with the same `settings.py` edit. |
| **A1, A2, A4, A5, A10, A11, A14** | **Genuine but weak.** They fail today because the name is absent (`AttributeError`/`KeyError`), not because a behaviour is wrong. A name-absence RED cannot distinguish "not written" from "written with the wrong value", so it proves less than a behavioural RED. A11 is the most *valuable* of these despite the weak RED, because it is the only guard on local development still working. | Write together with the group above; one `settings.py` edit turns them all green. |
| **A6, A7, A9** | **None — vacuously green from the first run.** No build config runs `migrate` today, no Blob code exists, `.env` is already gitignored. | Write **after** the settings edit and label them in-file as **regression guards**. Do **not** manufacture a RED by temporarily writing a `migrate` build command or a fake Blob import — that fakes the ceremony without adding information. |

**The blunt statement this change owes Strict TDD:** configuration has a weaker RED phase
than application logic, because many of these assertions restate a value rather than
exercise a behaviour. **Four of the fourteen (A3, A8, A12, A13) are genuine behavioural
REDs** — a real improvement over revision 1, where only A3 qualified, and the direct
result of `require_bool_env` and the tightened fail level. Seven are weak name-absence
REDs. Three (A6, A7, A9) are honestly regression guards with no RED at all. This is stated
here so `sdd-verify` records it as a known property of the change rather than discovering
it as a process defect — the same class of finding as WARNING 2 in item #1's archive
report (#47), pre-empted this time.

### The manual scenarios — acceptance checklist

These are **acceptance criteria, not tests**. Each has an exact location and an exact
observable.

**Manual (console) — 6**

| # | Steps | Expected observable |
|---|---|---|
| MC-1 | Vercel dashboard → the project → **Settings → Environment Variables** → find `DATABASE_URL` scoped to **Production** → click the eye icon to reveal | The hostname contains `-pooler.` and the branch is the **production** branch, not `dev` |
| MC-2 | In the same PowerShell session used for the migration, run `.venv\Scripts\python.exe manage.py showmigrations` | Every line shows `[X]`. **No `[ ]` anywhere.** |
| MC-3 | Vercel dashboard → **Storage** tab | A Blob store is listed and shows the project as **Connected**; **Settings → Environment Variables** now lists `BLOB_READ_WRITE_TOKEN` |
| MC-4 | `git switch -c prueba-preview`, make a trivial commit, push it → Vercel dashboard → **Deployments** | A **Preview** deployment appears and reaches status **Ready**; `DATABASE_URL` scoped to Preview resolves to the **dev** branch |
| MC-5 | Vercel dashboard → **Settings → Environment Variables**, filter to **Production**; then locally run `git grep -n "neon.tech"` | Production lists `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_HTTPS_ONLY`, `BLOB_READ_WRITE_TOKEN`; `git grep` returns **no matches** |
| **MC-6** *(new)* | **Settings → Environment Variables** → `DJANGO_HTTPS_ONLY` → **reveal the value** in each of Production, Preview and Development | Exactly `True` in Production and Preview; exactly `False` in Development. **Reveal it — do not assume.** This is the one variable whose *value* must be eyeballed: `require_bool_env` proves it parses, never which way it points |

**Manual (live) — 6**

| # | Steps | Expected observable |
|---|---|---|
| ML-1 | `curl.exe -I https://<vercel-project>.vercel.app/login` in PowerShell, then open the same URL in a browser | `HTTP/2 200`; the browser shows a padlock with no certificate warning and renders the login form. **Negative observable: a `301` whose `location` is the same https URL means a redirect loop — `SECURE_PROXY_SSL_HEADER` is wrong (Decision 11.4). The browser would show `ERR_TOO_MANY_REDIRECTS`** |
| ML-2 | `curl.exe -I https://<vercel-project>.vercel.app/static/admin/css/base.css` | `HTTP/2 200` and `content-type: text/css`. **A 404, or `content-type: text/html`, means `collectstatic` did not run** — apply the Decision 5 contingency |
| ML-3 | On the live `/login`, submit a valid administrador username and password | Redirect to `/`. **Not** a `403 Forbidden — CSRF verification failed` page. A 403 here means Decision 3 or 4 is misconfigured |
| ML-4 | After ML-3, browser DevTools → **Application → Cookies** → the `vercel.app` domain; then reload the page | `sessionid` and `csrftoken` cookies are present and the session survives the reload — i.e. no login loop and no 403 on any subsequent POST |
| ML-5 | Log in as `rol=administrador` → open `/admin/`; log out; log in as `rol=usuario` → open `/admin/`; log out; open `/` while logged out | administrador: `/admin/` renders **with CSS**; usuario: redirected or 403; logged out: redirected to `/login` |
| **ML-6** *(new)* | DevTools → **Network** → select the `/login` document request → **Response Headers**; then **Application → Cookies** → check the **Secure** column for `sessionid` and `csrftoken` | Header `strict-transport-security: max-age=3600; includeSubDomains`, **with no `preload` token**. Both cookies show **Secure ✓**. The Network panel shows a single `200`, not a chain of `301`s. Together with ML-4 this is the only evidence that `SECURE_PROXY_SSL_HEADER` is correct — A5 asserts the literal tuple and can prove nothing about behaviour. **If the observed `max-age` is not 3600, Vercel's edge is setting its own HSTS header and the app's value is advisory; record the observed value — this is not a failure** |

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | **N/A** — nothing in this change classifies files for execution. `requirements.txt` is installed by Vercel's builder and by the developer, unchanged by this item | — | — |
| Git repository selection | **N/A** — no git automation is designed. `git switch`/`git grep` appear only inside human checklist steps MC-4/MC-5 | — | — |
| Commit state | **N/A** — this change adds no secret-bearing file. `.env` was already gitignored and staged as such in item #1; `.env.example` carries placeholders, asserted by A9 (a value assertion, not a git-state one) | — | — |
| Push state | **N/A** — the repository has never been pushed and this design authorises no push. The `git push` in MC-4 is a human action the user performs when they choose to connect the repository to Vercel | — | — |
| PR commands | **N/A** — no PR automation | — | — |

**One boundary outside the standard five, recorded rather than ignored.** Test A8 spawns a
**subprocess** (`sys.executable manage.py check --deploy`). Its safety properties: the
argument vector is a fixed literal list with no shell interpolation and `shell=True` is
never used; `cwd` is the repository root derived from `__file__`, not from any input; the
environment is the explicit `PROD_ENV` dict built in the test, so the developer's real
`DATABASE_URL` and `DJANGO_SECRET_KEY` never reach the child; the fixture secret key is a
deliberately synthetic literal that is not and must never be a real key; and the child
performs no database connection, because `check --deploy` runs database checks only when
`--database` is passed. No RED test is created for the subprocess itself — it is test
infrastructure, not product behaviour, and manufacturing a test for it would be exactly
the invented work the threat-matrix reference warns against.

## Migration / Rollout

**No data migration.** The Neon production branch does not exist yet, so its first
`migrate` creates the schema from zero — there are no existing rows anywhere to transform.

**Rollout** is the first-deployment order in Decision 7: provision → set variables →
migrate → `createsuperuser` → deploy → manual checklist.

**Rollback.** Production data is disposable by decision 5 of #50, so rollback is
correspondingly blunt and cheap:

| Failure | Rollback |
|---|---|
| Bad settings value | Change it in the Vercel dashboard and redeploy — no code change |
| Bad migration | Reset the Neon production branch and re-run `migrate`. **Do not write a reverse migration** — there is no data worth preserving |
| **Redirect loop on first deploy** | Set `DJANGO_HTTPS_ONLY=False` in the Vercel dashboard and redeploy. That disables `SECURE_SSL_REDIRECT` and restores a reachable (unhardened) site in one dashboard edit, buying time to fix `SECURE_PROXY_SSL_HEADER`. **This is the reason the flag is a variable and not a constant** |
| **HSTS asserted in error** | Set `DJANGO_HTTPS_ONLY=False` and redeploy; browsers stop receiving the header, and every cached policy expires within **one hour** — the whole point of the short `max-age` in 11.3. This is the only rollback in this change that is not instantaneous |
| The whole deployment is wrong | Delete the Vercel project. The repository is unaffected; only `config/settings.py` and `.env.example` would need reverting |
| Local development broken by the fail-loud changes | Add `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1` and `DJANGO_HTTPS_ONLY=False` to `.env`. This is the only way this change can break a developer's machine, and it is two lines |

**Time-bound assumption, restated so it is not lost.** All of the above depends on
production being a demo with disposable data and no real field users. When that stops
being true, manual migrations and "reset the branch" rollback become a genuine gap
requiring its own backlog item — and `SECURE_HSTS_SECONDS` should be raised to a
conventional production value at the same time. Decision 8 of #50 records that no date or
milestone is known for this.

## Size Estimate

| Area | Authored lines | Δ vs revision 1 |
|---|---|---|
| `config/settings.py` | ~40 added, 1 modified | +22 |
| `.env.example` | ~10 | +2 |
| `config/tests/__init__.py` | 1 | — |
| `config/tests/conftest.py` | ~40 | +5 |
| `config/tests/test_deployment_settings.py` | ~125 | +55 |
| `config/tests/test_deployment_hygiene.py` | ~60 | +5 |
| **Authored total** | **~276** | **+86** |

**~276 lines against the 400-line review budget — still under, no split required, but the
risk rating rises from Low to Medium.** The change now consumes roughly 69% of the budget
and its estimate has grown twice (proposal ~80–120 → revision 1 ~190 → revision 2 ~276). A
third growth of similar size would cross. `sdd-tasks` should re-forecast rather than
inherit this number.

Guard lines, per the review workload contract:

```
Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Medium
```

**If a split becomes necessary**, the clean seam is *below* the hygiene guards, not through
the settings:

| Slice | Contents | Lines |
|---|---|---|
| A — settings + transport hardening | `config/settings.py`, `.env.example`, `conftest.py`, `test_deployment_settings.py` (A1–A5, A8, A10–A14) | ~216 |
| B — hygiene regression guards | `test_deployment_hygiene.py` (A6, A7, A9) | ~60 |

Slice A must not be subdivided: every setting it adds is exercised by the same probe
fixture and by the same `check --deploy` run, so splitting it would leave a slice whose
A8 cannot pass.

## Non-Goals (explicit)

- **A settings split** — Decision 1.
- **`vercel.json`** — Decision 5 (its *absence* is no longer test-enforced, only its
  not-running-migrations property is).
- **HSTS preload submission** — Decision 11.3. Refused deliberately and pinned by A14.
- **A one-year `SECURE_HSTS_SECONDS`** — Decision 11.3. Deferred to whenever a real domain
  and real users exist.
- **Retrofitting `require_bool_env` onto `DJANGO_DEBUG`** — Decision 11.2. Out of scope and
  would break existing `.env` files.
- **Any Blob consumption code** — Decision 8; items #11/#13.
- **Neon per-preview branch integration** — decision 4 of #50.
- **Staging environment, custom domain, backup/restore tooling** — decisions 5 and 6 of #50.
- **Sentry / observability** — item #14.
- **A scripted smoke test against the live URL** — it would be a network-dependent
  integration test in a suite that is otherwise hermetic. ML-1…ML-6 cover it as human
  checks instead.

## Required Spec Amendment

Decision 11 adds behaviour that spec #52 does not describe. The spec must gain one
requirement and seven scenarios before `sdd-tasks` runs, or the two artifacts disagree on
what this change does. Proposed wording, to be applied verbatim to
`sdd/despliegue-e-infraestructura/spec`:

> ### Requirement: HTTPS-only transport hardening
> Transport-security settings MUST derive from an explicit, fail-loud, strictly-parsed
> `DJANGO_HTTPS_ONLY` flag, so the application never infers its environment.
> - Scenario (Automatable): `DJANGO_HTTPS_ONLY` unset; loading settings raises
>   `ImproperlyConfigured`.
> - Scenario (Automatable): `DJANGO_HTTPS_ONLY` set to anything other than exactly `True`
>   or `False`; loading settings raises `ImproperlyConfigured` naming the variable.
> - Scenario (Automatable): `DJANGO_HTTPS_ONLY="True"`; `SESSION_COOKIE_SECURE`,
>   `CSRF_COOKIE_SECURE` and `SECURE_SSL_REDIRECT` are True, `SECURE_HSTS_SECONDS` is 3600
>   and `SECURE_HSTS_INCLUDE_SUBDOMAINS` is True.
> - Scenario (Automatable): `DJANGO_HTTPS_ONLY="False"`; all three flags are False and
>   `SECURE_HSTS_SECONDS` is 0, so plain-HTTP local development is unaffected.
> - Scenario (Automatable): `SECURE_HSTS_PRELOAD` is False and `security.W021` is silenced
>   deliberately, because `vercel.app` is a public suffix this project cannot submit to the
>   preload list.
> - Scenario (Manual, live): deployed app; the response carries
>   `Strict-Transport-Security` with `includeSubDomains` and no `preload`, session and CSRF
>   cookies carry `Secure`, and the page loads without a redirect loop.
> - Scenario (Manual, console): Vercel Production and Preview show `DJANGO_HTTPS_ONLY` with
>   the revealed value `True`; Development shows `False`.

The existing "Secrets handling" requirement's `check --deploy` scenario should also be
amended from *"no issues at targeted security severity levels"* to *"no issues at WARNING
or above"*, matching the tightened A8.

**Amended totals: 12 requirements, 26 scenarios — Automatable 14, Manual (live) 6, Manual
(console) 6.**

## Open Questions

- [ ] **[verify-at-apply] — the sharpest risk in this change.** Are Vercel environment
  variables exposed to the **build** step as well as the runtime? Decisions 2 and 11 make
  `DJANGO_ALLOWED_HOSTS` and `DJANGO_HTTPS_ONLY` required at import, joining
  `DJANGO_SECRET_KEY` and `DATABASE_URL` — **four** variables the build now needs. If the
  build cannot see them, `collectstatic` raises and the **entire deployment fails**, not
  just a request. *Symptom:* the build log shows `ImproperlyConfigured: Missing required
  environment variable: …`. *First fix:* confirm each variable is scoped to the
  environment being built and is not marked in a way that withholds it from the build.
  *Fallback if the platform genuinely cannot expose them at build time:* add a `vercel.json`
  whose build command supplies obviously-synthetic values inline for the build process
  only — e.g. `DJANGO_SECRET_KEY=build-only-not-a-real-key-<padding to 50 chars>
  DJANGO_ALLOWED_HOSTS=build DJANGO_HTTPS_ONLY=False DATABASE_URL=postgresql://u:p@h/db
  python manage.py collectstatic --noinput`. This is safe because build and runtime are
  separate processes, and `collectstatic` touches neither the database nor cookies. These
  values must stay inside the build command and must never be entered as dashboard
  variables. Note that A6's narrowed form survives this fallback unchanged — the build
  command contains `collectstatic`, not `migrate`.
- [ ] **[verify-at-apply]** Before pinning A8 at `--fail-level WARNING`, run
  `manage.py check --deploy` once under `PROD_ENV` and record what actually remains. See
  *Why A8 can now tighten*.
- [ ] **[verify-at-apply]** `migrate` is routed through Neon's **direct** endpoint as a
  belt-and-braces choice; the pooled endpoint very likely also works for this project's
  simple DDL. Decision 6.
- [ ] **`.env.example` remains unread.** Two attempts in this phase were refused by a
  sandbox permission rule on dotfiles, so Decision 9's matrix is inferred from
  `config/settings.py` and item #1's design, not observed. **`sdd-apply` must read it
  before editing and reconcile exactly three things:** (1) which of `DJANGO_SECRET_KEY`,
  `DATABASE_URL`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `TEST_DB_NAME` are already
  present and in what order, so the two new entries are appended in the file's existing
  style rather than a new one; (2) whether existing values are placeholders or real, since
  A9 will start asserting that they are placeholders; (3) whether `DJANGO_ALLOWED_HOSTS`
  is already documented as optional, in which case its comment must change to reflect that
  it is now required.
- [ ] The exact Vercel project name — and therefore the exact `<vercel-project>.vercel.app`
  hostname used in `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` — is fixed
  during the manual provisioning step and is not knowable now.

*Two open questions from revision 1 — Vercel's automatic `collectstatic` and its entrypoint
auto-detection — were resolved against exploration #49's official-documentation findings
and are now recorded as cited findings in Decision 5. The revision-1 question about whether
to close the four `check --deploy` warnings was answered by the user and is resolved in
Decision 11.*

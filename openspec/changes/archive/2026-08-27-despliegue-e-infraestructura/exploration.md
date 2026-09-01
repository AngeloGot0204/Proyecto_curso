# Exploration: Deployment and Production Infrastructure (backlog #2)

> Engram: `sdd/despliegue-e-infraestructura/explore` (observation 49)

## Current State

The repo (from archived backlog #1) has a working Django 5.2.17 project with:

- `config/settings.py`: environment-driven via `python-dotenv` + `dj-database-url`, `require_env()` fail-loud helper for `DJANGO_SECRET_KEY` and `DATABASE_URL`. `DEBUG` defaults to `False` unless `DJANGO_DEBUG=True`. `ALLOWED_HOSTS` reads from `DJANGO_ALLOWED_HOSTS`, default `localhost,127.0.0.1`.
- `WSGI_APPLICATION = 'config.wsgi.application'` already set (standard `django-admin startproject` wsgi.py); no `ASGI_APPLICATION` set.
- `STATIC_URL = 'static/'` set, but **no `STATIC_ROOT`**, no WhiteNoise, no static storage backend configured.
- `SecurityMiddleware` present in `MIDDLEWARE`, but no `SECURE_*` hardening flags (`SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`) and **no `CSRF_TRUSTED_ORIGINS`**.
- `DATABASES["default"] = dj_database_url.parse(require_env("DATABASE_URL"))` — no `CONN_MAX_AGE`, no `conn_health_checks`, no pooling config.
- Neon **dev branch** already used for local dev and tests (`--reuse-db`). No production branch exists yet.
- `.env` gitignored, never committed; `.env.example` holds placeholders (file was not directly readable due to sandbox permission, but referenced by settings and `.gitignore`).
- No `vercel.json`, no Vercel project, no Vercel Blob store, no Sentry, no WhiteNoise/`django-storages` dependency.
- Requirements: `Django>=5.2.8,<6.0`, `psycopg[binary]>=3.1.12,<4`, `python-dotenv`, `dj-database-url`. No `gunicorn`/`uvicorn` (irrelevant for Vercel's own runtime, which wraps WSGI itself).

**Definitely missing for deployment**: `STATIC_ROOT` (or WhiteNoise config), `CSRF_TRUSTED_ORIGINS` for the Vercel domain(s), `SECURE_PROXY_SSL_HEADER` (Vercel terminates TLS and proxies via `X-Forwarded-Proto`, so Django must be told to trust it — otherwise `request.is_secure()` is wrong, which breaks CSRF-cookie-secure and any HTTPS-only logic), a Neon **production** branch (only a dev branch exists), `SECRET_KEY`/`DATABASE_URL` provisioning as real Vercel env vars (currently only `.env`-driven locally), and a `vercel.json` (only needed for non-default config, see below).

## Affected Areas

- `config/settings.py` — add `STATIC_ROOT`, static storage backend choice, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `CONN_MAX_AGE`/pooled-endpoint guidance, and possibly a settings split (single file today, per backlog #1's noted open tradeoff).
- `requirements.txt` — no changes required for the "no build step" baseline (Vercel's own collectstatic handling covers static without WhiteNoise); would gain `sentry-sdk` only under #14, `django-storages`/Blob SDK only if attachments code (#11) is built now (recommended not to, see Q4).
- New: `vercel.json` — only needed to raise `maxDuration` past the default, or to `excludeFiles` (tests/fixtures) from the function bundle. Not strictly required for a minimal deploy.
- New: Vercel project + Neon **production** branch + Vercel Blob store, and their env-var wiring — infrastructure, not code.
- `usuarios/tests/` — deployment checks (`manage.py check --deploy`) can be added as a test, see Q6.

---

## Q1 — Serverless reality check (core finding)

Vercel's Django support (per current docs, updated 2026-07-24) is **more turnkey than the "serverless Django is painful" reputation suggests** for this project's shape (single monolith, server-rendered, no Celery/background workers):

- **Entrypoint**: Vercel auto-detects `manage.py`, reads `DJANGO_SETTINGS_MODULE`, and resolves `WSGI_APPLICATION` (already set to `config.wsgi.application` in this repo) into a single Vercel Function. No manual `vercel.json` build config is required for the entrypoint — it already works as-is. If `ASGI_APPLICATION` were also set, Vercel would prefer ASGI; this project has no ASGI need (no websockets/Channels in scope), so WSGI stays correct.
- **Cold starts / duration**: Vercel uses **Fluid compute by default**, meaning function instances can be reused across requests (mitigating pure cold-start-per-request), and Hobby plan gives **300s max duration by default** (not a tight budget for a Django wizard/report app — this is generous, not a constraint here).
- **Bundle size**: Python functions get a 500 MB uncompressed limit (vs. 250 MB for Node) — comfortable for Django + psycopg + a handful of deps; openpyxl (item #4) will not be a problem either.
- **No persistent filesystem**: confirmed constraint — any file write at request time (uploaded logo, generated `.xlsx`, session-scoped temp files) must NOT rely on local disk; ADR-0009 already anticipated this by routing all files to Vercel Blob.

### Database connections (the real risk area)

- Neon offers two endpoint types: a **pooled** endpoint (hostname suffixed `-pooler`, routes through Neon's managed PgBouncer, handles up to ~10,000 concurrent client connections) and a **direct** endpoint (needed for `CREATE INDEX CONCURRENTLY`, `LISTEN/NOTIFY`, session-level features, and is the one migrations conventionally use, though migrations also work over the pooled endpoint in transaction mode for simple DDL).
- **Recommendation: use the pooled (`-pooler`) `DATABASE_URL` for the deployed app's runtime traffic.** Serverless functions open a fresh DB connection per cold instance and Neon's own guidance is explicit: if using a pooled connection, avoid stacking Django's own connection pooling on top (i.e. do not set `CONN_MAX_AGE` to a large persistent value expecting Django-level reuse — with ephemeral/scaling function instances, a long `CONN_MAX_AGE` mostly just risks stale/leaked connections rather than actually reusing them across genuinely separate instances). **Set `CONN_MAX_AGE = 0`** (the safe, connection-per-request default) and let Neon's pooler absorb the connection churn. Django 5.1+ has native connection pooling (`django.db.backends.postgresql` `pool` option via psycopg3's `ConnectionPool`) as a documented alternative to `CONN_MAX_AGE`, but adding an in-process pool on a platform that itself recycles instances non-deterministically adds complexity without a clear win here — not recommended for this project's scale.
- Local dev keeps using the existing Neon **dev branch** (already working, no change).

### Static files

Three real options exist:

1. **Vercel's native static handling (recommended)**: if `STATIC_ROOT` is set with a supported storage backend (`StaticFilesStorage`, `ManifestStaticFilesStorage`, or WhiteNoise's `CompressedManifestStaticFilesStorage`), **Vercel runs `collectstatic` automatically during its own build step** and serves the result from its CDN at `STATIC_URL`. No manual build script, no WhiteNoise dependency required. This is the lowest-effort, currently-documented path and matches "no build pipeline" bias already established in ADR-0001/backlog #1.
2. **WhiteNoise middleware**: compatible, but per Vercel's own docs it is "only active when running locally with `vercel dev`" — in production Vercel's CDN serves the files regardless, so adding WhiteNoise buys nothing extra in production and is redundant complexity unless local `vercel dev` static serving parity is valued.
3. **`django-storages` to an external object store (e.g. routing static assets to Vercel Blob or S3-compatible storage)**: Vercel detects `django-storages` and runs `collectstatic` against it during build, uploading directly to the configured storage provider. Unnecessary for this project — this app has almost no custom static assets (server-rendered Django templates, minimal CSS/JS per ADR-0001's "no frontend framework" constraint), so CDN-served local static output is sufficient; object storage for static assets is over-engineering here.

**Recommendation: Option 1** — set `STATIC_ROOT`, no WhiteNoise, no static storage backend beyond Django's default. Simple, zero extra dependency, matches project's minimal-JS profile.

### Migrations

Confirmed hard rule: **migrations must never run inside a request handler** (no `django.db.migrations` call from a view, no "migrate on first request" trick) — a serverless function has no business running schema DDL on a cold start race, and concurrent invocations during a deploy would race.

The two realistic patterns, given a solo developer and Vercel's current lack of a first-class "post-deploy migrate step" for Django:

- **A. Manual, developer-triggered migration** — after `vercel pull` (which fetches the current env vars including `DATABASE_URL` into `.env.local`), the developer runs `python manage.py migrate` locally against the target Neon branch (dev or prod) before/after promoting a deployment. Simple, explicit, fits solo-dev scale, and reuses the exact same "manual step" pattern backlog #1 already exercises for local dev.
- **B. A build-step migration script** (`pyproject.toml` `[tool.vercel.scripts] build = "..."` or a custom `build.py`/shell script invoking `manage.py migrate`) — runs automatically on every deploy. **Not recommended as the default here**: build-time execution happens for *every* deployment including preview deployments if a Neon-per-preview branch isn't carefully scoped, it has no safeguard against two concurrent deploys racing DDL, and it silently couples "ship code" with "mutate schema" — a riskier default for a single developer who is not yet comfortable debugging serverless build environments (echoes the same caution the backlog's own sequencing note gives about offline/IndexedDB being deferred due to solo-dev inexperience).
- **Recommendation: Pattern A (manual)** for this item, revisited later only if release cadence grows enough to justify automation risk.

---

## Q2 — Environments (Vercel × Neon mapping)

- **Vercel production deployment** (the `main` branch push) should point at a **Neon production branch** — this branch does not exist yet and must be created as part of this item's provisioning work.
- **Vercel preview deployments** (any other branch/PR) can point at the **existing Neon dev branch**, or — better — use **Neon's native Vercel integration**, which auto-creates a **copy-on-write Neon branch per preview deployment** (schema+data snapshot of its parent, isolated per PR) and injects `DATABASE_URL` automatically into that preview's environment. This is a documented, actively maintained integration (Vercel Marketplace) and removes the risk of preview deployments corrupting the shared dev branch's data.
- **Minimum viable setup for a solo developer**: two Neon branches are enough — `production` (mapped to Vercel Production) and the existing `dev`/default branch reused for local dev and, if the native integration isn't adopted, also for previews. A dedicated third "staging" environment is **not** worth the added complexity for a single-developer academic project: Vercel's preview-deployment-per-PR already gives an inspectable, shareable pre-production URL, which covers what a staging environment would otherwise provide.

---

## Q3 — Vercel Blob: provision now or defer?

ADR-0009 names Vercel Blob as part of item #2's stated scope in `BACKLOG.md` ("Vercel + Neon (Postgres) + Vercel Blob, HTTPS automático"), but the only concrete Blob *consumers* are later items: #11 (attachments), #13 (logo/template upload), and #4/#7 (generated `.xlsx` persistence, implied by ADR-0009's file list).

**Recommendation: provision the Blob store now, do not write any upload/download code now.**

- "Provision" = create the Vercel Blob store for the project and confirm its access token reaches the app as an env var (`BLOB_READ_WRITE_TOKEN`), the same way `DATABASE_URL`/`DJANGO_SECRET_KEY` are wired. This is infrastructure setup, consistent with item #2's actual charter ("deployment and infrastructure"), costs nothing extra, and removes a later blocker so item #11/#13 can start immediately on the *feature* work instead of first discovering "there's no Blob store yet."
- "Do not build usage code" — no `django-storages` Blob backend, no attachment model, no upload view. That is explicitly item #11/#13's scope; building it now would be scope creep the same way backlog #1's exploration flagged for offline-session logic. There is also a genuine open technical question (see Risks) about whether Blob access from Django will go through the REST API directly or the beta Python SDK — that decision belongs to #11's own exploration, not this one.

---

## Q4 — Secrets and `require_env()` interaction

- Vercel's env var model: variables set in the Vercel dashboard (or via `vercel env add`) are injected into the function's runtime environment per-environment (Production / Preview / Development), the same shape `os.environ` already expects. `require_env()` (fail loudly if a var is missing) **works unmodified** on Vercel — no code change needed, only making sure every required var (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG` if used) is actually set per-environment in the Vercel dashboard before the first deploy of that environment.
- `load_dotenv(BASE_DIR / ".env")` is a documented no-op when `.env` is absent and never overrides already-set env vars — safe to leave as-is; Vercel's runtime will not have a `.env` file, so it simply falls through to `os.environ` set by the platform.
- **Flag**: nothing in the current settings defaults to an insecure value if env vars are missing — `require_env()` raises `ImproperlyConfigured` for `SECRET_KEY`/`DATABASE_URL`, and `DEBUG` defaults to `False` (safe direction) if `DJANGO_DEBUG` is unset. The one gap: `ALLOWED_HOSTS` defaults to `"localhost,127.0.0.1"` if `DJANGO_ALLOWED_HOSTS` is unset — on Vercel this is a **fail-closed-in-practice** default (Django will reject requests with a 400 rather than silently accepting an unexpected host), which is the safe failure mode, but it means a forgotten env var manifests as "site returns 400" rather than a fail-loud startup error like the other two. Worth deciding explicitly during design whether `ALLOWED_HOSTS` should also go through `require_env()` for consistency, or stay defaulted (tradeoff: convenience for local dev vs. uniform fail-loud behavior).
- `CSRF_TRUSTED_ORIGINS` has no current handling at all and must be added — Django will otherwise reject POST logins/forms served over the Vercel domain due to CSRF's Origin check. `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` should also be set for HTTPS detection behind Vercel's proxy — without it, `request.is_secure()` is wrong and any `SESSION_COOKIE_SECURE`/CSRF-cookie-secure setting the design later adds would misbehave.

---

## Q5 — Verifiability under Strict TDD

Honest split between what's testable and what's inherently manual:

**Can be tested automatically:**

- `python manage.py check --deploy` — Django's own deployment checklist (flags missing `SECURE_*` settings, `DEBUG=True` in what looks like production, missing `ALLOWED_HOSTS`, etc.). Can be wired as a management-command invocation in CI/a test, asserting exit code 0 against a production-like settings snapshot (env vars set to simulate prod: `DJANGO_DEBUG=False`, a real-looking `ALLOWED_HOSTS`, HTTPS-related flags present).
- **Settings assertions**: a pytest test that imports `django.conf.settings` (or spawns a subprocess with prod-like env vars) and asserts concrete values — e.g. `STATIC_ROOT is not None`, `CSRF_TRUSTED_ORIGINS` contains the expected Vercel domain, `SECURE_PROXY_SSL_HEADER` is set. This is the same pattern backlog #1 already used to test `SESSION_COOKIE_AGE` as a settings assertion (see WARNING 1 in its archive report) — legitimate, low-value-but-real coverage: it proves the setting exists with the right value, not that the platform behaves correctly given it.
- A **CONN_MAX_AGE / DATABASE_URL parsing test** — assert `dj_database_url.parse(...)` produces the pooled-endpoint host when given a `-pooler` URL, and that `CONN_MAX_AGE == 0` is set in `DATABASES["default"]`. Real but narrow: it tests the settings module, not Neon's actual pooling behavior.

**Inherently manual (say so plainly, do not fake a test for these):**

- Whether the actual deployed app responds correctly over HTTPS with a valid certificate — this is Vercel's own guarantee (ADR-0009's premise), not something this project's test suite can or should assert; a one-time manual check (`curl -I https://<deployment-url>`) after first deploy is the honest verification.
- Whether static files actually resolve from the CDN in production, whether login/logout work end-to-end against the deployed Neon production branch, and whether the Blob store is reachable — these need a **manual smoke test** after each deploy (visit `/login`, log in, confirm `/admin` loads with static CSS, confirm no 500 on a simple authenticated page). A scripted smoke test against a live deployed URL is possible (`requests.get(deployed_url + "/login")` asserting 200) but is genuinely an *integration* test against live infrastructure, not a unit test — worth proposing as an optional, clearly-labeled manual-trigger script rather than part of the default `pytest` suite (it would be flaky/slow/network-dependent inside CI).
- Whether migrations were actually applied to the Neon production branch before the deploy that needs them went live — this is an ordering/process concern (see Q1 Migrations), not something a test can catch after the fact.

---

## Q6 — Alternatives to Vercel (informing, not overturning, ADR-0009)

ADR-0009 already compared Vercel/Neon against a self-managed VPS, Heroku, and Firebase/Supabase, and settled on Vercel for good reasons (zero ops for a solo academic-project developer, free Hobby tier, HTTPS automation for the service worker). This exploration does not revisit that decision, but the **friction cost specific to Django-on-serverless** is worth stating plainly so it's an informed tradeoff rather than an inherited one:

| | Vercel (chosen) | Container/VM PaaS (Railway, Fly.io, Render) |
|---|---|---|
| Deploy model | Function-per-request, no persistent process, no local disk | Long-running process, persistent local disk (ephemeral or volume-backed depending on plan) |
| Migrations | Manual/out-of-band step (no first-class "run once after deploy" hook for Django specifically) | Trivial — a release/start command (`release: python manage.py migrate`) runs once per deploy, a first-class primitive on most of these platforms |
| Long-running/background work (future Celery-style needs) | Not a natural fit — would need Vercel Queues/Workflows, a different mental model | Natural fit — a worker process is just another process type |
| Static files | Automatic via platform + CDN, no config | Needs its own static-serving story (WhiteNoise or a CDN) |
| Cost at this project's scale | Free (Hobby) | Free tiers exist but are typically more limited (compute-hours, sleep-after-inactivity) |
| Operational familiarity for a Django developer | Less — Django docs/tutorials mostly assume a long-running WSGI server | More — matches the "traditional" Django deployment mental model most tutorials teach |

**Net**: Vercel's main cost versus a container host is the missing first-class migration hook and the conceptual shift away from "one long-running Django process" — both manageable at this project's solo/academic scale, but real, and this is the honest tradeoff the ADR's "Costo real" bullets already gesture at without naming migrations specifically.

---

## Approaches

### 1. Minimal Vercel-native deploy (recommended)

Use Vercel's automatic Django detection (existing `WSGI_APPLICATION`, no custom `vercel.json` needed for the entrypoint), `STATIC_ROOT` + Vercel's built-in `collectstatic`, Neon pooled endpoint with `CONN_MAX_AGE=0`, manual migration step, Blob store provisioned but unused.

- **Pros:** smallest possible surface, matches "no build pipeline" bias already set in ADR-0001/backlog #1, nothing to maintain beyond settings changes and env var provisioning.
- **Cons:** manual migration step requires developer discipline (no CI/CD guardrail against "deployed code expects a migration that wasn't run yet").
- **Effort:** Low.

### 2. Vercel-native deploy + build-step migration automation

Same as #1, but add a `pyproject.toml` build script that runs `manage.py migrate` on every deploy.

- **Pros:** removes the "forgot to migrate" human error class.
- **Cons:** couples every deploy (including previews, unless carefully scoped to production-only branches) to a schema mutation; no protection against concurrent deploy races; higher blast radius for a solo developer still building comfort with the platform.
- **Effort:** Low-Medium.

### 3. WhiteNoise + explicit `django-storages` for static, instead of Vercel-native `collectstatic`

- **Pros:** closer to "classic" Django deployment patterns documented broadly across the ecosystem, arguably more portable if a future migration off Vercel happens.
- **Cons:** strictly more configuration than option 1 for **no functional gain in production** on Vercel today (per Vercel's own docs, WhiteNoise only matters for `vercel dev` parity) — added complexity without benefit for this project's scope.
- **Effort:** Low, but not justified.

## Recommendation

**Approach 1.** Configure `config/settings.py` for `STATIC_ROOT` (no WhiteNoise), `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, and `CONN_MAX_AGE=0` against Neon's pooled endpoint; provision (but do not integrate/consume) Vercel Blob; create a Neon production branch; wire all required env vars into Vercel's dashboard per environment; keep migrations as an explicit, manually-triggered step. Defer Sentry (item #14) and attachments/Blob consumption code (item #11) entirely. This keeps item #2 scoped exactly to "deployment and infrastructure" per its backlog description, and gives items #3-14 a real, reachable HTTPS deployment to build against.

## Risks

**Needs a user decision before proposal:**

- Does the user already have (or is willing to create) Vercel, Neon, and a payment-free Vercel Blob store accounts/projects? This item cannot proceed without those three accounts existing.
- Should `ALLOWED_HOSTS` be promoted to `require_env()` (fail-loud, more setup friction) or stay defaulted (convenience, silent-ish 400 failure mode if forgotten)? — flagged in Q4, a real design fork.
- Confirm the "provision Blob now, consume later" scope boundary (Q3) — if the user actually wants attachment/logo upload code built as part of #2, that changes this item's size substantially and should be an explicit scope decision, not an assumption carried into `sdd-propose`.
- Confirm whether the native Neon-Vercel integration (auto per-preview branches) is adopted now or deferred — affects whether preview deployments share the dev branch or get isolated copies; either is workable, but it's a environment-topology decision, not purely technical.

**Technical risk to manage during implementation:**

- `SECURE_PROXY_SSL_HEADER` misconfiguration is a common, easy-to-miss Vercel/Django gotcha (breaks CSRF cookie detection silently) — must be verified with a real HTTPS request against the deployed URL, not just a settings-value assertion.
- Neon connection-pooling behavior under Vercel's Fluid compute is stated based on both providers' current documentation but has **not been empirically load-tested** for this project — flag as an open question to revisit if login/report-generation requests start seeing connection errors under real field usage.
- Vercel's Python Blob SDK is in **beta** (as of this research) — item #11's eventual implementation may need to fall back to Vercel Blob's REST API directly rather than a first-class Python SDK; this is an open question for #11's own exploration, not a blocker for #2.
- The manually-triggered migration step (chosen over build-step automation) depends entirely on developer discipline; if this project's cadence grows, revisit Approach 2.
- Everything cited from Vercel/Neon docs was fetched during this exploration (dated 2026-07-24 / 2026-07-22 on Vercel's pages) — both platforms' serverless/Python support has changed meaningfully in the recent past (e.g., collectstatic automation, Fluid compute defaults) and should be re-verified against current docs at `sdd-design`/`sdd-apply` time rather than assumed stable.

## Ready for Proposal

Yes, once the "needs a user decision" items above are answered — particularly account/service availability and the `ALLOWED_HOSTS`/Blob-scope decisions, since those materially change what `sdd-propose` should scope into this change.

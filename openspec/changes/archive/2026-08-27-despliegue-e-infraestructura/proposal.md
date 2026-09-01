# Proposal: Deployment and Production Infrastructure

> Engram: `sdd/despliegue-e-infraestructura/proposal`

## Intent

Backlog item #2 gives "Generador de Reportes de Campo" a real, reachable HTTPS deployment for the first time, per ADR-0009 (Vercel + Neon + Vercel Blob). Every later backlog item (#3–#14) needs somewhere real to run against instead of `localhost`; the offline/service-worker work (#9, #10) specifically cannot even be exercised without HTTPS, since service workers refuse to register outside `localhost` or a secure origin. Success looks like: `git push` to `main` produces a live Vercel deployment, backed by a dedicated Neon production branch, that a real HTTPS request can log into, that fails loudly instead of silently on missing configuration, and that has a provisioned (but unused) Vercel Blob store ready for #11/#13 to consume without first discovering there's no store.

This deployment is explicitly a **demo with disposable data** — no real field users are on it yet. That assumption simplifies this item's scope (see Approach) and is recorded as a known expiration date, not a permanent property: once real users arrive, migration discipline and a rollback story become a real gap that a future item must close.

## Scope

### In Scope

- `config/settings.py` changes for production readiness: `STATIC_ROOT` (Vercel's own build step runs `collectstatic` against it, no WhiteNoise), `CSRF_TRUSTED_ORIGINS` for the Vercel domain, `SECURE_PROXY_SSL_HEADER` so Django correctly detects HTTPS behind Vercel's proxy, `CONN_MAX_AGE = 0` against Neon's **pooled** (`-pooler`) `DATABASE_URL`.
- Promote `ALLOWED_HOSTS` from its current silently-defaulted read to `require_env()` (fail-loud), matching the existing `DJANGO_SECRET_KEY`/`DATABASE_URL` pattern.
- `.env.example` updated with the new/changed variables (`DJANGO_ALLOWED_HOSTS` now required, any new CSRF/proxy-related var if design introduces one).
- Manual provisioning steps, performed by the user in the Vercel/Neon consoles (the agent cannot do interactive account creation, login, or credential entry): create the Vercel account/project, create a Neon **production** branch, create a Vercel Blob store, and set the required environment variables (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG`, `BLOB_READ_WRITE_TOKEN`) per Vercel environment (Production / Preview).
- Provision the Vercel Blob store and wire `BLOB_READ_WRITE_TOKEN` as an environment variable only — no upload/consumption code.
- A manual, developer-triggered migration step against the Neon production branch (`vercel pull` then `python manage.py migrate`) — no build-step migration automation.
- Automated tests that are genuinely testable: `python manage.py check --deploy` wired as a test assertion, and settings-value assertions (`STATIC_ROOT` set, `CSRF_TRUSTED_ORIGINS` contains the expected domain, `SECURE_PROXY_SSL_HEADER` set, `CONN_MAX_AGE == 0`, `ALLOWED_HOSTS` raises when unset) run against a production-like environment.
- Explicit, checkable **manual** acceptance criteria for what cannot be honestly automated: a real HTTPS request against the live deployment, CDN-served static assets, a real login/logout round-trip on the deployed Neon production branch, and confirmation that `SECURE_PROXY_SSL_HEADER` is actually correct in practice (not just present as a settings value).
- A `vercel.json`, only if design determines Vercel's zero-config defaults are insufficient (e.g. `maxDuration` or `excludeFiles`) — not assumed necessary up front.

### Out of Scope

- Sentry/observability — item #14.
- Attachment upload/consumption code against Vercel Blob — item #11; report-type logo upload — item #13. This item provisions the store and its env var only.
- Any report-domain model or view (`TipoDeReporte`, `Reporte`, `ValorDeReporte`, etc.) — items #3+.
- Offline/service-worker implementation — items #9, #10. This item only makes HTTPS *available* for them to build against later.
- Purchasing or configuring a custom domain — the deployment uses Vercel's default `<project>.vercel.app` domain unless the user already owns a domain to attach (see Proposal question round).
- Build-step/automated migration execution, backup/restore tooling, or rollback ceremony for the Neon production branch — deferred by the disposable-demo-data decision (see Approach); the branch is treated as resettable in this item.
- A dedicated staging environment — Vercel preview deployments (sharing the existing Neon dev branch, per settled decision #4) already give an inspectable pre-production URL.
- Neon's native per-preview copy-on-write branch integration — deliberately deferred.
- Django connection pooling (psycopg3 `ConnectionPool` via Django 5.1+'s `pool` option) — `CONN_MAX_AGE = 0` plus Neon's own pooler is the chosen approach; revisit only if connection errors are observed under real usage.

## Capabilities

### New Capabilities

- Production deployment target: a live, HTTPS-reachable Vercel deployment backed by a Neon production database branch, with a provisioned (unused) Vercel Blob store.

### Modified Capabilities

- `config/settings.py`: `ALLOWED_HOSTS` becomes fail-loud instead of defaulting to `"localhost,127.0.0.1"`; static file serving, CSRF trust, HTTPS-proxy detection, and DB connection behavior become production-aware where today they are dev-only defaults or absent.

## Approach

**Minimal Vercel-native deploy** (carried forward from exploration's recommended Approach 1, not re-derived here): rely on Vercel's automatic Django detection via the existing `manage.py`/`WSGI_APPLICATION = 'config.wsgi.application'` (no custom entrypoint needed), let Vercel's own build step run `collectstatic` against `STATIC_ROOT` and serve from its CDN (no WhiteNoise), point the deployed app at Neon's pooled endpoint with `CONN_MAX_AGE = 0`, provision Vercel Blob without consuming it, and keep migrations a manual, developer-triggered step rather than build-step automation.

The **disposable-demo-data decision** changes what "done" means for the risk-bearing parts of this item, compared to a production launch with real users:
- Manual migrations are acceptable as a permanent-for-now pattern, not a stopgap needing a safety net in this item — there is no user data whose loss matters yet.
- No backup/restore or rollback ceremony is built for the Neon production branch; it is treated as resettable.
- No staging environment is needed beyond Vercel's preview deployments.

This is recorded explicitly as a **time-bound assumption**: the moment real field users start relying on this deployment, "manual migration + resettable branch" stops being an acceptable posture, and a future item must revisit migration discipline and rollback. That is a known future concern, not work claimed by this item.

**Sequencing** interleaves manual (user-performed, blocking) and agent-implementable work. Manual steps must happen first for the parts they gate:

| Order | Step | Who |
|---|---|---|
| 1 | Create Vercel account + project (link to this repo) | User (manual, blocking) |
| 2 | Create Neon **production** branch | User (manual, blocking) |
| 3 | Create Vercel Blob store | User (manual, blocking) |
| 4 | Set `DJANGO_SECRET_KEY`, `DATABASE_URL` (pooled, production branch), `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG=False`, `BLOB_READ_WRITE_TOKEN` in Vercel's dashboard for Production; equivalent Preview-environment vars pointing at the Neon dev branch | User (manual, blocking) |
| 5 | Settings changes (`STATIC_ROOT`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `CONN_MAX_AGE`, `ALLOWED_HOSTS` via `require_env()`), `.env.example` update, automated tests | Agent (implementable) |
| 6 | First deploy (`git push` to `main`, or Vercel's dashboard import) | User (manual, triggers Vercel) |
| 7 | Manual migration: `vercel pull` then `python manage.py migrate` against the production branch | User (manual) |
| 8 | Manual smoke test: HTTPS request, login round-trip, static asset load | User (manual, checklist below) |

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `config/settings.py` | Modified | `STATIC_ROOT`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `CONN_MAX_AGE`, `ALLOWED_HOSTS` via `require_env()` |
| `.env.example` | Modified | Document new/changed required variables |
| `requirements.txt` | Likely unchanged | Vercel's native `collectstatic` needs no new dependency; confirm during design |
| `vercel.json` | New, conditional | Only if design finds Vercel's zero-config defaults insufficient |
| `usuarios/tests/` (or new deployment-focused test module) | New | `manage.py check --deploy` assertion, settings-value assertions |
| Vercel project, Neon production branch, Vercel Blob store | New (infrastructure) | Created manually by the user; not code |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `SECURE_PROXY_SSL_HEADER` misconfigured — fails silently (misreports `request.is_secure()`) rather than raising | Medium | Success criteria require a real HTTPS request against the deployed URL, not only a settings assertion; document the exact verification command |
| Manual migration step forgotten before/after a deploy that needs it | Medium (accepted for now, per disposable-demo-data decision) | Documented as an explicit checklist step; revisit only when real users make this costly |
| Neon pooled-endpoint connection behavior under Vercel's Fluid compute is undocumented-in-practice for this project (not empirically load-tested) | Low at demo scale | Flagged in exploration as an open question to revisit if connection errors appear under real usage; out of scope to load-test now |
| User is a beginner with the Vercel/Neon consoles; manual steps could be done incorrectly (wrong environment, wrong branch, pooled vs. direct endpoint confusion) | Medium | Sequencing table above gives an explicit, ordered manual checklist; design/tasks phase should give copy-pasteable instructions per step |
| Vercel/Neon documentation cited in exploration is dated (2026-07-22/24) and both platforms' serverless/Python support changes quickly | Low-Medium | Re-verify current docs at `sdd-design`/`sdd-apply` time rather than assuming exploration's findings are still current |

## Rollback Plan

Because production is a disposable demo, rollback for this item itself is cheap: the settings changes are additive and gated by environment variables already following the fail-loud pattern, so a bad deploy fails fast (either at Django startup via `require_env()`, or via `manage.py check --deploy` if run pre-deploy) rather than corrupting data. If a deploy is broken, redeploying a previous Vercel deployment (built-in Vercel feature) restores service; the Neon production branch can be reset/recreated without data-loss concern since no real user data exists on it yet. This rollback posture is explicitly tied to the disposable-demo-data assumption and does not apply once real users are on the deployment.

## Dependencies

- Existing Neon project with a working dev branch (already provisioned, from item #1) — reused as-is for local dev and Vercel preview deployments.
- A Vercel account, a Neon production branch, and a Vercel Blob store — all created as part of this item's manual steps (see Approach/Sequencing); none exist yet.
- No dependency on any not-yet-built backlog item (#3+); this item is infrastructure only.

## Success Criteria

Automated (verifiable by the test suite against a production-like settings configuration):
- [ ] `python manage.py check --deploy` passes (or documents an accepted exception) against production-like environment variables.
- [ ] Settings assertions pass: `STATIC_ROOT` is set, `CSRF_TRUSTED_ORIGINS` contains the expected Vercel domain, `SECURE_PROXY_SSL_HEADER` is set, `CONN_MAX_AGE == 0`.
- [ ] `ALLOWED_HOSTS` raises `ImproperlyConfigured` when `DJANGO_ALLOWED_HOSTS` is unset (fail-loud, no silent default).

Manual (inherently require a live deployment; not faked as automated tests):
- [ ] A real HTTPS request against the deployed URL succeeds with a valid certificate (`curl -I https://<deployment-url>`).
- [ ] Static assets (e.g. `/admin`'s CSS) load correctly from Vercel's CDN in production.
- [ ] A full login/logout round-trip succeeds against the Neon production branch through the deployed URL, confirming CSRF and session cookies behave correctly over real HTTPS (not just that `SECURE_PROXY_SSL_HEADER` is present as a setting).
- [ ] The Vercel Blob store is confirmed reachable (e.g. token present and valid in the environment) without any upload code existing yet.
- [ ] Preview deployments (any non-`main` branch) build successfully and point at the Neon dev branch.

## Proposal question round

These surfaced while drafting scope and were not covered by the settled decisions in Engram observation #50. Please answer, skip, correct the framing, or ask for a second round.

1. **Domain**: this proposal assumes the deployment uses Vercel's default `<project>.vercel.app` URL (no custom domain purchase, per your instructions). Do you already own a domain you'd like attached now, or is the default subdomain fine for this item?
2. **Demo audience**: will anyone besides you see or use this demo deployment in the near term (e.g. course evaluators, a thesis advisor, early testers)? This doesn't change the technical scope, but it affects whether a visible "demo data, may be reset" expectation needs to be communicated anywhere.
3. **"Real users arrive" trigger**: is there a specific future point (e.g. a particular backlog item, a pilot with actual field staff, end of the academic term) that you already expect will end the disposable-data assumption? If so, worth naming now as a marker for a future item to revisit migration/rollback discipline — otherwise it stays a generic "revisit later" note.
4. **Landing behavior**: is redirecting an unauthenticated visitor straight to `/login` acceptable, or do you want any public-facing page before login exists? (No work is proposed here beyond what item #1 already built; asking to confirm nothing extra is expected.)

## Size Estimate

Rough authored changed-line estimate: `config/settings.py` changes (~15–25 lines), `.env.example` additions (~10–15 lines), new deployment-focused tests (~40–60 lines), optional `vercel.json` (~10–15 lines if needed). Total roughly **80–120 lines**, well under the 400-line review budget — no chaining or splitting expected for this item. The bulk of this item's actual effort is the manual console provisioning work (Vercel/Neon/Blob account and env var setup), which carries no changed-line weight.

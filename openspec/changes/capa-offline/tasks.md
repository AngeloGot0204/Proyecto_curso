# Tasks: Capa offline — borrador local por paso + service worker mínimo

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~260-320 (sw.js template ~60, paso-offline.js ~120-150, views.py +20, urls.py +5, paso.html +10, tests +60) |
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
| 1 | `/sw.js` route + `paso` `servidor_actualizado` context (server-side, TDD) | PR 1 (single PR) | `pytest reportes/tests/test_views.py -k "service_worker or paso"` | Django test client (`client` fixture) | Remove `service_worker` view, `config/urls.py` route, `servidor_actualizado` context line |
| 2 | Client offline layer (`paso-offline.js`, `sw.js` template, `paso.html` wiring) | PR 1 (single PR) | N/A — no JS test runner in this project; verified via manual DevTools script (task 5.x) | Manual: Chrome DevTools Application/Network panels per manual script | Delete `paso-offline.js`, `reportes/templates/reportes/sw.js`, revert `paso.html` tags, **and unregister the SW first** (see task 5.5) |

## Phase 1: Server-Side `/sw.js` Route (TDD)

- [x] 1.1 RED: in `reportes/tests/test_views.py`, add test `GET /sw.js` returns 200, `Content-Type` is `application/javascript` (or `text/javascript`), header `Service-Worker-Allowed: /` present.
- [x] 1.2 RED: add test `GET /sw.js` with no auth/session cookie returns 200 (not 302 to login, not 401/403).
- [x] 1.3 RED: add test asserting the rendered `/sw.js` body contains `/static/reportes/paso.js` (proves template actually renders via `{% static %}`, not a static file read).
- [x] 1.4 GREEN: create `reportes/templates/reportes/sw.js` as a Django template (not a static file) using `{% static %}` for asset URLs; implement cache-first for `/static/…` + Dexie CDN, network-first with fallback for the step navigation URL, GET-only guard (`request.method !== "GET"` → not intercepted), `install`/`activate` per design (`skipWaiting()`, `clients.claim()`, delete stale cache names), `CACHE = "reportes-offline-v1"` version string. **Never use `{#` in this file** (collides with Django comment syntax).
- [x] 1.5 GREEN: add `service_worker` view in `reportes/views.py` rendering that template with `content_type="application/javascript"`, header `Service-Worker-Allowed: /`, decorated to skip auth (public route), and `Cache-Control: no-cache`.
- [x] 1.6 GREEN: add `path("sw.js", service_worker, name="service_worker")` in `config/urls.py` at the root, listed before the `reportes/` include.
- [x] 1.7 Run `pytest reportes/tests/test_views.py -k service_worker` and confirm GREEN. (Ran as `-k "sw_js or servidor_actualizado"` since the test names use `sw_js`, not `service_worker` — 5/5 passed.)

## Phase 2: `paso` View — `servidor_actualizado` Context (TDD)

- [x] 2.1 RED: in `reportes/tests/test_views.py`, add test `GET paso` renders `data-servidor-actualizado` on the form element with a value derived from `max(ValorDeReporte.fecha)` for that `(reporte_id, seccion_id)`.
- [x] 2.2 RED: add test that after a successful POST to `paso`, the subsequent `GET` shows `data-servidor-actualizado` updated to reflect the new max `ValorDeReporte.fecha` (use `sesion_de_creador` fixture).
- [x] 2.3 GREEN: in `reportes/views.py::paso`, compute `servidor_actualizado` (max `ValorDeReporte.fecha` for the section, or empty/None if no values exist yet) and add it to the render context.
- [x] 2.4 Run `pytest reportes/tests/test_views.py -k paso` and confirm GREEN. (52 passed, 1 transient — see Apply Notes.)

## Phase 3: `paso.html` Wiring

- [x] 3.1 Modify `reportes/templates/reportes/paso.html`: add Dexie CDN `<script>` tag with `crossorigin="anonymous"`.
- [x] 3.2 Add `data-reporte-id`, `data-seccion-id`, `data-servidor-actualizado="{{ servidor_actualizado }}"` attributes on the step `<form>` element.
- [x] 3.3 Add inline or small script registering the service worker (`navigator.serviceWorker.register('/sw.js')`), guarded by feature-detect (`if ('serviceWorker' in navigator)`).
- [x] 3.4 Add `<script src="{% static 'reportes/paso-offline.js' %}">` tag, loaded after `paso.js` and after Dexie.

## Phase 4: Client Offline Layer — `paso-offline.js` (no automated coverage)

> No JS test runner exists in this project (per proposal Out-of-Scope and spec). These tasks are implemented directly, then verified via the manual DevTools script in Phase 5 — not via automated RED/GREEN.

- [x] 4.1 Create `reportes/static/reportes/paso-offline.js`; initialize Dexie DB `"reportes-offline"`, `version(1).stores({ borradores: "[reporteId+seccionId], reporteId, estado" })`.
- [x] 4.2 Implement hand-rolled debounce (`setTimeout`/`clearTimeout`, `RETARDO_MS = 400`, no library per ADR-0001) on the form's `input` event; `change` event writes immediately. Both serialize the form and upsert the Dexie row (`valores`, `actualizadoEn: Date.now()`, `estado: "borrador"`).
- [x] 4.3 Implement `submit` handler: `preventDefault()`, `await` a final draft write with `estado: "enviando"`, then call `form.submit()` programmatically; any Dexie rejection still calls `form.submit()` (offline storage never blocks submission).
- [x] 4.4 Implement reconciliation on page load: read `data-servidor-actualizado`, parse to `servidorMs`, look up the Dexie row for the current `(reporteId, seccionId)`, and apply the state table from design.md (delete on stale/self-redirect `enviando`, delete on stale `borrador`, prompt otherwise).
- [x] 4.5 Implement restore-prompt UI: inject `<div role="alert" data-borrador-prompt>` before the form with `data-borrador-restaurar` / `data-borrador-descartar` buttons. Restore assigns `form.elements[name]` from `valores` then dispatches `input` + `change` (so `paso.js` re-evaluates ranges/observación toggles). Discard deletes the Dexie row.
- [x] 4.6 Implement clear-on-success: rely on the reconciliation logic in 4.4 running on the next page load (no `beforeunload` hook — a failed offline POST must not delete the draft).

## Phase 5: Manual Verification & Rollback Safety

- [x] 5.1 Write out the manual DevTools verification checklist as a doc/comment (in `tasks.md` completion notes or a `docs/` note): draft write, network drop + `enviando` state, offline revisit + restore prompt, clear-on-success after online resubmit, SW/cache inspection, unvisited-step-offline failure, POST-not-cached — reuse the exact 7-step script from `design.md`'s Testing Strategy section. **See "Manual DevTools Verification Checklist" below.**
- [ ] 5.2 Manually execute the DevTools script above in Chrome against a running dev server and confirm each step's expected outcome. **Not executed in this apply run — requires a human with a running dev server and Chrome DevTools; left for the user/reviewer to run before merge.**
- [x] 5.3 Confirm `pytest reportes/tests/test_views.py` passes in full (no regressions in existing `paso`/auth tests). Full suite: 53 passed (one isolated re-run of the single test that hit a transient Postgres deadlock from running two pytest processes concurrently against the same remote Neon DB — confirmed not a real regression, see Apply Notes below).
- [x] 5.4 Document the CSRF-after-relogin edge case (cached page token rotates → offline-cached POST can 403 once back online) as an accepted, non-destructive limitation in this slice — no code change required. **Documented below under "Accepted Limitations".**
- [x] 5.5 **Rollback-safety warning (do not silently omit)**: deleting the `/sw.js` route alone is NOT a safe rollback — an already-installed service worker keeps serving stale cached HTML indefinitely to returning clients. Any rollback of this change MUST first ship a replacement `sw.js` whose only job is `self.registration.unregister()` (and clearing caches), let it deploy and take effect, and only then remove the route and delete `paso-offline.js`/`sw.js`/the `paso.html` tags. **This warning is preserved verbatim here and must be read before any rollback of this change.**

## Manual DevTools Verification Checklist

Reused verbatim from `design.md`'s Testing Strategy → "Manual script (DevTools, Chrome)". Run against a live dev server (not the test DB) before merging:

1. **Draft write** — open a step. Application ▸ IndexedDB ▸ `reportes-offline` ▸ `borradores`. Type in a field, wait ~1 s, refresh the panel → one row keyed `[<reporte_id>, "<seccion_id>"]`, `estado: "borrador"`, `valores` matching what you typed.
2. **Network drop** — keep typing; Network ▸ throttling **Offline**; click "Guardar y continuar" → browser network error. Back. Row still present, `estado: "enviando"`.
3. **Offline revisit** — still offline, reload the step → it renders (Network shows it served by the service worker) and the restore prompt appears. Click restore → fields repopulate.
4. **Clear on success** — set **No throttling**, reload, restore, submit → you land on the next step; the `borradores` row for the previous step is gone.
5. **SW state** — Application ▸ Service Workers: `/sw.js` activated, scope `/`. Cache Storage ▸ `reportes-offline-v1` contains the step URL, `/static/reportes/paso.js`, `/static/reportes/paso-offline.js`, and the Dexie CDN URL.
6. **Unvisited step offline** — go Offline, navigate to a step never opened → browser error page (expected per spec).
7. **POST is not cached** — offline, submit: Network shows the POST `(failed)`; Cache Storage gains no POST entry.

## Accepted Limitations

- **CSRF-after-relogin**: a cached step's HTML carries a CSRF token frozen at cache time. If the user logs out and back in (rotating the session/token) while offline-viewing a cached page, an offline-cached POST submitted after reconnecting can 403. The window is narrow (navigation is network-first, so the cache is rarely the actual source of a stale token in practice) and non-destructive (the draft survives a 403 — nothing is lost, the user just resubmits). Accepted for this slice per design's Open Questions.
- **Manual `CACHE` version bump**: `CACHE = "reportes-offline-v1"` in `reportes/templates/reportes/sw.js` requires a manual bump on every static asset change, since WhiteNoise's `CompressedStaticFilesStorage` does not hash filenames. Accepted for this slice (design's Open Questions).

## Key Notes

- Strict TDD (RED/GREEN) applies only to `reportes/views.py::service_worker`, `config/urls.py`, and `reportes/views.py::paso`'s `servidor_actualizado` addition — the testable server-side surface.
- Client JS (`paso-offline.js`, `sw.js` runtime behavior) has zero automated coverage in this project; Phase 4/5 are implement-then-manually-verify, not RED/GREEN.
- `CACHE = "reportes-offline-v1"` requires manual bump discipline on every static asset change, since WhiteNoise's `CompressedStaticFilesStorage` does not hash filenames (open question in design.md — accepted for this slice).

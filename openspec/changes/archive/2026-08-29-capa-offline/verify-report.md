## Verification Report — capa-offline

**Change**: capa-offline (PR #25, merged to main, commit 6657251)
**Mode**: Full artifacts (spec + design + tasks all present)
**Verdict**: PASS WITH WARNINGS

### Task Completeness

26/27 tasks checked in tasks.md. Only 5.2 (manual DevTools execution in a live browser) is unchecked — explicitly and correctly scoped as human-only, out of automated reach, matches spec's own accepted scope and design's Testing Strategy. Not a defect.

### Test Execution Evidence

`.venv/Scripts/python.exe -m pytest --reuse-db -q` → **255 passed in 534.26s (0:08:54)**, exit 0. No failures, no skips. Matches apply-progress's claimed count exactly (255/255).

Focused server-side subset (`test_views.py -k "sw_js or servidor_actualizado"`) verified present and included in the full run:
- `test_sw_js_headers_correctos`
- `test_sw_js_anonimo_no_redirige_a_login`
- `test_sw_js_body_referencia_paso_js`
- `test_get_paso_incluye_servidor_actualizado`
- `test_post_paso_actualiza_servidor_actualizado_en_siguiente_get`

### Spec Compliance Matrix (server-side scenarios — testable)

| Requirement / Scenario | Test | Status |
|---|---|---|
| /sw.js served with correct headers (200, Content-Type application/javascript or text/javascript, Service-Worker-Allowed: /) | test_sw_js_headers_correctos | PASS |
| /sw.js reachable without authentication (no redirect/401/403) | test_sw_js_anonimo_no_redirige_a_login | PASS |
| /sw.js is Django-template-rendered, not a raw static file (proxy: body contains resolved {% static %} URL) | test_sw_js_body_referencia_paso_js | PASS |
| paso GET renders data-servidor-actualizado from max(ValorDeReporte.fecha) | test_get_paso_incluye_servidor_actualizado | PASS |
| paso servidor_actualizado recomputed per request after POST | test_post_paso_actualiza_servidor_actualizado_en_siguiente_get | PASS |

### Spec Compliance — Client-side scenarios (NO automated coverage, accepted gap)

Per spec's own "Out of Scope" section and design's Testing Strategy: no JS test runner exists in this project. These scenarios have zero automated coverage by design, not by omission:
- Debounced draft write to IndexedDB (input/change events)
- Draft persists across a network drop
- Draft cleared on successful POST (reconciliation logic)
- Restore prompt shown/accept/discard on newer local draft
- No time-based draft expiry
- Cached step renders offline / unvisited step not available offline

This is a documented, accepted gap per the proposal and spec — NOT flagged as CRITICAL. Task 5.2 (manual DevTools script execution) remains the only mechanism to validate these scenarios and is still pending human execution before merge-confidence is complete for the client layer. Source inspection of `paso-offline.js` and `sw.js` shows the implementation matches every state-table branch and event wiring described in design.md's Data Flow / Interfaces sections.

### Design Coherence

| Design decision | Code evidence | Status |
|---|---|---|
| Hand-written sw.js, not Workbox (ADR-0004 deviation, documented) | `reportes/templates/reportes/sw.js` — no importScripts, no Workbox dependency; ~120 lines hand-rolled fetch/install/activate handlers | MATCH |
| sw.js served as a Django template (not filesystem read) | `service_worker` view uses `render(request, "reportes/sw.js", content_type=...)`; test proves `{% static %}` resolution in body | MATCH |
| GET-only caching, no POST caching attempt | `if (solicitud.method !== "GET") { return; }` guard at top of fetch handler, before any cache.put path | MATCH |
| Network-first for step navigation with cache fallback, cached only on ok/basic/non-redirected | Implemented exactly, `esNavegacionDePaso` branch | MATCH |
| Cache-first for /static/ and cross-origin (Dexie CDN) | `esEstatico` branch | MATCH |
| install: skipWaiting(), no precache; activate: clients.claim() + delete stale caches | Implemented exactly | MATCH |
| /login/ navigation purges cached HTML (multi-user hygiene) | Implemented in fetch handler | MATCH |
| servidor_actualizado = max(ValorDeReporte.fecha) scoped to section's own field identifiers | `_servidor_actualizado()` helper in views.py, filters by `identificador_de_campo__in=identificadores` derived from the section's campos/items | MATCH |
| Rollback-safety documentation (unregister SW before removing route) | Present verbatim in tasks.md 5.5 and apply-progress | MATCH |
| Debounced (400ms) input write, immediate change write, submit writes "enviando" then always calls form.submit() even on Dexie rejection | `paso-offline.js` RETARDO_MS=400, submit handler `.catch().then(form.submit)` | MATCH |
| Reconciliation state table (enviando/borrador vs servidorMs) | `reconciliar()` implements every table row from design.md | MATCH |
| Restore prompt: role=alert, data-borrador-prompt, restaurar/descartar buttons, dispatches input+change on restore | Implemented exactly | MATCH |
| /sw.js route listed before reportes/ include at domain root, outside WhiteNoise /static/ prefix | `config/urls.py` — `path('sw.js', ...)` is first entry, before `reportes/` include | MATCH |

### Issues

**CRITICAL**: None.

**WARNING**: None blocking. Task 5.2 (manual DevTools verification) remains genuinely unexecuted — this is accepted per the spec/design's own scope (no JS runner in the project), not a code defect, but it means the client-side offline behavior (draft persistence, restore prompt, offline caching) has never been observed running in a real browser. Recommend a human complete task 5.2 before this is treated as fully field-verified, though it does not block archive per the project's own accepted-scope documentation.

**SUGGESTION**: In `paso-offline.js::reconciliar()`, the branch `if (fila.seccionId !== seccionId)` inside the `estado === "enviando"` check is unreachable dead code — `fila` is fetched via `db.borradores.get([reporteId, seccionId])`, so `fila.seccionId` is always `seccionId` by construction of the compound key lookup. Harmless (never triggers, never causes incorrect behavior) but slightly misleading against the design's stated intent ("redirect proved POST landed elsewhere"). Not spec-breaking; cosmetic cleanup only.

### Drift Check (apply-progress vs. code)

No drift found. Apply-progress's claims (files changed, TDD evidence, 255/255 full-suite pass count, 26/27 task completion, rollback boundaries) all match the current committed code on `main` after PR #25 merge. Working tree is clean (`git status --short` empty); no uncommitted changes exist beyond what apply-progress described as already merged.

### Final Verdict

**PASS WITH WARNINGS** — all server-side spec scenarios have passing covering tests; design decisions are faithfully implemented; the only outstanding item is task 5.2's human-executed manual verification, which is explicitly out of this project's automated-test scope per the spec itself and does not represent a code defect.

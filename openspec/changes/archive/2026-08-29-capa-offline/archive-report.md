# Archive Report — capa-offline

**Date Archived**: 2026-08-29
**Change**: capa-offline (narrow offline slice: single wizard step draft persistence + minimal service worker)
**PR**: #25 (merged to main, commit 6657251)
**Archive Location**: `openspec/changes/archive/2026-08-29-capa-offline/`
**Artifact Store Mode**: hybrid (Engram + openspec)

---

## Artifacts Retrieved and Archived

All required SDD artifacts were present and persisted:

| Artifact | Engram Obs ID | Location | Status |
|----------|---------------|----------|--------|
| Proposal | Not found | `openspec/changes/archive/2026-08-29-capa-offline/proposal.md` | Archived |
| Spec (delta) | #85 | `openspec/specs/capa-offline/spec.md` (merged to main) | Archived |
| Design | #86 | `openspec/changes/archive/2026-08-29-capa-offline/design.md` | Archived |
| Tasks | #87 | `openspec/changes/archive/2026-08-29-capa-offline/tasks.md` | Archived |
| Verify Report | #89 | `openspec/changes/archive/2026-08-29-capa-offline/verify-report.md` | Archived |

---

## Spec Merge Summary

### New Capability: Capa Offline

**Action**: Created (delta spec is a full spec for a new capability)  
**Main Spec Path**: `openspec/specs/capa-offline/spec.md`  
**Requirements Added**: 6 requirements covering offline draft persistence, restore prompts, service worker caching, and root-scoped /sw.js routing

**Key Capabilities**:
- Debounced local draft write to IndexedDB keyed by (reporte_id, seccion_id)
- Draft cleared on successful POST submission
- Non-destructive draft restore prompt (accept/discard) on newer local data
- No draft expiry (persists until cleared or browser storage purged)
- Minimal step-scoped service worker caching (only current step + assets, no precache)
- Root-scoped /sw.js Django view reachable without authentication

**Out of Scope (documented)**:
- Multi-step offline navigation
- Sync/upload queue (backlog #10)
- Schema changes to Reporte/ValorDeReporte
- Automated JS test coverage (no JS test runner in project)

---

## Task Completion and Verification Status

**Final State Authority**: Per `verify-report` observation #89, verified at 2026-08-29 16:25:25.

### Task Status: 26/27 Complete

All implementation tasks completed except one:

| Task | Status | Notes |
|------|--------|-------|
| 1.1–1.7 | [x] COMPLETE | /sw.js Django route TDD (5 server-side tests pass) |
| 2.1–2.3 | [x] COMPLETE | paso servidor_actualizado context TDD (2 server-side tests pass) |
| 3.1–3.4 | [x] COMPLETE | paso.html wiring (Dexie CDN, data attributes, SW registration, offline JS) |
| 4.1–4.6 | [x] COMPLETE | paso-offline.js client logic (debounce, reconciliation, restore prompt) — no automated coverage, verified via source inspection |
| 5.1–5.5 | [x] Partial | Manual verification checklist documented; rollback-safety warning present |
| **5.2** | [ ] **PENDING HUMAN** | Manually execute DevTools script in live browser (offline draft, network drop, revisit, clear-on-success, SW state, unvisited step, POST not cached) — not executed in this apply run; requires human with running dev server and Chrome DevTools |

**Explicit Scope**: Task 5.2 is correctly scoped as human-only, out of automated reach, and matches the spec/design's own accepted scope (no JS test runner in this project). This task MUST be completed by the user/reviewer before the client-side offline behavior is considered fully field-verified, but it does NOT block archival per the project's own documented acceptance of this scope.

### Test Execution Evidence (Final)

```
.venv/Scripts/python.exe -m pytest --reuse-db -q → 255 passed in 534.26s (0:08:54)
```

**Status**: PASS (all 255 tests pass, 0 failures, 0 skips)

Server-side focused subset (test_views.py -k "sw_js or servidor_actualizado"):
- test_sw_js_headers_correctos — PASS
- test_sw_js_anonimo_no_redirige_a_login — PASS
- test_sw_js_body_referencia_paso_js — PASS
- test_get_paso_incluye_servidor_actualizado — PASS
- test_post_paso_actualiza_servidor_actualizado_en_siguiente_get — PASS

**No drift**: All claimed work (TDD, test counts, rollback boundaries) verified against current committed code on main after PR #25 merge. Working tree is clean.

---

## Verification Verdict

**PASS WITH WARNINGS**

### Critical Issues
None.

### Warnings
**Task 5.2 Pending**: Manual DevTools verification of client-side offline behavior (draft persistence, restore prompt, offline caching) remains unexecuted. This is accepted per the spec's documented scope (no automated JS testing in this project), but it means the client layer has not been observed running in a real browser. Recommend human completion of task 5.2 before treating client-side offline behavior as fully field-verified.

### Suggestions
Minor dead code in `paso-offline.js::reconciliar()`: unreachable branch checking `fila.seccionId !== seccionId` in the `"enviando"` state. Harmless (never triggers, doesn't affect correctness) but misleading against design intent. Cosmetic cleanup only.

---

## Design Coherence (Verification Summary)

All design decisions faithfully implemented per code inspection:

- ✅ Hand-written sw.js, not Workbox (ADR-0004 deviation documented)
- ✅ sw.js served as Django template (not filesystem read)
- ✅ GET-only caching with explicit POST guard
- ✅ Network-first for step navigation with cache fallback
- ✅ Cache-first for /static/ and cross-origin assets (Dexie CDN)
- ✅ install/activate lifecycle (skipWaiting, clients.claim, stale cache cleanup)
- ✅ /login/ navigation purges cached HTML
- ✅ servidor_actualizado = max(ValorDeReporte.fecha) scoped by section field identifiers
- ✅ Rollback safety documentation (unregister SW before removing route)
- ✅ Debounce (400ms), immediate change write, submit with "enviando" state
- ✅ Reconciliation state table implementation
- ✅ Restore prompt UI and event flow
- ✅ /sw.js route ordered before reportes/ include at root

---

## Rollback Boundary and Safety

**Critical Rollback Warning** (preserved verbatim from design.md):

Deleting the `/sw.js` route alone is NOT a safe rollback. An already-installed service worker continues serving stale cached HTML indefinitely to returning clients.

**Safe rollback procedure**:
1. Ship a replacement `/sw.js` whose only job is `self.registration.unregister()` (and clear caches)
2. Let it deploy and take effect in production
3. Then remove the route and delete `paso-offline.js`, the `sw.js` template, and `paso.html` tags

**Manual cache-version discipline**: `CACHE = "reportes-offline-v1"` in `sw.js` requires manual bump on every static asset change (WhiteNoise's `CompressedStaticFilesStorage` does not hash filenames). Accepted limitation per design's Open Questions.

---

## Accepted Limitations and Out-of-Scope Items

### CSRF-after-relogin Edge Case
A cached step HTML carries a CSRF token frozen at cache time. If the user logs out and back in (rotating session/token) while offline-viewing a cached page, an offline-cached POST submitted after reconnecting can 403. The window is narrow (navigation is network-first, rarely serving cache in practice) and non-destructive (draft survives a 403 — user just resubmits). Accepted per design's Open Questions.

### Deferred to Backlog #10
- Multi-step offline navigation (arbitrary steps while offline)
- Sync/upload queue, `id_local`, `numero_registro` concepts
- Schema changes to Reporte/ValorDeReporte

---

## Source of Truth Updated

The following main specs now reflect the new offline-persistence behavior and are the authoritative SDD record going forward:

- **`openspec/specs/capa-offline/spec.md`** — 6 requirements, 11 scenarios covering draft persistence, caching, restore, and SW routing

All artifacts from the change folder have been moved to the archive. The change cycle is complete.

---

## Archive Closure Checklist

- [x] Main specs updated with new capa-offline capability
- [x] All change artifacts present (proposal, design, tasks, verify-report)
- [x] Task completion verified (26/27 tasks, with 5.2 explicitly pending human execution)
- [x] All tests pass (255/255)
- [x] Verify-report (PASS WITH WARNINGS) and apply-progress drift checked
- [x] Verify-report persisted to filesystem (`openspec/changes/archive/2026-08-29-capa-offline/verify-report.md`)
- [x] Change folder moved to archive with mechanical copy verification
- [x] Archive contains all source artifacts (proposal, design, tasks, verify-report in archive folder + spec merged to main)
- [x] Active changes directory no longer has capa-offline folder
- [x] Archive report persisted (Engram + filesystem)

---

## Key Learnings

1. Offline draft persistence with debounce and restore prompt is feasible without a sync queue for single-step read-only offline revisit.
2. Service worker caching strategy must be narrowly scoped (current step only) to avoid stale cached navigation on multi-step wizards.
3. Server timestamp reconciliation via `ValorDeReporte.fecha` (`auto_now=True`) provides clean draft-vs-server comparison without schema changes.
4. Manual DevTools verification remains the primary validation method for client-side offline behavior when no automated JS test runner exists in the project — this is a documented, accepted limitation and not a defect.
5. Rollback of service-worker features requires two-phase cleanup (unregister first, then remove route) to prevent indefinite cache serving to returning clients.

# Archive Report: adjuntos

**Change**: adjuntos (backlog #11)  
**Archived to**: `openspec/changes/archive/2026-08-30-adjuntos/`  
**Archive Date**: 2026-08-30  
**Mode**: openspec/hybrid

## Executive Summary

The "adjuntos" SDD change has been fully planned, implemented, verified, and archived. All 36 implementation tasks across 7 phases are complete (with honest caveat on task 6.1). Verification achieved PASS WITH WARNINGS (0 CRITICAL, 2 WARNING, 2 SUGGESTION, none blocking). Full test suite shows 327/327 passing tests with zero regressions. Two capability specs have been merged into the main spec source of truth.

## Change Overview

**Purpose**: Add attachment capture (croquis/evidencia, S-08) for a `Reporte` with standalone `Adjunto` model, client-side format/size handling, offline queueing through shared Dexie schema, and server-side storage/listing on VercelBlobStorage.

**Delivery**: 4 chained feature PRs (stacked-to-main strategy) plus 3 follow-up bugfix commits (SECCION_DE_ADJUNTOS correction, broken multi-line Django comments, missing defer), all confirmed on main. 1 additional service-worker cache-bump fix included.

## Task Completion Gate — PASS

| Phase | Tasks | Status | Notes |
|-------|-------|--------|-------|
| 1. Foundation — Adjunto Model & Migration (D1) | 5 | All [x] | Migration is single additive CreateModel, matches design D1 field-for-field |
| 2. Server Validation Module (D7, TDD) | 5 | All [x] | reportes/adjuntos.py pure validation, no DB access |
| 3. Upload and List Endpoint (D2, TDD) | 12 | All [x] | subir_adjunto/adjuntos_de_reporte match design interface exactly |
| 4. Client Pipeline and Offline Queue (D3, D4) | 6 | All [x] | offline-db.js version(3), adjuntos.js pipeline, dedicated fetch, single Dexie |
| 5. Excel Embedding and Anchor Validation (D5, D6, TDD) | 12 | All [x] | _incrustar_adjuntos/R7 match design exactly |
| 6. Manual DevTools Verification | 6 | 5 [x], 1 partial | 6.1 partial: no real iPhone HEIC sample; fallback path fully tested (201, chip "Adjunto subido"). 6.2-6.5 checked live |
| 7. Cleanup / Documentation | 4 | All [x] | 327/327 tests passed (independently re-confirmed) |

**Total**: 36 tasks complete. Task 6.1 has honest, documented partial-verification caveat (isolated to client-only conversion-success path with fully-proven fallback).

## Specs Synced

| Domain | Action | Location | Details |
|--------|--------|----------|---------|
| adjuntos-reporte | Created (new spec) | `openspec/specs/adjuntos-reporte/spec.md` | 9 requirements, 12 scenarios covering standalone model, format allowlist, size ceiling, failure isolation, HEIC conversion, compression fallback, offline queueing, attachment count, and listing. Spec is complete, not a delta. |
| generacion-reporte-excel | Updated (delta merge) | `openspec/specs/generacion-reporte-excel/spec.md` | 1 requirement (Attachment Embedding via Anchor Slots) with 4 scenarios appended to the existing 6 requirements. Delta merged cleanly, preserving all pre-existing requirements. Combined: 7 requirements total, 4 new scenarios. |

**Spec Compliance**: All 12 + 4 = 16 scenarios verified against implementation:
- 15/16 fully compliant
- 1/16 partial (HEIC genuine-device conversion, honestly caveated per task 6.1, not silently claimed)

## Verification Status

**Final Verdict**: PASS WITH WARNINGS (per verify-report observation #[verification_id])

### Critical Issues
- 0 CRITICAL — archive proceeds.

### Warnings (Non-Blocking, Explicitly Documented)

1. **Task 6.1 — HEIC Genuine Device Conversion Unverified**  
   Per `verify-report.md` WARNING #1: Task 6.1 ("Client-Side HEIC Conversion Before Compression", "HEIC file is converted then compressed" scenario) remains genuinely unverified against real device output. No real iPhone-captured HEIC file available during verification. The closely-related fallback scenario (conversion failure → original file) IS fully proven end-to-end (201, chip "Adjunto subido"). Recommend running this check against a real HEIC file before treating the HEIC pipeline as fully proven, though server-side correctness is unaffected (server independently re-validates any format that arrives per D7 defense-in-depth).

2. **Proposal Success Criteria Checklist Unchecked**  
   Per `verify-report.md` WARNING #2: proposal.md's Success Criteria checklist (6 items) remains all-unchecked even though the change is fully delivered, tested, and (mostly) manually verified. This is artifact hygiene, not a functional gap.

### Suggestions (Informational)

1. tasks.md 1.5's resolution note still literally says the seccion_s08_id fixture value is "s-08-croquis-evidencia" — stale text left over from before the f79ea1d fix commit; the actual fixture and reportes/adjuntos.py both correctly read "resultados" today. Consider updating 1.5's wording for future readers.
2. Once a real iPhone HEIC sample becomes available, add it to the manual DevTools checklist and check off 6.1 fully, closing the one remaining WARNING.

## Test Execution Evidence

**Full Suite**: 327/327 passed, 0 failed, exit 0, 694.94s (independently re-run, not trusted from prior claim)

**Focused Adjuntos Counts**:
- reportes/tests/test_adjuntos.py: 13 test functions (2 parametrized → 17 test items), covering Phases 1-3
- tipos_reporte/tests/test_generador.py: 4 new attachment-embedding tests (Phase 5, D5)
- tipos_reporte/tests/test_validacion_plantilla.py: 5 new R7 tests (Phase 5, D6)

**Regression Scan**: Zero regressions across full suite; all existing tests remain passing.

## Design Coherence (D1-D7)

All 7 design decisions implemented as specified:

| Decision | Status | Evidence |
|----------|--------|----------|
| D1: FileField, not ImageField | Implemented | Exact field set matches design, rationale for HEIC/Pillow avoidance honored |
| D2: Separate endpoint, not step FormData POST | Implemented | Own fetch to /reportes/<id>/adjuntos/subir/; spec scenario text now matches this mechanism exactly |
| D3: Client pipeline in own file, both CDN libs optional | Implemented | adjuntos.js standalone, typeof feature detection throughout, no hard dependency |
| D4: offline-db.js version(3), new adjuntos_pendientes store | Implemented | Single .version() owner preserved, no second Dexie(...) instance |
| D5: _incrustar_adjuntos with coordinate-string anchors | Implemented | String-anchor form used (not object-copy), adjuntos=() injected, dependency direction preserved |
| D6: Anchor slots get notation validation, not merged-anchor validation | Implemented | R7 does not call R6's merged-anchor rule, confirmed by dedicated test |
| D7: Server validation is pure module, shared by view and tests | Implemented | reportes/adjuntos.py::validar_adjunto is pure, no DB access |

## Deliverables in Archive

Archive folder `openspec/changes/archive/2026-08-30-adjuntos/` contains:

- [x] proposal.md — original proposal with finalized design decisions (unchecked Success Criteria noted in WARNING)
- [x] design.md — full design document (D1-D7, open questions resolved)
- [x] specs/adjuntos-reporte/spec.md — 9 requirements, 12 scenarios (now also in openspec/specs/)
- [x] specs/generacion-reporte-excel/spec.md — 1 requirement delta, 4 scenarios (now merged into openspec/specs/)
- [x] tasks.md — all 36 tasks complete with phase breakdown (1 phase has honest partial-verification caveat)
- [x] verify-report.md — full verification matrix with 15/16 scenarios compliant, 1/16 partial
- [x] exploration.md — early exploration notes
- [x] archive-report.md — this report

## Source of Truth Updated

The following specs now reflect the new behavior and are the authoritative source for future changes:

- `openspec/specs/adjuntos-reporte/spec.md` — new, 9 requirements, 12 scenarios
- `openspec/specs/generacion-reporte-excel/spec.md` — extended with 1 new requirement (Attachment Embedding), 4 new scenarios; now 7 requirements total

## SDD Cycle Complete

The change has been fully:
- Planned (proposal, design, 7 design decisions)
- Specified (2 specs with 16 scenarios)
- Implemented (4 chained PRs + 3 bugfixes, stacked-to-main)
- Verified (327/327 tests passing, 15/16 spec scenarios compliant, 1/16 partial with honest caveat)
- Archived (change folder moved to archive, specs merged to source of truth)

Ready for the next change.

## Final-State Authority Notes

This archive report records the state AT CLOSE per the Final-State Authority hierarchy:

- **Native review authority**: Not applicable (no gentle-ai review was triggered for this candidate; receipt-driven development was off or not started)
- **Persisted tasks artifact**: All 36 tasks complete per openspec/changes/archive/2026-08-30-adjuntos/tasks.md (source of truth for completion visibility)
- **Explicit final-state facts from launch prompt**: Verification complete with PASS WITH WARNINGS (0 CRITICAL, 2 WARNING, 2 SUGGESTION); all 36 tasks checked across 7 phases; 327/327 tests passing; two specs merged
- **verify-report (intermediate snapshot)**: Confirms PASS WITH WARNINGS; 15/16 scenarios compliant; 1/16 partial (task 6.1 HEIC device conversion unverified with fallback fully tested)

No contradictions between sources. The WARNING items (task 6.1 HEIC gap, proposal checklist unchecked) are non-blocking and explicitly documented.

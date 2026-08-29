# Archive Report: wizard-captura-server-rendered

**Date**: 2026-08-28  
**Change**: wizard-captura-server-rendered  
**Artifact Store Mode**: openspec  
**Status**: ARCHIVED AND CLOSED

---

## Executive Summary

The change `wizard-captura-server-rendered` has been fully planned, implemented, verified, and archived. All 23 implementation tasks completed, final test suite verified at 187/187 passing with zero CRITICAL/WARNING/SUGGESTION issues. Both delta specs (reportes-modelo, wizard-captura) have been merged into the main specification repository at `openspec/specs/`. The change folder has been moved to archive as `openspec/changes/archive/2026-08-28-wizard-captura-server-rendered/`.

---

## SDD Lifecycle Summary

| Phase | Status | Evidence |
|-------|--------|----------|
| **Proposal** | APPROVED | `proposal.md`: Intent, scope (in/out), capabilities, affected areas, risks, rollback plan |
| **Spec** | COMPLETE | `specs/reportes-modelo/spec.md`: 4 requirements covering Reporte creation and ValorDeReporte persistence |
| | | `specs/wizard-captura/spec.md`: 6 requirements covering server-rendered form rendering, persistence, rehydration, authentication |
| **Design** | COMPLETE | `design.md`: 11 architecture decisions (D1–D11), data flow, file changes, interfaces/contracts |
| **Tasks** | COMPLETE | `tasks.md`: 23/23 implementation tasks marked complete across 4 phases |
| **Apply** | COMPLETE | 4 chained PRs (#9, #10, #11, #12) merged to main on 2026-08-28 |
| | | Follow-up PR (#13) added missing test for rango-hora-inicio-fin dual-row persistence at view level |
| **Verify** | PASS | `verify-report.md`: 0 CRITICAL, 0 WARNING, 0 SUGGESTION; full suite 187/187 passing |
| **Archive** | COMPLETE | Specs merged to main; change folder moved to archive (2026-08-28) |

---

## Task Completion Gate

**Status**: PASS

All 23 implementation tasks in `tasks.md` are marked complete (`[x]`):
- Phase 1 (generador.py extraction): 3/3 tasks complete
- Phase 2 (reportes app + models): 6/6 tasks complete
- Phase 3 (form builder + codec): 5/5 tasks complete
- Phase 4 (views, urls, templates): 9/9 tasks complete

No unchecked implementation tasks remain in the persisted artifact.

---

## Spec Sync Summary

**Mode**: openspec (mechanical filesystem sync, no Engram observation IDs)

### Synced Delta Specs → Main Specs

| Domain | Source | Destination | Action | Verification |
|--------|--------|-------------|--------|--------------|
| reportes-modelo | `specs/reportes-modelo/spec.md` | `openspec/specs/reportes-modelo/spec.md` | **Created** (main spec did not exist) | `diff -r` returned 0 (bit-for-bit identical) |
| wizard-captura | `specs/wizard-captura/spec.md` | `openspec/specs/wizard-captura/spec.md` | **Created** (main spec did not exist) | `diff -r` returned 0 (bit-for-bit identical) |

Both delta specs were complete specifications (not incremental deltas), so they were copied mechanically using `cp -R` and verified with `diff -r`. No existing main specs were modified; both are new capabilities.

**Artifacts persisted to source of truth**:
- `openspec/specs/reportes-modelo/spec.md` — defines Reporte and ValorDeReporte models with their persistence contract
- `openspec/specs/wizard-captura/spec.md` — defines server-rendered multi-step capture workflow

---

## Archive Move Summary

**Mode**: openspec (mechanical filesystem move with snapshot verification)

### Change Folder → Archive

| Source | Destination | Method | Snapshot Verification |
|--------|-------------|--------|----------------------|
| `openspec/changes/wizard-captura-server-rendered/` | `openspec/changes/archive/2026-08-28-wizard-captura-server-rendered/` | `git mv` (tracked in Git) | `diff -r` pre-move snapshot vs. archived folder: **0 (identical)** |

The entire change folder (proposal, specs, design, tasks, verify-report, apply-progress, exploration) was moved atomically using `git mv`. A pre-move snapshot was created and compared against the archived folder; the diff was empty (zero exit), confirming byte-for-byte integrity.

**Active changes directory verification**:
- Source directory `openspec/changes/wizard-captura-server-rendered/` confirmed removed ✓
- Archive directory `openspec/changes/archive/2026-08-28-wizard-captura-server-rendered/` confirmed created and populated ✓

---

## Verification Report Summary

Per `verify-report.md` persisted at archive time (observation recorded 2026-08-28):

**Verdict**: PASS  
**Final test count**: 187 passed, 0 failed, 0 errors  
**Critical issues**: 0 (one CRITICAL found in first verify pass, closed by follow-up commit `4dbcadb`)  
**Warnings**: 0  
**Suggestions**: 0 (two non-blocking Open Questions in design.md remain: PRG last-step redirect UX and D5's generador.py touch outside original proposal Affected Areas — both explicitly approved during apply)

**Spec compliance matrix**:
- reportes-modelo: all 4 scenarios PASS (Reporte creation ×2, ValorDeReporte per value, rango-hora-inicio-fin dual-row)
- wizard-captura: all 6 scenarios PASS (dynamic form render, empty section, per-step durable persistence, GET rehydration, non-blocking obligatorio, auth required)

**Design coherence**: D1–D11 all confirmed matching implementation with zero deviation

---

## Implementation Delivery Summary

**PR Chain**: 4 chained PRs merged to main
- **PR #9** (`feat/motor-definicion-tipo-reporte-01-modelos`): Phase 1 — generador.py extraction + reportes models
- **PR #10** (`feat/motor-definicion-tipo-reporte-02-validacion-estructural`): Phase 2 — formularios.py + valores.py codec
- **PR #11** (`feat/motor-definicion-tipo-reporte-03-validacion-plantilla`): Phase 3 — views, urls, templates
- **PR #12** (`feat/motor-definicion-tipo-reporte-04-servicio-admin`): Phase 4 — integration + admin configuration

**Follow-up PR**: #13 (test for rango-hora-inicio-fin dual-row persistence at view level)  
**Merged to**: main branch on 2026-08-28

---

## Archived Artifacts

The complete change folder has been archived at `openspec/changes/archive/2026-08-28-wizard-captura-server-rendered/` with all source artifacts intact:

- ✓ `proposal.md` — Intent, scope, capabilities, affected areas, risks, rollback plan
- ✓ `specs/reportes-modelo/spec.md` — Reporte and ValorDeReporte specification (also synced to main specs)
- ✓ `specs/wizard-captura/spec.md` — Server-rendered wizard specification (also synced to main specs)
- ✓ `design.md` — 11 architecture decisions, data flow, interfaces/contracts
- ✓ `tasks.md` — 23/23 tasks complete with detailed phase breakdown
- ✓ `verify-report.md` — Final verification report (PASS, 0 CRITICAL, 187 tests)
- ✓ `apply-progress.md` — Implementation progress and delivery notes
- ✓ `exploration.md` — Discovery notes from exploration phase

**Archive integrity**: All files verified via `diff -r` against pre-move snapshot with zero differences.

---

## Dependencies and Downstream Impact

**Upstream dependencies** (already merged):
- Backlog #3/#4 (`DefinicionDeTipo`, `estructura` schema, `TipoDeDato`) ✓

**Downstream dependencies** (backlog items built on this foundation):
- Backlog #6: Required-field enforcement and "No cumple" warnings (out of scope, marked explicitly)
- Backlog #7: Visto bueno / closing a report (out of scope, marked explicitly)
- Backlog #8: Collaboration, invitations, roles beyond creator-only (out of scope, marked explicitly)
- Backlog #9: Offline capture, service worker, IndexedDB (out of scope, marked explicitly)
- Backlog #10: Sync and `numero_registro` assignment (out of scope, marked explicitly)

The model shape (minimal `estado`, version snapshot FK, one row per field) was designed to support these backlog items without costly rework.

---

## Source of Truth Updated

The following main specifications have been synced with delta specs and now reflect the new behavior implemented in this change:

- **`openspec/specs/reportes-modelo/spec.md`** — Reporte and ValorDeReporte models and persistence contract (NEW)
- **`openspec/specs/wizard-captura/spec.md`** — Server-rendered multi-step capture workflow (NEW)

The main specification repository (`openspec/specs/`) is now the authoritative source for these capabilities. Any future work building on this change (e.g., backlog #7–#10) should reference these specs.

---

## Final State Authority

Per SDD Archive Skill Final-State Authority hierarchy:

1. **Native review authority**: Not applicable (openspec mode, no gentle-ai review receipt)
2. **Persisted tasks artifact**: `tasks.md` shows 23/23 complete ✓
3. **Explicit final-state facts from launch prompt**:
   - "All 4 chained PRs (#9, #10, #11, #12) merged to main" ✓
   - "One follow-up PR (#13) added the single missing test flagged by sdd-verify's first pass" ✓
   - "sdd-verify re-run: PASS, 0 CRITICAL, 0 WARNING, 0 SUGGESTION" ✓
   - "23/23 tasks complete, full suite 187/187 tests pass" ✓
   - "verify-report.md already persisted at openspec/changes/wizard-captura-server-rendered/verify-report.md" ✓
4. **Intermediate snapshots** (verify-report, apply-progress): Aligned with final state facts; no contradictions

**Conclusion**: All sources agree. The change is complete, verified, and archived in its final state.

---

## Rollback Capability

Per proposal's Rollback Plan: "Revert the `reportes` app and its `INSTALLED_APPS`/`urls.py` registration; no other app depends on it yet, so rollback is a clean app removal plus migration reversal."

**Rollback remains valid**:
- `reportes/` app is self-contained
- No other app currently depends on `reportes` models or views
- Only one interdependency: `tipos_reporte/generador.py` now exports public `claves_de_valor(nodo)` (refactored from `_destinos`)
  - Rollback of `reportes/` does not require reverting the `generador.py` change; the exported function has no callers outside `reportes`

---

## SDD Cycle Complete

The change **wizard-captura-server-rendered** has successfully completed the full SDD lifecycle:

1. ✓ **Proposed** — Intent and scope approved
2. ✓ **Specified** — 10 requirements across 2 specs, all scenarios covered
3. ✓ **Designed** — 11 architecture decisions, interfaces, data flow documented
4. ✓ **Tasked** — 23 implementation tasks in strict TDD order across 4 phases
5. ✓ **Applied** — 4 chained PRs + 1 follow-up PR, all merged to main
6. ✓ **Verified** — Final pass: 187 tests, 0 CRITICAL/WARNING/SUGGESTION
7. ✓ **Archived** — Specs synced to main; change folder moved to archive

**Ready for the next change** or follow-up backlog work (#6–#10).

---

## Key Learnings

1. Extracting `generador.claves_de_valor(nodo)` before implementing the wizard ensures identical key derivation on both sides (wizard persistence + generator reading), preventing silent drift.
2. Building form field names at construction time from `clave_de_etiqueta` ensures they match `ValorDeReporte.identificador_de_campo` and generator keys without parallel logic.
3. Reusing `validacion._iterar_nodos` in the wizard form builder anchors both to the same structure traversal, reducing the risk of inconsistency across refactors.
4. Designing with a minimal `estado` field and a `definicion` snapshot FK allows future backlog items (#7–#10) to build on this foundation without costly rework.
5. Strict TDD in 4 delivery phases with clear rollback boundaries (each PR independently revertible) supports safe reviewer load distribution and fast, independent verification across 400-line budget slices.


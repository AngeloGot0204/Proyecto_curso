# Archive Report: Validación de datos del formulario

**Change Name**: validacion-datos-formulario  
**Archived Date**: 2026-08-29  
**Archive Location**: `openspec/changes/archive/2026-08-29-validacion-datos-formulario/`  
**Status**: COMPLETE AND VERIFIED

## Executive Summary

The "validación de datos del formulario" feature is fully implemented, verified, and closed. All 28 tasks are complete, the full test suite passes (203/203 tests), and delta specs have been merged into the main specification store. The change introduces server-side aggregate validation with a review screen (S-09) and client-side hora-range feedback, reusing existing obligatorio-detection logic to prevent drift. Two new capabilities (`validacion-reporte`) and one modified capability (`wizard-captura`) are now part of the source of truth.

## Final State at Archive

**Date of Archive**: 2026-08-29  
**Source of Truth**: All specs merged into `openspec/specs/`  
**Implementation Lineage**: 4 merged PRs (#14, #15, #16, #17) targeting main branch  

### Task Completion (Task Completion Gate)
- **Persisted Tasks Artifact**: `openspec/changes/archive/2026-08-29-validacion-datos-formulario/tasks.md`
- **Status**: All 28 implementation tasks marked complete (100%)
- **Phases Covered**:
  - Phase 1: Foundation (fixture setup) ✅
  - Phase 2: `validar_reporte` core (TDD) ✅ (9 tasks)
  - Phase 3: `formularios.py` companion field (TDD) ✅ (4 tasks)
  - Phase 4: S-09 review screen (TDD) ✅ (4 tasks)
  - Phase 5: Client-side JS layer (TDD) ✅ (3 tasks)
  - Phase 6: Regression ✅ (3 tasks)

### Verification State
**Source**: `openspec/changes/archive/2026-08-29-validacion-datos-formulario/verify-report.md` (persisted 2026-08-29)

- **Verdict**: PASS WITH WARNINGS
- **Test Results**: 203 passed, 0 failed (100% success rate)
- **Issues at Verification Time**:
  - CRITICAL: 0
  - WARNING: 1 (non-blocking) — No dedicated test directly asserts `ValorDeReporte` persistence for `{id}_observacion` field. Covered indirectly via generic form persistence + form-construction test. Low risk.
  - SUGGESTION: 1 (accepted design tradeoff) — JS behavioral scenarios (hora-range disable, No cumple reveal) have zero executed-runtime coverage; only rendered-attribute contract + manual review. Acceptable per project's lack of JS test runner.

**Final Status**: Both warning and suggestion are non-blocking and explicitly accepted in verify-report. Change is ready for archive.

### Spec Merge Summary

#### 1. New Capability: `validacion-reporte`

**Location Created**: `openspec/specs/validacion-reporte/spec.md`

**Requirements Added** (6 scenarios, all covered):
- **Aggregate validation function**: `validar_reporte(reporte)` returns `errores` (blocking) and `advertencias` (non-blocking), reusing `_validar_completitud` obligatorio logic.
- **Scenarios**: All obligatorio fields filled → empty errors; missing obligatorio → one error entry; obligatorio detection matches generator exactly; stray hora_fin<=hora_inicio → advertencia; "No cumple" without observación → advertencia; "No cumple" with observación → no advertencia.
- **Review screen (S-09)**: `/reportes/<reporte_id>/revision/` exposes error and warning lists, disables "Generar" when errors present.
- **Scope**: Server-side validation and review UX; generation trigger deferred to backlog #7.

#### 2. Modified Capability: `wizard-captura`

**Location**: `openspec/specs/wizard-captura/spec.md` (merged in place)

**Requirements Added** (6 scenarios):
1. **Client-side hora range feedback** (2 scenarios): Vanilla JS disables "Siguiente" when fin <= inicio; re-enables on correction.
2. **Server-side non-blocking hora range re-check** (1 scenario): Direct POST with invalid range still persists; no validation error.
3. **"No cumple" observación toggling** (2 scenarios): "No cumple" selection reveals required observación field; observación persists under `{id}_observacion` key.

**Requirements Modified** (1 requirement, 2 scenarios):
- **Non-blocking obligatorio marker** expanded to explicitly guarantee non-blocking behavior for hora-range and "No cumple" checks. Existing test `test_post_paso_sin_valor_obligatorio_no_bloquea` confirmed passing unmodified in intent.

**Preservation**: All existing 5 requirements (`One URL and dynamic form per section`, `Per-step durable persistence`, `GET rehydration from persisted rows`, `Authentication required`) remain unchanged.

### Mechanical Verification

**Spec Copy Operations**:
- `openspec/changes/archive/2026-08-29-validacion-datos-formulario/specs/validacion-reporte/spec.md` → `openspec/specs/validacion-reporte/spec.md` ✅ (diff: 0 lines difference)
- `openspec/changes/archive/2026-08-29-validacion-datos-formulario/specs/wizard-captura/spec.md` → `openspec/specs/wizard-captura/spec.md` ✅ (merged: 6 new scenarios + 1 modified requirement)

**Archive Move Operation**:
- Source: `openspec/changes/validacion-datos-formulario/`
- Destination: `openspec/changes/archive/2026-08-29-validacion-datos-formulario/` (git mv) ✅
- Verification: diff -r snapshot (pre-move) vs. archived folder = 0 differences ✅
- Source now absent from active changes: ✅

### Artifacts in Archive

All SDD artifacts preserved in the archive folder:
- `proposal.md` — intent, scope, approach, rollback plan ✅
- `design.md` — architectural decisions, module contracts ✅
- `exploration.md` — research and decision history ✅
- `tasks.md` — 28/28 tasks complete, work unit breakdown ✅
- `apply-progress.md` — implementation progress snapshot ✅
- `verify-report.md` — verification results and coverage analysis ✅
- `specs/validacion-reporte/spec.md` — new spec (scenarios and requirements) ✅
- `specs/wizard-captura/spec.md` — delta spec merged into main ✅
- `archive-report.md` — this file, final state at closure ✅

## Lineage and Traceability

### Implementation Delivery
- **PR Chain**: #14 (Models) → #15 (Structural Validation) → #16 (Template & Validation) → #17 (Admin Service)
- **Target Branch**: main (all 4 PRs merged)
- **Completion Date**: 2026-08-29

### Task Tracking
- **Framework**: SDD (Structured Design Delivery)
- **Phase**: sdd-archive (final closure)
- **Artifact Store**: openspec (filesystem-based spec store with version control)

## Rollback and Reversibility

Per proposal.md, all changes are additive or locally revertible:
- `validacion.py` (new module) — removable without affecting wizard-captura
- `revision.html` (new template) — removable without affecting existing views
- `paso.html`/`paso` POST edits (template/view-local) — revertible via `git revert`
- `paso.js` (new script) — removable client-side
- No schema migrations — observación reuses existing `ValorDeReporte` key pattern

**Rollback Scope**: If S-09 or validation logic misbehaves, the route, template, and module can be removed without affecting the wizard-captura pipeline (D8 non-blocking contract remains intact).

## Acceptance Criteria Met

From proposal.md "Success Criteria":
1. ✅ Siguiente is disabled client-side when hora_fin <= hora_inicio, re-validated server-side without blocking POST.
2. ✅ "No cumple" selection reveals required observación field and persists it via existing key-pair pattern.
3. ✅ `validar_reporte` returns correct errores/advertencias, reusing generator obligatorio logic (no drift confirmed by anti-drift test).
4. ✅ S-09 view lists errores (linked to paso) and advertencias; Generar disabled iff errores non-empty.
5. ✅ `test_post_paso_sin_valor_obligatorio_no_bloquea` passes unmodified in intent (step POST remains non-blocking).

## Known Limitations and Future Work

All deferred items remain in backlog (documented in both specs' Out of Scope):
- **Backlog #7**: Actual `.xlsx` generation trigger ("visto bueno") — "Generar" button is disabled-only in this change.
- **Backlog #9**: Offline S-09 (stays server-rendered).
- **Backlog #11**: Unsupported adjunto format blocking (no adjuntos model exists yet).

Warning items from verify-report.md remain accepted non-blocking:
- **Indirect test coverage** for `{id}_observacion` persistence (covered via generic loop + form-construction test).
- **No JS runtime coverage** for hora-range and "No cumple" toggles (design tradeoff; no JS test harness in project).

## Archive Status

- **Change Folder**: Moved to `openspec/changes/archive/2026-08-29-validacion-datos-formulario/`
- **Specs Merged**: Both delta specs synced into `openspec/specs/`
- **SDD Cycle**: CLOSED
- **Next Action**: none — change is complete and can be deployed or referenced for future work.

---

**Archived by**: sdd-archive phase executor  
**Timestamp**: 2026-08-29T00:49:00Z  
**Artifact Store Mode**: openspec (filesystem-based)

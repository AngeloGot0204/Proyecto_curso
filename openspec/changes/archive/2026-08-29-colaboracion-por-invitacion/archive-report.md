# Archive Report: colaboracion-por-invitacion

**Change**: colaboracion-por-invitacion  
**Archived to**: `openspec/changes/archive/2026-08-29-colaboracion-por-invitacion/`  
**Archive Date**: 2026-08-29  
**Mode**: openspec/hybrid  

## Executive Summary

The "colaboracion-por-invitacion" (collaboration by invitation) change has been completed, fully verified, and archived. All 4 chained PRs (#21–#24) merged to main. Full test suite passes (250/250). Verification report confirms PASS with zero CRITICAL, WARNING, or SUGGESTION issues. All implementation tasks marked complete. Delta specs successfully merged into main specs; new `colaboracion-reporte` capability added; `wizard-captura`, `generacion-documento`, and `cierre-reporte` specs updated to reflect participant access widening.

## Artifacts

### Change Folder Contents (Archived)
- `proposal.md` — Initial scope and approach for collaboration feature
- `specs/` — Delta specifications for 4 capabilities:
  - `colaboracion-reporte/spec.md` — New capability defining ParticipacionEnReporte model, CambioDeValor audit trail with FIFO-30 retention, invite action, and participants/history view
  - `wizard-captura/spec.md` (delta) — Participant access required, value writes recorded to audit trail
  - `generacion-documento/spec.md` (delta) — Narrowed from any-authenticated-user to creator-or-invited-participant
  - `cierre-reporte/spec.md` (delta) — Creator-only closure unchanged; revision view access widened to participants
- `design.md` — Design decisions (D1–D6): fetch-then-check-then-404 access pattern, no-op guard, FIFO-30 implementation, invite/cerrar carve-outs, participantes view template
- `tasks.md` — 5 phases, 99 tasks, all marked complete [x]
  - Phase 1: Models + permission predicate (8 tasks)
  - Phase 2: guardar_valor refactor + FIFO-30 (13 tasks)
  - Phase 3: Widen paso/revision, narrow generar (17 tasks)
  - Phase 4: Invite action + participantes view (16 tasks)
  - Phase 5: Full suite verification (2 tasks)
- `exploration.md` — Exploration findings from sdd-explore phase
- `apply-progress.md` — Apply phase progress and commit summary
- `verify-report.md` — Verification results (PASS, 0 CRITICAL/WARNING/SUGGESTION, 250 tests)

### Main Specs Updated
1. **New**: `openspec/specs/colaboracion-reporte/spec.md`
   - ParticipacionEnReporte Model (2 scenarios)
   - CambioDeValor Model and FIFO-30 Retention (5 scenarios)
   - Creator-Only Invite Action (4 scenarios)
   - Participants and History View (2 scenarios)

2. **Modified**: `openspec/specs/wizard-captura/spec.md`
   - ADDED: "Participant Access Required" requirement (2 scenarios)
   - ADDED: "Value Writes Recorded to CambioDeValor" requirement (1 scenario)
   - MODIFIED: "Authentication required" requirement (cross-reference to participant access)

3. **Modified**: `openspec/specs/generacion-documento/spec.md`
   - REPLACED: "Any Authenticated User May Generate" → "Creator or Invited Participant May Generate"
   - Updated scenarios: creator success, invited participant success, non-participant denial

4. **Modified**: `openspec/specs/cierre-reporte/spec.md`
   - ADDED: "Cerrar Reporte Access Is Unaffected By Invitations" requirement (1 scenario)
   - ADDED: "Revision View Access Widens With Invitations" requirement (2 scenarios)

## Verification Summary

Per `verify-report.md` (Engram observation #81):

- **Runtime Evidence**: Full project suite `pytest reportes/` — **250 passed** (independently reproduced)
- **Spec Compliance**: All 4 capability specs' requirements and scenarios verified:
  - colaboracion-reporte: 8/8 scenarios PASS
  - wizard-captura delta: 3/3 scenarios PASS
  - generacion-documento delta: 3/3 scenarios PASS
  - cierre-reporte delta: 3/3 scenarios PASS
- **Design Decisions**: All 6 design decisions (D1–D6) correctly implemented and tested
- **Issues**: CRITICAL: 0, WARNING: 0, SUGGESTION: 0
- **Status**: PASS

## Task Completion

All 5 phases complete. Implementation tasks: 99/99 marked [x].

- Phase 1 (Models + permisos.py): ✅ 8 tasks
- Phase 2 (guardar_valor + FIFO-30): ✅ 13 tasks
- Phase 3 (Widen paso/revision, narrow generar): ✅ 17 tasks
- Phase 4 (Invite + participantes): ✅ 16 tasks
- Phase 5 (Full suite): ✅ 2 tasks

## Delivery Summary

**PRs Merged to Main**:
- PR #21: `feat(reportes): add ParticipacionEnReporte/CambioDeValor models and permisos helper`
- PR #22: `feat(reportes): guardar_valor refactor with CambioDeValor audit trail and FIFO-30 trim`
- PR #23: `feat(reportes): widen paso/revision to participants, narrow generar via _reporte_accesible`
- PR #24: `feat(reportes): invite action, participantes view, and participant access gates`

**Final State**:
- All 4 chained PRs merged to main (complete lineage: main ← #21 ← #22 ← #23 ← #24)
- Working tree clean (no uncommitted drift)
- Full test suite: 250/250 PASS
- `makemigrations --check --dry-run`: "No changes detected" (migration 0004 complete)
- Verification gate: PASS (zero CRITICAL/WARNING/SUGGESTION)

## Merging Notes

**Merge Strategy**: Delta specs merged into main specs mechanically via shell `cp` for new capabilities and explicit requirement-by-requirement replacement for modifications. All requirements outside the delta were preserved; no destructive changes.

**Changes Made**:
1. `colaboracion-reporte`: Full new spec copied (not a delta)
2. `wizard-captura`: 2 new requirements prepended; 1 existing requirement cross-referenced
3. `generacion-documento`: "Any Authenticated User" requirement replaced with narrower "Creator or Invited Participant" requirement
4. `cierre-reporte`: 2 new requirements appended

No removed or renamed requirements. All modifications preserve backward compatibility at the spec level (implementation was gated correctly at apply time).

## Archive Structure

```
openspec/changes/archive/2026-08-29-colaboracion-por-invitacion/
├── proposal.md
├── design.md
├── exploration.md
├── apply-progress.md
├── tasks.md
├── verify-report.md
├── archive-report.md (this file)
└── specs/
    ├── colaboracion-reporte/spec.md
    ├── wizard-captura/spec.md
    ├── generacion-documento/spec.md
    └── cierre-reporte/spec.md
```

## Source of Truth Updated

The following main specs now reflect the final merged state:
- `openspec/specs/colaboracion-reporte/spec.md` (new)
- `openspec/specs/wizard-captura/spec.md`
- `openspec/specs/generacion-documento/spec.md`
- `openspec/specs/cierre-reporte/spec.md`

## SDD Cycle Status

✅ **Complete**: The change has been fully planned (proposal), specified (4 capability specs), designed (6 design decisions), tasked (99 tasks), applied (4 chained PRs, 250 tests), verified (PASS, 0 issues), and archived (specs merged, folder moved, audit trail established).

Ready for the next change.

## Engram Artifact IDs

- verify-report: Engram #81 (sdd/colaboracion-por-invitacion/verify-report)
- archive-report: (persisted as this observation, topic: sdd/colaboracion-por-invitacion/archive-report)

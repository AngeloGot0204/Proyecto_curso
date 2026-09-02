# Apply Progress: Report Type Definition Engine (backlog #3)

> Engram: `sdd/motor-definicion-tipo-reporte/apply-progress` (observation #76)
> Full text (all 4 slices, TDD Cycle Evidence tables, Work Unit Evidence,
> file-by-file line counts) lives in Engram observation #76. This file is a
> condensed index for filesystem archival.

## Branch / PR chain (stacked-to-main)

| Slice | Branch | Base | Commit |
|---|---|---|---|
| 1 | feat/motor-definicion-tipo-reporte-01-modelos | main | f4c89fb |
| 2 | feat/motor-definicion-tipo-reporte-02-validacion-estructural | Slice 1 | 2a724a7 |
| 3 | feat/motor-definicion-tipo-reporte-03-validacion-plantilla | Slice 2 | e56532d |
| 4 | feat/motor-definicion-tipo-reporte-04-servicio-admin | Slice 3 | c9d5328 |

No push performed (project convention: push is user-authorized only).

## Grand totals across all 4 slices (authored lines)

| Slice | Forecast | Actual | Overrun |
|---|---|---|---|
| 1 (models) | ~330 | 537 | +63% |
| 2 (structural validation R1-R4) | ~290 | 503 | +73% |
| 3 (template validation R5-R6 + security) | ~200 | 421 | +111% |
| 4 (activation service + admin) | ~262-390 | 663 | +70-150% |
| Total | ~1082-1210 | ~2124 | ~+90-96% |

Explicitly accepted by the user via the 4-slice stacked-PR split before
apply started (design's Review Workload Forecast flagged 400-line-budget
risk as High). Re-evaluated by sdd-verify - see 07-verify.md.

## Bugfix discovered and fixed during Slice 4

`DefinicionDeTipo.save()`'s immutability guard (design D3, Slice 1) checked
`self.estado != Estado.BORRADOR` instead of the row's PREVIOUS
(`anterior.estado`) - the exact wording of the design's own pseudocode,
copied literally in Slice 1. Consequence: the legitimate borrador->activa
transition itself (assigning `version` for the first time) tripped the
guard. Fixed by gating the CONGELADOS-diff check on `anterior.estado !=
BORRADOR` instead of `self.estado != BORRADOR`. Regression test added.
Independently re-derived by sdd-verify via mutation testing (07-verify.md) -
confirmed the original bug reproduces exactly as described and 6 tests
across 2 files fail without the fix.

## Deviations from design (13 total, see Engram #76 for full list)

Most relevant to verify: (10) the save()-guard bugfix above; (11)
`analizar_yaml_seguro` wiring collapsed into one `ModelForm.clean()` rather
than split `ModelForm.clean()` + `DefinicionDeTipo.clean()`; (13)
`TipoDeReporteAdmin` got its own undocumented `desactivar` action.

## Status (as reported by apply)

4/4 slices complete. 103/103 project tests green (86 prior + 17 new).
Ready for sdd-verify over the complete change - not per-slice.

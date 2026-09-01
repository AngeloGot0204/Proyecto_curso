# Tasks: Report Type Definition Engine (backlog #3)

> Engram: `sdd/motor-definicion-tipo-reporte/tasks` (observation #75)
> Full step-by-step task text lives in Engram observation #75 and its
> feeding apply-progress observation #76 (also archived as
> 06-apply-progress.md in this folder). This file is a condensed index.

## Delivery decision

Design's own Review Workload Forecast (~1082 authored lines, 2.7x the
400-line budget) triggered `delivery_strategy: ask-on-risk`. The user
explicitly chose **stacked-to-main** (each branch built on the previous
one's tip, no branch targeting `main` directly except the first), which
supersedes the design/tasks' own "Feature Branch Chain" recommendation
(each branch targeting `main` independently).

## Phase 1 (Slice 1): RED + GREEN - scaffold and models
- [x] 1.1-1.8 - app scaffold, TipoDeReporte/DefinicionDeTipo models, the
  four DB constraints, immutability + delete guards, 0001_initial,
  settings/deps (PyYAML, openpyxl, Pillow, MEDIA_ROOT/MEDIA_URL).
  Branch `feat/motor-definicion-tipo-reporte-01-modelos`, commit `f4c89fb`.

## Phase 2 (Slice 2): RED + GREEN - structural validation rules (R1-R4)
- [x] 2.1-2.5 - `validacion.py` R1 (required fields), R2 (known type),
  R3 (cell notation), R4 (collisions), `ProblemaDeDefinicion`/
  `ResultadoDeValidacion`, accumulation.
  Branch `feat/motor-definicion-tipo-reporte-02-validacion-estructural`,
  commit `2a724a7`.

## Phase 3 (Slice 3): RED + GREEN - template validation rules (R5-R6) + security
- [x] 3.1-3.7 - R5 (template/sheet readable), R6 (merge anchor), the
  `plantilla_xlsx` fixture, `analizar_yaml_seguro` (yaml.safe_load-only),
  the two Threat Matrix REDs (malicious YAML tag rejected, corrupt .xlsx
  produces exactly one `plantilla-ilegible` problem, never a crash).
  Branch `feat/motor-definicion-tipo-reporte-03-validacion-plantilla`,
  commit `e56532d`.

## Phase 4 (Slice 4): RED + GREEN - activation service and admin
- [x] 4.1-4.7 - `servicios.py` (`activar_definicion`, `desactivar_tipo`),
  `admin.py` (`DefinicionDeTipoForm`, both ModelAdmins, layered delete
  guards, activar/desactivar actions). 17 new tests (7 activation + 9
  admin + 1 model regression). Branch
  `feat/motor-definicion-tipo-reporte-04-servicio-admin`, commit `c9d5328`.
- Bugfix discovered and fixed in this slice: `DefinicionDeTipo.save()`'s
  immutability guard checked `self.estado` instead of the row's PREVIOUS
  (`anterior.estado`), which blocked the legitimate first
  borrador->activa transition. Fixed; regression test added. Re-derived
  and confirmed by sdd-verify (see 07-verify.md, mutation-testing section).

## STATUS
All 4 phases complete per the tasks/apply-progress artifacts. 103/103
project tests green at the time tasks was last updated (86 prior + 17 new
this slice). sdd-verify (07-verify.md) independently re-ran the full suite,
re-derived RED genuineness for a representative sample via mutation
testing, and found one CRITICAL functional gap not caught by the existing
103 tests - see 07-verify.md before treating this change as ready to
archive as-is.

# Apply Progress: Generador de Excel desde plantilla (backlog #4)

**Mode**: Strict TDD
**This run (PR 2 of 3)**: Phase 3 (Cell Writing and Sheet Export) only — tasks 3.1-3.9. Phase 4
(logo swap) remains explicitly OUT of scope and untouched. PR 1 (Phase 1+2) is merged to `main`;
its record below is copied forward for continuity, not re-applied.

## Completed Tasks (cumulative)

### Phase 1: Foundation — Exceptions and Test Fixtures (PR 1, merged)
- [x] 1.1 RED: failing test for `ProblemaDeGeneracion` importability/subclass
- [x] 1.2 GREEN: `tipos_reporte/generador.py` created with `ProblemaDeGeneracion`,
      `PlantillaIlegible`, `ValoresIncompletos`
- [x] 1.3 RED: `ValoresIncompletos(["b","a"])` sorting/message test
- [x] 1.4 GREEN: confirmed by 1.2/1.3's passing test
- [x] 1.5 `plantilla_xlsx` fixture extended with `hojas_extra=()` and `imagen=None`
- [x] 1.6 `imagen_png` fixture added
- [x] 1.7 `valores_completos` fixture helper added (matches `definicion_valida`'s ids)

### Phase 2: Template Loading and Completeness Validation (PR 1, merged)
- [x] 2.1 RED: "Template loads successfully" test
- [x] 2.2 RED: "Template file cannot be read" tests (invalid bytes + missing file)
- [x] 2.3 GREEN: `generar_reporte` steps 1-3 (open/load/select sheet, `PlantillaIlegible` wrapping)
- [x] 2.4 RED: `_destinos(nodo)` unit tests (scalar + range)
- [x] 2.5 GREEN: `_destinos` implemented (design D1, reuses `_claves_de_celda_requeridas`)
- [x] 2.6 RED: required simple value missing test
- [x] 2.7 RED: one side of required range missing test
- [x] 2.8 RED: multiple missing ids reported together test
- [x] 2.9 RED: non-obligatorio node with absent key does NOT raise
- [x] 2.10 GREEN: `_validar_completitud` implemented and wired into `generar_reporte` (design
      Sequence step 4; D2 membership test; D3 `obligatorio` requiredness)

### Phase 3: Cell Writing and Sheet Export (PR 2, this run)
- [x] 3.1 RED: "Simple field value is written by id" scenario test (`turno`/`B2`/`"Mañana"`)
- [x] 3.2 RED: "Range field values are written from two independent keys" scenario test
      (`descanso_inicio`→`C3`, `descanso_fin`→`C4`)
- [x] 3.3 RED: falsy-value test — `False`/`0` via round trip; `""` via a unit-level companion
      test against `_escribir_valores` directly (see Deviations from Design — openpyxl/XLSX
      round-trip limitation, not an implementation gap)
- [x] 3.4 GREEN: cell-writing pass — `_escribir_valores(hoja, estructura, valores)` walks all
      nodes via `_iterar_nodos`, uses `_destinos(nodo)` for every present key in `valores`
      (membership test, D2/D3), writes `hoja[coordenada] = valores[clave]`
- [x] 3.5 RED: "Only the declared sheet is exported" test using `hojas_extra=("Otra",)`
- [x] 3.6 RED: "Untouched sheet content remains byte-identical in structure" test — merged
      ranges outside anchor cells preserved
- [x] 3.7 GREEN: `_exportar_solo_hoja_declarada(libro, nombre_hoja)` — deletes every sheet
      `!= estructura["hoja"]`, then `libro.active = 0` (design D5)
- [x] 3.8 RED: "Successful generation returns readable bytes" test — `.tell() == 0` and
      re-openable via `load_workbook`
- [x] 3.9 GREEN: `libro.save(buffer); buffer.seek(0); return buffer` wired as the final step,
      after cell writing and sheet-only export (design Sequence steps 6-8)

## Remaining Tasks (deferred to PR 3)

### Phase 4: Logo Swap (PR 3)
- [ ] 4.1-4.5 — all pending (logo present/absent/template-has-no-image scenarios, `_images`
      swap implementation, wiring into main sequence)

### Phase 5: Integration and Cleanup
- [ ] 5.1-5.4 — pending until Phase 4 lands (full-suite spec-coverage check, docstring review,
      threat-matrix confirmation)

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-2.10 | see PR 1 record | — | — | ✅ | ✅ | ✅ | ➖ None needed |
| 3.1 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written, failed with `hoja["B2"].value is None` before 3.4 | ✅ Passed after 3.4 | ➖ Single scenario | ➖ None needed |
| 3.2 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written, failed (cells unwritten) before 3.4 | ✅ Passed after 3.4 | ✅ 2 cells (C3, C4) | ➖ None needed |
| 3.3 | `tipos_reporte/tests/test_generador.py` | Unit (DB) + Unit (pure) | ✅ 19/19 | ✅ Written; `False`/`0` failed before 3.4; `""` unit test written after discovering the round-trip limitation | ✅ Passed after 3.4 | ✅ 3 falsy values (`False`, `0`, `""`) | ➖ None needed |
| 3.4 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 19/19 | — | ✅ Passed (3.1-3.3) | ➖ N/A | ➖ None needed |
| 3.5 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written, failed with `sheetnames == ['REPORTE', 'Otra']` before 3.7 | ✅ Passed after 3.7 | ➖ Single scenario | ➖ None needed |
| 3.6 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written; passed immediately (no prior code touched merges) — kept as a regression guard for D5 | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 3.7 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 19/19 | — | ✅ Passed (3.5-3.6) | ➖ N/A | ➖ None needed |
| 3.8 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written; passed immediately (step 8 already existed from PR 1) — kept as an explicit spec-scenario regression guard | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 3.9 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 19/19 | — | ✅ Confirmed by 3.8 (step reordered to run after 3.4/3.7, not re-implemented) | ➖ N/A | ➖ None needed |

### Test Summary (this run)
- **Total tests added this run**: 8 (`tipos_reporte/tests/test_generador.py`) — 6 new scenario
  tests (3.1, 3.2, 3.3×2 parametrized cases, 3.5, 3.6, 3.8) + 1 unit-level companion test for the
  `""` falsy case
- **Total tests passing (module)**: 19/19 (11 from PR 1 + 8 new)
- **Total tests passing (full `tipos_reporte/tests/` suite)**: 99/99 (91 from PR 1 baseline + 8
  new — 0 regressions), run once cleanly (a prior parallel/racing run against the same
  `--reuse-db` Postgres DB produced spurious `IntegrityError`s from two pytest processes writing
  concurrently — not a real regression; the clean sequential re-run is authoritative)
- **Layers used**: Unit (`@pytest.mark.django_db` tests exercising `generar_reporte` against a
  real in-memory `openpyxl` workbook round trip) + one pure unit test directly against
  `_escribir_valores` (no DB, no round trip)
- **Approval tests**: None — no refactoring tasks, only additive functions
- **Pure functions created this run**: `_escribir_valores`, `_exportar_solo_hoja_declarada`
  (both pure over `hoja`/`estructura`/`valores`/`libro`, no I/O beyond in-memory openpyxl object
  mutation)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest tipos_reporte/tests/test_generador.py -k "escribe or hoja or export or exitosa or rango or byte" -q` → `11 passed, 8 deselected` |
| Runtime harness command/scenario and exact result | `pytest tipos_reporte/tests/ -q` (full app suite, includes DB-backed `@pytest.mark.django_db` tests using real SQLite/Postgres via `--reuse-db` and real in-memory `openpyxl` workbooks) → `99 passed` (0 regressions vs. the 91-test PR-1 baseline) |
| Rollback boundary | Revert the write-pass/export-pass code inside `tipos_reporte/generador.py` (the `_escribir_valores`/`_exportar_solo_hoja_declarada` functions and their call sites) and the 8 new tests appended to `tipos_reporte/tests/test_generador.py`. PR 1's exceptions, fixtures, template loading and completeness validation remain intact and untouched — zero blast radius outside this PR's slice. |

## Files Changed (this run)

| File | Action | What Was Done |
|------|--------|----------------|
| `tipos_reporte/generador.py` | Modified | Added `_escribir_valores` (cell-writing pass, design Sequence step 6) and `_exportar_solo_hoja_declarada` (sheet-only export, design D5, step 7); wired both into `generar_reporte` between completeness validation and the final `BytesIO` save; updated module docstring |
| `tipos_reporte/tests/test_generador.py` | Modified | Added 8 tests covering Phase 3 scenarios: scalar write, range write, falsy-value handling (`False`/`0` round-trip + `""` unit-level), sheet-only export, merged-range preservation, and final-bytes readability |
| `openspec/changes/generador-excel-plantilla/tasks.md` | Modified | Marked tasks 3.1-3.9 `[x]` |

## Deviations from Design

None from `design.md`'s architecture decisions (D1-D5, Sequence steps 6-8) — the implementation
matches `_destinos`/`_iterar_nodos` reuse, membership-test semantics, and the delete-in-place
sheet export exactly as specified.

One test-design correction discovered during RED, not a design deviation: task 3.3's spec text
lists `False`/`0`/`""` as the falsy values to prove are written verbatim. `""` cannot be asserted
via a save/reload round trip because openpyxl/XLSX serializes an empty-string cell identically to
a never-written (blank) cell — confirmed independently (`ws['B2'] = ''` → save → reload → `None`).
This is an XLSX/openpyxl format limitation, not a defect in `_escribir_valores`'s membership-test
logic (`clave in valores`, which does correctly assign `""` to the in-memory cell before save).
The `""` case is therefore asserted at the unit level directly against `_escribir_valores`'s
in-memory effect on the `openpyxl` worksheet, before serialization — `False`/`0` keep their
original save/reload round-trip assertion since those two values DO survive XLSX serialization
intact.

## Issues Found

None.

## Workload / PR Boundary

- Mode: stacked-to-main chain, PR 2 of 3 (as scoped by the orchestrator's launch prompt)
- Current work unit: Unit 2 — "`_destinos` helper + scalar/range cell-writing pass + sheet-only
  export" (per tasks.md's Suggested Work Units table)
- Boundary: starts from PR 1's merged state (template loading + completeness validation, no cell
  writes or export logic yet); ends with cell writing (scalar + range) and sheet-only export
  fully implemented and tested; explicitly excludes logo swap (PR 3)
- Estimated review budget impact: ~120 authored changed lines (`generador.py` +50/-9,
  `test_generador.py` +215) — within the forecasted PR 2 slice size; PR 3 remains separately
  scoped per the tasks.md forecast

## Status

30/34 tasks complete (Phase 1: 7/7, Phase 2: 10/10, Phase 3: 9/9, Phase 4: 0/5, Phase 5: 0/4
gated on Phase 4). Ready for next batch (PR 3: Phase 4 — logo swap).

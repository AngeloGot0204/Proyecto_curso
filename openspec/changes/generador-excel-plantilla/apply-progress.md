# Apply Progress: Generador de Excel desde plantilla (backlog #4)

**Mode**: Strict TDD
**This run**: PR 1 of 3 — Phase 1 (Foundation) + Phase 2 (Template Loading and Completeness
Validation) only. Phase 3 (cell writing/sheet export) and Phase 4 (logo swap) are explicitly
OUT of scope for this run and remain untouched.

## Completed Tasks (this run)

### Phase 1: Foundation — Exceptions and Test Fixtures
- [x] 1.1 RED: failing test for `ProblemaDeGeneracion` importability/subclass
- [x] 1.2 GREEN: `tipos_reporte/generador.py` created with `ProblemaDeGeneracion`,
      `PlantillaIlegible`, `ValoresIncompletos`
- [x] 1.3 RED: `ValoresIncompletos(["b","a"])` sorting/message test
- [x] 1.4 GREEN: confirmed by 1.2/1.3's passing test
- [x] 1.5 `plantilla_xlsx` fixture extended with `hojas_extra=()` and `imagen=None`
- [x] 1.6 `imagen_png` fixture added
- [x] 1.7 `valores_completos` fixture helper added (matches `definicion_valida`'s ids)

### Phase 2: Template Loading and Completeness Validation
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

## Remaining Tasks (deferred to PR 2 / PR 3)

### Phase 3: Cell Writing and Sheet Export (PR 2)
- [ ] 3.1-3.9 — all pending (scalar/range cell writes, falsy-value handling, sheet-only export,
      merged-range preservation, final `BytesIO` return)

### Phase 4: Logo Swap (PR 3)
- [ ] 4.1-4.5 — all pending (logo present/absent/template-has-no-image scenarios, `_images`
      swap implementation, wiring into main sequence)

### Phase 5: Integration and Cleanup
- [ ] 5.1-5.4 — pending until Phase 3/4 land (full-suite spec-coverage check, docstring review,
      threat-matrix confirmation)

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tipos_reporte/tests/test_generador.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ➖ Single (structural) | ➖ None needed |
| 1.2 | `tipos_reporte/generador.py` | Unit | N/A (new) | — | ✅ Passed (1.1) | ➖ N/A | ➖ None needed |
| 1.3 | `tipos_reporte/tests/test_generador.py` | Unit | ✅ 1/1 (1.1) | ✅ Written | ✅ Passed | ✅ 2 ids (a, b) | ➖ None needed |
| 1.4 | — | — | — | — | ✅ Confirmed by 1.3 | ➖ N/A | ➖ N/A |
| 1.5/1.6/1.7 | `tipos_reporte/tests/conftest.py` | Fixture infra | ✅ 82/82 (full pre-existing suite) | ➖ N/A (fixture infra, exercised by Phase 2 RED tests) | ✅ Passed | ➖ N/A | ➖ None needed |
| 2.1 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 5/5 | ✅ Written | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 2.2 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 5/5 | ✅ Written | ✅ Passed | ✅ 2 cases (invalid bytes, missing file) | ➖ None needed |
| 2.3 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 5/5 | — | ✅ Passed (2.1/2.2) | ➖ N/A | ➖ None needed |
| 2.4 | `tipos_reporte/tests/test_generador.py` | Unit | ✅ 5/5 | ✅ Written | ✅ Passed | ✅ 2 cases (scalar, range) | ➖ None needed |
| 2.5 | `tipos_reporte/generador.py` | Unit | ✅ 5/5 | — | ✅ Passed (2.4) | ➖ N/A | ➖ None needed |
| 2.6 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 7/7 | ✅ Written | ✅ Passed | ➖ (covered w/ 2.7-2.9) | ➖ None needed |
| 2.7 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 7/7 | ✅ Written | ✅ Passed | ✅ range-partial case | ➖ None needed |
| 2.8 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 7/7 | ✅ Written | ✅ Passed | ✅ multi-id accumulation case | ➖ None needed |
| 2.9 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 7/7 | ✅ Written | ✅ Passed | ✅ non-obligatorio negative case | ➖ None needed |
| 2.10 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 7/7 | — | ✅ Passed (2.6-2.9) | ➖ N/A | ➖ None needed |

### Test Summary
- **Total tests written this run**: 11 (`tipos_reporte/tests/test_generador.py`)
- **Total tests passing (module)**: 11/11
- **Total tests passing (full `tipos_reporte/tests/` suite)**: 91/91 (82 pre-existing + 9 new
  functions, some covering 2 scenarios each — see file for exact count)
- **Layers used**: Unit (11) — pure-function unit tests (`_destinos`, `ValoresIncompletos`) plus
  `@pytest.mark.django_db` unit tests exercising `generar_reporte` against a real in-memory
  `openpyxl` workbook (no HTTP/view layer involved)
- **Approval tests**: None — no refactoring tasks, only additive new module
- **Pure functions created**: `_destinos`, `_validar_completitud` (both pure over
  `estructura`/`valores` dicts, no I/O)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest tipos_reporte/tests/test_generador.py -q` → `11 passed` |
| Runtime harness command/scenario and exact result | `pytest tipos_reporte/tests/ -q` (full app suite, includes DB-backed `@pytest.mark.django_db` tests using real SQLite via `--reuse-db` and real in-memory `openpyxl` workbooks) → `91 passed` (0 regressions vs. the 82-test baseline) |
| Rollback boundary | Revert `tipos_reporte/tests/conftest.py`'s fixture diff (47 insertions/4 deletions) and delete `tipos_reporte/generador.py` and `tipos_reporte/tests/test_generador.py`. No other module imports `generador.py` yet — zero blast radius outside this PR. |

## Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `tipos_reporte/generador.py` | Created | `ProblemaDeGeneracion`, `PlantillaIlegible`, `ValoresIncompletos`; `_SUFIJO_POR_CLAVE`, `_destinos`; `_validar_completitud`; `generar_reporte` steps 1-4 (load template, select sheet, completeness validation) |
| `tipos_reporte/tests/test_generador.py` | Created | 11 tests covering Phase 1 (exceptions) and Phase 2 (template load, `_destinos`, completeness validation) scenarios |
| `tipos_reporte/tests/conftest.py` | Modified | `plantilla_xlsx` gained `hojas_extra=()`/`imagen=None`; new `imagen_png` fixture; new `valores_completos` fixture |
| `openspec/changes/generador-excel-plantilla/tasks.md` | Modified | Marked tasks 1.1-1.7 and 2.1-2.10 `[x]` |

## Deviations from Design

None — implementation matches design (D1-D3, Sequence steps 1-4). Note: `generar_reporte`'s
`buffer = BytesIO(); libro.save(buffer); buffer.seek(0); return buffer` (design's Sequence step
8) currently runs immediately after step 4 (completeness validation) because steps 5-7 (logo
swap, cell writing, sheet-only export) are not yet implemented in this PR slice — this is
intentional and will move to its correct position after step 6 lands in PR 2/PR 3, not a design
deviation.

## Issues Found

None.

## Workload / PR Boundary

- Mode: stacked-to-main chain, PR 1 of 3 (as scoped by the orchestrator's launch prompt)
- Current work unit: Unit 1 — "Exceptions + fixture extension + template-load/completeness RED→GREEN tests"
- Boundary: starts from an empty `tipos_reporte/generador.py` (module did not exist), ends with
  template loading + completeness validation fully implemented and tested; explicitly excludes
  cell writing, sheet export, and logo swap (PR 2/PR 3)
- Estimated review budget impact: ~483 authored changed lines (`generador.py` 145,
  `test_generador.py` 287, `conftest.py` diff 51) — within the forecasted PR 1 slice size; PR 2
  and PR 3 remain separately scoped per the tasks.md forecast

## Status

21/34 tasks complete (Phase 1: 7/7, Phase 2: 10/10, Phase 3: 0/9, Phase 4: 0/5, Phase 5: 0/4
gated on Phase 3/4). Ready for next batch (PR 2: Phase 3 — cell writing and sheet export).

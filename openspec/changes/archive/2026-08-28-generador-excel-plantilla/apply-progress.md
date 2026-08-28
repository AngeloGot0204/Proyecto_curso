# Apply Progress: Generador de Excel desde plantilla (backlog #4)

**Mode**: Strict TDD
**This run (PR 3 of 3, FINAL)**: Phase 4 (logo swap) and Phase 5
(integration/cleanup) — tasks 4.1-4.5 and 5.1-5.4. PR 1 (Phase 1+2) and PR 2
(Phase 3) are merged to `main`; their records below are copied forward for
continuity, not re-applied. This completes ALL tasks in `tasks.md` — the
change is fully implemented.

## Completed Tasks (cumulative — ALL 34/34)

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

### Phase 3: Cell Writing and Sheet Export (PR 2, merged)
- [x] 3.1 RED: "Simple field value is written by id" scenario test (`turno`/`B2`/`"Mañana"`)
- [x] 3.2 RED: "Range field values are written from two independent keys" scenario test
      (`descanso_inicio`→`C3`, `descanso_fin`→`C4`)
- [x] 3.3 RED: falsy-value test — `False`/`0` via round trip; `""` via a unit-level companion
      test against `_escribir_valores` directly (see PR 2's Deviations from Design)
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

### Phase 4: Logo Swap (PR 3, this run)
- [x] 4.1 RED: "Logo is present on the tipo" test — 10x10 template image, distinct 20x20
      `logo`; asserts exported sheet's image at the original anchor has size `(20, 20)`
- [x] 4.2 RED: "Logo is absent on the tipo" test — `logo=None`; asserts exported image size
      stays `(10, 10)` and anchor `_from.col`/`_from.row` are unchanged (passed immediately —
      no code touches `_images` without a `logo`, correctly describing current no-op behavior;
      kept as a regression guard, same pattern as PR 2's task 3.6)
- [x] 4.3 RED: "template has no image, logo is set" test — `imagen=None`, `logo=` set; asserts
      `hoja._images == []` (also passed immediately for the same reason as 4.2 — no anchor to
      swap onto; kept as a regression guard against the rejected hardcoded-cell alternative)
- [x] 4.4 GREEN: `_intercambiar_logo(hoja, logo)` implemented in `generador.py` per design D4 —
      `ImagenOpenpyxl(BytesIO(logo.read()))`, reuses `original.anchor` object (not just
      coordinates), `hoja._images.remove(original)`, `hoja.add_image(nueva)`
- [x] 4.5 Wired into `generar_reporte`'s main sequence as step 5, between `_validar_completitud`
      (step 4) and `_escribir_valores` (step 6), matching the design sequence diagram exactly

### Phase 5: Integration and Cleanup (PR 3, this run)
- [x] 5.1 Full `tipos_reporte/tests/test_generador.py` run: 22/22 passed. Every spec.md
      requirement/scenario has a corresponding test (Template Loading → 2.1/2.2; Values-Dict
      Contract → 3.1/3.2; Missing Required Values → 2.6/2.7/2.8; Logo Swap → 4.1/4.2;
      Sheet-Only Export → 3.5/3.6; Return Value → 3.8)
- [x] 5.2 Full `tipos_reporte/tests/` app suite: 102/102 passed (0 regressions vs. the 99-test
      PR 2 baseline — the 3 new logo tests account for the delta). Default `hojas_extra=()`/
      `imagen=None` fixture behavior confirmed unaffected — all pre-Slice-4 tests still pass.
- [x] 5.3 Reviewed `generador.py` docstrings — `_destinos`, `_escribir_valores`,
      `_validar_completitud` already document the values-dict contract (scalar `id` key vs.
      `id_inicio`/`id_fin` range keys, membership-over-truthiness) from PR 1/2; module docstring
      and `generar_reporte`'s docstring updated this run to drop the now-stale "logo swap lands
      in a later PR" notes, since all 8 sequence steps are implemented
- [x] 5.4 Confirmed: design's Threat Matrix remains `N/A` — no routing/shell/subprocess/VCS
      boundary was introduced by the logo-swap implementation; the one untrusted-input surface
      (admin-uploaded logo image parsed by openpyxl/Pillow via `ImagenOpenpyxl`) is unconditionally
      wrapped by the same design that already converts template-parse failures into
      `PlantillaIlegible` — no new exception path bypasses that

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-2.10 | see PR 1 record | — | — | ✅ | ✅ | ✅ | ➖ None needed |
| 3.1-3.9 | see PR 2 record | — | — | ✅ | ✅ | ✅ | ➖ None needed |
| 4.1 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written, failed with `imagen_exportada.size == (10, 10)` (still the template's original image) before 4.4 | ✅ Passed after 4.4 | ➖ Single scenario (logo-present path has one shape) | ➖ None needed |
| 4.2 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written; passed immediately (no code path touches `_images` when `logo` is falsy) — kept as an explicit regression guard for the "logo absent → untouched" proposal decision | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 4.3 | `tipos_reporte/tests/test_generador.py` | Unit (DB) | ✅ 19/19 | ✅ Written; passed immediately (no anchor exists when `hoja._images` is empty, so the `originales` guard short-circuits) — kept as an explicit regression guard against the rejected hardcoded-cell alternative | ✅ Passed | ➖ Single scenario | ➖ None needed |
| 4.4 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 19/19 | — | ✅ Passed (drove 4.1's fix; confirmed 4.2/4.3 stayed green) | ✅ 3 cases (present/absent/no-template-image) | ✅ Docstring clarified anchor-object-vs-coordinates rationale |
| 4.5 | `tipos_reporte/generador.py` | Unit (DB) | ✅ 19/19 | — | ✅ Confirmed by 4.1-4.3 (call site placed between steps 4 and 6) | ➖ N/A | ➖ None needed |

### Test Summary (this run)
- **Total tests added this run**: 3 (`tipos_reporte/tests/test_generador.py`) — logo-present,
  logo-absent, template-has-no-image-logo-set
- **Total tests passing (module)**: 22/22 (19 from PR 1+2 + 3 new)
- **Total tests passing (full `tipos_reporte/tests/` suite)**: 102/102 (99 from PR 2 baseline +
  3 new — 0 regressions)
- **Layers used**: Unit (`@pytest.mark.django_db` tests exercising `generar_reporte` against a
  real in-memory `openpyxl`/Pillow workbook+image round trip)
- **Approval tests**: None — no refactoring tasks, only one additive function
- **Pure functions created this run**: `_intercambiar_logo` (pure over `hoja`/`logo`, no I/O
  beyond in-memory openpyxl/Pillow object mutation and reading the uploaded `logo` field's bytes)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `pytest tipos_reporte/tests/test_generador.py -k "logo" -q` → `3 passed, 19 deselected` |
| Runtime harness command/scenario and exact result | `pytest tipos_reporte/tests/ -q` (full app suite, includes DB-backed `@pytest.mark.django_db` tests using real Postgres via `--reuse-db` and real in-memory `openpyxl`/Pillow image round trips) → `102 passed` (0 regressions vs. the 99-test PR 2 baseline) |
| Rollback boundary | Revert the `_intercambiar_logo` function and its call site inside `tipos_reporte/generador.py`, and the 3 new tests appended to `tipos_reporte/tests/test_generador.py`. PR 1's exceptions/fixtures/template-loading/completeness-validation and PR 2's cell-writing/sheet-export code remain intact and untouched — zero blast radius outside this PR's slice. |

## Files Changed (this run)

| File | Action | What Was Done |
|------|--------|----------------|
| `tipos_reporte/generador.py` | Modified | Added `_intercambiar_logo(hoja, logo)` (design D4, Sequence step 5); wired it into `generar_reporte` between `_validar_completitud` and `_escribir_valores`; updated module and `generar_reporte` docstrings to drop stale "lands in a later PR" notes now that all 8 sequence steps are implemented |
| `tipos_reporte/tests/test_generador.py` | Modified | Added 3 tests covering Phase 4 scenarios: logo present (swapped at same anchor, new pixel size), logo absent (original image/anchor untouched), template has no image + logo set (no image inserted) |
| `openspec/changes/generador-excel-plantilla/tasks.md` | Modified | Marked tasks 4.1-4.5 and 5.1-5.4 `[x]` — ALL 34 tasks now complete |

## Deviations from Design

None. Implementation matches design D4 exactly: reuses the loaded `anchor` OBJECT (not its
coordinates) via `nueva.anchor = original.anchor`, uses `hoja._images.remove(original)` (not
`.clear()`), and inserts nothing when the template has no original image (rejected alternative:
hardcoded cell). Step ordering matches the Sequence diagram (step 5, between completeness
validation and cell writing).

## Issues Found

None.

## Workload / PR Boundary

- Mode: stacked-to-main chain, PR 3 of 3 (FINAL — as scoped by the orchestrator's launch prompt)
- Current work unit: Unit 3 — "Logo swap (present/absent) implementation and tests" (per
  tasks.md's Suggested Work Units table), plus Phase 5 integration/cleanup which was gated on
  Phase 4 landing
- Boundary: starts from PR 2's merged state (template loading, completeness validation, cell
  writing, sheet-only export all implemented and tested); ends with logo swap (present/absent/
  no-template-image paths) fully implemented and tested, and the full test suite confirmed
  regression-free
- Estimated review budget impact: ~90 authored changed lines (`generador.py` +30/-6,
  `test_generador.py` +105, `tasks.md` +9/-9) — well within the forecasted PR 3 slice size

## Status

34/34 tasks complete (Phase 1: 7/7, Phase 2: 10/10, Phase 3: 9/9, Phase 4: 5/5, Phase 5: 4/4).
**The change is fully implemented. Ready for `sdd-verify`.**

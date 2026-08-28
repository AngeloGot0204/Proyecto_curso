# Tasks: Generador de Excel desde plantilla (backlog #4)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~480-560 (exceptions ~25, generador.py ~110, conftest.py extension ~60, test_generador.py ~280-350) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (user decision needed) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Exceptions + fixture extension + template-load/completeness RED→GREEN tests | PR 1 | `pytest tipos_reporte/tests/test_generador.py -k "plantilla or incompletos"` | N/A — pure unit tests against synthetic fixtures, no external service | Revert `conftest.py` fixture diff and delete new exception classes; no other module depends on them yet |
| 2 | `_destinos` helper + scalar/range cell-writing pass + sheet-only export | PR 2 | `pytest tipos_reporte/tests/test_generador.py -k "escribe or hoja or export"` | N/A — pure unit tests via `openpyxl.load_workbook` round trip | Revert write-pass code inside `generador.py`; PR 1's exceptions/fixtures remain intact |
| 3 | Logo swap (present/absent) implementation and tests | PR 3 | `pytest tipos_reporte/tests/test_generador.py -k "logo"` | N/A — pure unit tests via `PIL.Image.open` size assertions | Revert logo-swap block in `generador.py`; PR 2's write pass keeps working without it |

## Phase 1: Foundation — Exceptions and Test Fixtures

- [x] 1.1 RED: In `tipos_reporte/tests/test_generador.py`, write a failing test asserting `tipos_reporte.generador.ProblemaDeGeneracion` is importable and is an `Exception` subclass.
- [x] 1.2 GREEN: Create `tipos_reporte/generador.py` with `ProblemaDeGeneracion(Exception)` (`regla = "problema-de-generacion"`), `PlantillaIlegible(ProblemaDeGeneracion)` (`regla = "plantilla-ilegible"`), and `ValoresIncompletos(ProblemaDeGeneracion)` (`regla = "valores-incompletos"`, stores sorted `self.faltantes` tuple, builds message listing missing ids).
- [x] 1.3 RED: Write a unit test instantiating `ValoresIncompletos(["b", "a"])` and asserting `.faltantes == ("a", "b")` and both ids appear in `str(exc)`.
- [x] 1.4 GREEN: Confirm 1.2's `ValoresIncompletos.__init__` sorts `faltantes` and satisfies 1.3 (already covered if implemented per design; adjust if test fails).
- [x] 1.5 In `tipos_reporte/tests/conftest.py`, extend the `plantilla_xlsx` fixture with optional `hojas_extra=()` (creates extra sheets via `wb.create_sheet(nombre)`) and `imagen=None` (path from a new `imagen_png` fixture; `wb.active.add_image(Image(str(ruta)), "B2")`), preserving current default behavior for existing Slice-3 tests.
- [x] 1.6 In `tipos_reporte/tests/conftest.py`, add the `imagen_png` fixture (`tmp_path`-based, `PIL.Image.new(...)`, parametrizable `nombre`/`tamano`/`color`) per design's `Test Fixture Extension` section.
- [x] 1.7 Add `valores` fixture helper(s) in `conftest.py` (or local test factory) that build a complete/partial `dict` keyed by leaf id, matching `estructura`'s `campos`/`items`/range ids, for reuse across `test_generador.py` scenarios.

## Phase 2: Template Loading and Completeness Validation

- [x] 2.1 RED: Write "Template loads successfully" test — valid `plantilla_xlsx` bytes on an activated `DefinicionDeTipo`, complete `valores`; assert `generar_reporte` returns a `BytesIO` re-openable via `load_workbook`.
- [x] 2.2 RED: Write "Template file cannot be read" test — factory default (non-xlsx) blob and a deleted/missing file path; assert `PlantillaIlegible` is raised, not a raw `openpyxl`/`OSError`.
- [x] 2.3 GREEN: In `generador.py`, implement `generar_reporte(definicion, valores)` steps 1-3: `definicion.tipo.plantilla.open("rb")` / `load_workbook(fh)` inside `try/finally` closing the handle; wrap open/parse/`libro[estructura["hoja"]]` KeyError into `PlantillaIlegible`, mirroring `activar_definicion`'s convention.
- [x] 2.4 RED: Add `_destinos(nodo)` unit test — given a scalar `campo` node, assert it returns `[(id, celda_coord)]`; given a `rango-hora-inicio-fin` node, assert it returns `[(f"{id}_inicio", celda_inicio), (f"{id}_fin", celda_fin)]`.
- [x] 2.5 GREEN: Implement `_destinos(nodo)` in `generador.py` using `_SUFIJO_POR_CLAVE` mapping and `_claves_de_celda_requeridas` (imported from `tipos_reporte.validacion`) per design D1.
- [x] 2.6 RED: Write "A required simple value is missing" test — required `campo` id absent from `valores`; assert `ValoresIncompletos` raised with that id in `.faltantes` and no bytes returned.
- [x] 2.7 RED: Write "Only one side of a required range value is missing" test — `descanso_inicio` present, `descanso_fin` absent; assert `.faltantes == ("descanso_fin",)`.
- [x] 2.8 RED: Write "Multiple missing ids are all reported together" test — two required ids missing; assert both appear in one raised `.faltantes` (not fail-fast on the first).
- [x] 2.9 RED: Write a completeness test confirming a non-`obligatorio` node with an absent key does NOT raise (per confirmed decision: only required leaf ids raise `ValoresIncompletos`).
- [x] 2.10 GREEN: Implement the completeness validation pass in `generador.py` — walk nodes via `_iterar_nodos`, filter to `nodo.get("obligatorio")` truthy, accumulate every `_destinos` key missing from `valores` (membership test, not truthiness, per D2/D3), raise one `ValoresIncompletos` with all accumulated ids before any mutation.

## Phase 3: Cell Writing and Sheet Export

- [ ] 3.1 RED: Write "Simple field value is written by id" scenario test (`turno`/`B2`/`"Mañana"`).
- [ ] 3.2 RED: Write "Range field values are written from two independent keys" scenario test (`descanso_inicio`→`C3`, `descanso_fin`→`C4`).
- [ ] 3.3 RED: Write a falsy-value test — `False`/`0`/`""` values for scalar fields are written as-is (not skipped), asserting D2's membership-over-truthiness rule.
- [ ] 3.4 GREEN: Implement the cell-writing pass in `generador.py` — walk all nodes via `_iterar_nodos`, use `_destinos(nodo)` for every present key in `valores` (present-but-not-required keys also written; absent optional keys leave cells untouched), write `hoja[coordenada] = valores[clave]`.
- [ ] 3.5 RED: Write "Only the declared sheet is exported" test using `hojas_extra=("Otra",)`; assert returned workbook's `sheetnames == [estructura["hoja"]]`.
- [ ] 3.6 RED: Write "Untouched sheet content remains byte-identical in structure" test — template with merged ranges outside anchor cells; assert `merged_cells.ranges` unchanged after generation.
- [ ] 3.7 GREEN: Implement sheet-only export in `generador.py` per design D5 — `del libro[nombre]` for every sheet `!= estructura["hoja"]`, then `libro.active = 0`.
- [ ] 3.8 RED: Write "Successful generation returns readable bytes" test — assert final `BytesIO` re-opens via `load_workbook` without error and `.seek(0)` was applied.
- [ ] 3.9 GREEN: Implement `libro.save(buffer); buffer.seek(0); return buffer` as the final step of `generar_reporte`.

## Phase 4: Logo Swap

- [ ] 4.1 RED: Write "Logo is present on the tipo" test — `plantilla_xlsx` with `imagen=` a 10x10 PNG, `tipo_de_reporte_factory(logo=SimpleUploadedFile(...))` with a distinct 20x20 PNG; assert exported sheet's image at the original anchor has size `(20, 20)`.
- [ ] 4.2 RED: Write "Logo is absent on the tipo" test — same template image, `logo=None`; assert exported sheet's image size remains `(10, 10)` and anchor position (`_from.col`/`_from.row`) is unchanged.
- [ ] 4.3 RED: Write a "template has no image, logo is set" test — `imagen=None`, `logo=` set; assert no image is inserted (`hoja._images` stays empty) rather than defaulting to a hardcoded cell.
- [ ] 4.4 GREEN: Implement the logo swap in `generador.py` per design D4 — when `definicion.tipo.logo` is set and `hoja._images` is non-empty, build `ImagenOpenpyxl(BytesIO(definicion.tipo.logo.read()))`, reuse `original.anchor`, `hoja._images.remove(original)`, `hoja.add_image(nueva)`; run this step before the cell-writing pass and after the completeness check.
- [ ] 4.5 Wire the logo swap call site into `generar_reporte`'s main sequence (step 5, between completeness validation and cell writing) and confirm step ordering matches the design sequence diagram.

## Phase 5: Integration and Cleanup

- [ ] 5.1 Run the full `tipos_reporte/tests/test_generador.py` suite and confirm every spec scenario in `openspec/changes/generador-excel-plantilla/specs/generacion-reporte-excel/spec.md` has a corresponding passing test.
- [ ] 5.2 Run the existing `tipos_reporte/tests/` suite (Slice-3 tests) to confirm the `plantilla_xlsx`/`conftest.py` fixture extension did not break prior tests (default `hojas_extra=()`/`imagen=None` behavior preserved).
- [ ] 5.3 Review `generador.py` docstrings/comments for clarity on the values-dict contract (scalar vs `_inicio`/`_fin` keys) so backlog #7's future `ValorDeReporte` adapter has a documented interface to satisfy.
- [ ] 5.4 Confirm no threat-matrix-driven tasks are outstanding (design's Threat Matrix is `N/A` — no routing/shell/subprocess/VCS boundary in this change).

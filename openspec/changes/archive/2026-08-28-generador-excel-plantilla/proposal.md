# Proposal: Generador de Excel desde plantilla (backlog #4)

## Intent

`TipoDeReporte`/`DefinicionDeTipo` (backlog #3) already declare, validate, and activate the
anchor-cell layout of a report template. There is no code yet that actually produces the filled
`.xlsx` file a supervisor downloads. Without this generator, backlog #7 (manual closing) has no
service to call, and the validated `estructura` contract stays unused. This change builds that
standalone generation service now, decoupled from the not-yet-built value-persistence models, so
it can be built and tested against #3 alone.

## Scope

### In Scope
- `tipos_reporte/generador.py::generar_reporte(definicion, valores) -> BytesIO`, accepting an
  already-**activated** `DefinicionDeTipo` and a plain `dict` of captured values (not a
  `ValorDeReporte` model/queryset — that model does not exist yet).
- Loads the original `.xlsx` via `openpyxl.load_workbook` from `TipoDeReporte.plantilla`, opened
  as a binary file object (`.open("rb")` / `.close()` in `try/finally`), converting read failures
  into a domain problem, following the `activar_definicion` convention.
- Writes only cell values into the anchor cells declared in `estructura["secciones"]` (`celda` for
  `campos`/simple `items`; `celda_inicio`/`celda_fin` for `rango-hora-inicio-fin` items). Never
  rebuilds the workbook.
- Logo swap: when `TipoDeReporte.logo` is set, replace the template's image via `ws._images`
  (remove original, insert the tipo's logo at the same position/anchor) before writing values.
  When `logo` is `None`, leave the template's original logo untouched (decision below).
- Exports only `estructura["hoja"]` per ADR-0002.
- Reuses `tipos_reporte/validacion.py` helpers (`_iterar_nodos`, `_mapa_de_celdas_no_ancla`,
  `_claves_de_celda_requeridas`, `_TIPOS_CON_RANGO`) instead of duplicating anchor logic.
- Defines and documents the values-dict contract (see Approach) as the interface backlog #7's
  future `ValorDeReporte` → dict adapter must satisfy.
- Tests-first (strict TDD): failing tests precede implementation for load/write/logo-swap/export
  behavior, using the existing `plantilla_xlsx` synthetic fixture pattern.

### Out of Scope
- `ValorDeReporte`/`Reporte` persistence models — reserved for backlog #5/#7.
- HTTP endpoint that triggers generation — backlog #7's job.
- Committing a real anonymized reference `.xlsx` as a golden-file fixture — deferred; no such file
  currently exists in the repo. This change instead extends the synthetic `plantilla_xlsx`
  fixture pattern with a merged-range + image scenario, sufficient for unit/regression coverage
  now. Adding a real-template golden test is flagged as recommended follow-up work.
- Formula preservation — out of scope; reference sheets contain no formulas (ADR-0002).

## Capabilities

### New Capabilities
- `generacion-reporte-excel`: service that fills a validated report template with captured values
  and an optional logo swap, returning the generated workbook bytes for a single declared sheet.

### Modified Capabilities
- None

## Approach

Plain function `generar_reporte(definicion: DefinicionDeTipo, valores: dict) -> BytesIO`:
1. Open `definicion.tipo.plantilla` binary, `load_workbook`.
2. If `definicion.tipo.logo` is set, remove the original image from
   `ws._images` and insert the logo image at the same anchor before writing values; otherwise
   leave `ws._images` untouched.
3. Walk `estructura["secciones"]` via `_iterar_nodos`; for each leaf, look up its value by id in
   `valores` and write it to the anchor cell(s).
4. **Values-dict contract (decision)**: `valores` is keyed by leaf `id` (the `campo`/`item` id).
   - Simple types (`texto`, `numero`, `fecha`, `hora`, `seleccion`, `booleano`): `valores[id]` is
     the scalar to write into `celda`.
   - `rango-hora-inicio-fin`: two independent keys, `valores[f"{id}_inicio"]` and
     `valores[f"{id}_fin"]`, written to `celda_inicio` and `celda_fin` respectively. Matches
     TECH-DESIGN's stated grain for `ValorDeReporte` ("una fila por valor capturado") — inicio and
     fin are two separate captured values/rows, not one composite value, so backlog #7's future
     adapter maps each `ValorDeReporte` row to one dict key directly, with no zipping needed.
   - Missing required keys raise a domain problem at generation time (see step 3.5 below) rather
     than writing a blank cell.
3.5. Before writing, validate that every id returned by `_claves_de_celda_requeridas` (for
   required `campos`/`items`) is present in `valores` (both `_inicio`/`_fin` keys for range items).
   Missing required ids raise a domain-level exception (e.g. `ValoresIncompletos`) listing the
   missing ids, mirroring the `activar_definicion` convention of converting foreseeable failure
   modes into typed domain problems rather than letting `generar_reporte` produce a silently
   incomplete `.xlsx`.
5. Save the target sheet only (`estructura["hoja"]") to a `BytesIO` and return it.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `tipos_reporte/generador.py` | New | `generar_reporte` service |
| `tipos_reporte/validacion.py` | None (read-only reuse) | Import existing anchor/node helpers |
| `tipos_reporte/tests/conftest.py` | Modified | Extend `plantilla_xlsx` fixture for logo/image scenario; add `valores` fixture helpers |
| `tipos_reporte/tests/test_generador.py` | New | TDD suite: load, anchor writes, range writes, logo swap (present/absent), sheet-only export |
| `adrs/0002-motor-de-generacion-de-excel.md` | None | Authoritative constraint reference only |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `ws._images` manipulation is undocumented/untested in openpyxl usage so far | Medium | Dedicated TDD coverage for logo-present and logo-absent paths before merge |
| No real reference template committed; synthetic fixture may not catch layout drift | Medium | Document as explicit follow-up; synthetic fixture covers structural contract (merges, anchors, image) |
| Range-value tuple contract could mismatch #7's eventual `ValorDeReporte` shape | Low | Documented explicitly here as the contract #7 must adapt to; revisit if #7 exploration finds a mismatch |
| Missing required values raise mid-generation, needs clear caller-facing error | Low | Typed `ValoresIncompletos` exception listing missing ids; caller (future #7 endpoint) surfaces it as a validation error, not a 500 |

## Rollback Plan

Single new module (`generador.py`) plus test/fixture additions; no migrations, no changes to
existing models or `validacion.py` behavior. Revert by deleting the new module and test file and
reverting the `conftest.py` fixture extension — no data or schema impact.

## Dependencies

- Backlog #3 (`TipoDeReporte`, `DefinicionDeTipo`, `validacion.py`) — merged.
- `openpyxl>=3.1,<4` (already pinned in `requirements.txt`).

## Success Criteria

- [ ] `generar_reporte` produces a valid `.xlsx` containing only the declared sheet with correct
      values in all anchor cells (`campos`, simple `items`, and `rango-hora-inicio-fin` pairs).
- [ ] Logo swap verified for both logo-present (image replaced at same anchor) and logo-absent
      (original template image untouched) cases.
- [ ] No workbook rebuild — non-target sheets/styling remain byte-identical to source template
      where unmodified.
- [ ] All tests written before implementation (strict TDD) and passing.

## Proposal question round — resolved

1. **Logo-absent behavior**: when `TipoDeReporte.logo` is not set, the template's original logo is
   left untouched. Removing it would ship an official document with no branding, worse than
   keeping the generic template logo.
2. **Range-value contract**: `rango-hora-inicio-fin` values arrive as two independent dict keys
   (`f"{id}_inicio"` / `f"{id}_fin"`), not a tuple. Matches TECH-DESIGN's "one row per captured
   value" grain for the future `ValorDeReporte` model — inicio/fin are two rows, not one composite
   value, so backlog #7's adapter maps each row to one key with no zipping.
3. **Golden-file strategy**: deferred. No real anonymized reference `.xlsx` is available now; the
   extended synthetic `plantilla_xlsx` fixture (merged ranges + image) is sufficient for this
   slice. Real-template regression coverage is flagged as recommended follow-up.
4. **Incomplete values**: the generator raises a domain-level exception (e.g. `ValoresIncompletos`)
   listing missing required ids, rather than silently writing blank cells — an official report with
   silently missing data is worse than a failed generation the caller must handle.

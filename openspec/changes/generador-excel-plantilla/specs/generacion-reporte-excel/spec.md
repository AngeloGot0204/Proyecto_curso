# Generación de Reporte Excel Specification

## Purpose

Define the behavior of `generar_reporte(definicion, valores) -> BytesIO`, a service that fills an
activated report template (`DefinicionDeTipo`) with captured values and returns the generated
workbook for a single declared sheet, without rebuilding the source `.xlsx`.

## Requirements

### Requirement: Template Loading

The system MUST load the source workbook from `definicion.tipo.plantilla`, opening it
as a binary file object and closing it in a `try/finally` block, converting read failures into a
domain-level problem (following the `activar_definicion` convention).

#### Scenario: Template loads successfully

- GIVEN an activated `DefinicionDeTipo` whose `tipo.plantilla` points to a valid `.xlsx`
- WHEN `generar_reporte(definicion, valores)` is called with a complete `valores` dict
- THEN the workbook is opened via `openpyxl.load_workbook` and the file handle is closed
  afterward, regardless of success or failure

#### Scenario: Template file cannot be read

- GIVEN a `definicion.tipo.plantilla` that cannot be opened or parsed as a workbook
- WHEN `generar_reporte(definicion, valores)` is called
- THEN a typed domain exception is raised instead of an unhandled `openpyxl`/IO exception

### Requirement: Values-Dict Contract

The system MUST accept `valores` as a plain `dict` keyed by leaf `id`, not a `ValorDeReporte`
model or queryset.

- Simple types (`texto`, `numero`, `fecha`, `hora`, `seleccion`, `booleano`) MUST be looked up as
  `valores[id]`.
- `rango-hora-inicio-fin` items MUST be looked up as two independent keys,
  `valores[f"{id}_inicio"]` and `valores[f"{id}_fin"]` — NOT a tuple or composite value under a
  single key.

#### Scenario: Simple field value is written by id

- GIVEN a `campo` with `id="turno"` and `celda="B2"` in `estructura`
- AND `valores = {"turno": "Mañana"}`
- WHEN `generar_reporte(definicion, valores)` is called
- THEN cell `B2` of the exported sheet contains `"Mañana"`

#### Scenario: Range field values are written from two independent keys

- GIVEN a `rango-hora-inicio-fin` item with `id="descanso"`, `celda_inicio="C3"`,
  `celda_fin="C4"`
- AND `valores = {"descanso_inicio": "08:00", "descanso_fin": "08:30"}`
- WHEN `generar_reporte(definicion, valores)` is called
- THEN cell `C3` contains `"08:00"` and cell `C4` contains `"08:30"`

### Requirement: Missing Required Values

The system MUST validate, before writing, that every required id from
`_claves_de_celda_requeridas` (including both `_inicio`/`_fin` keys for range items) is present in
`valores`. The system MUST raise a typed domain exception (e.g. `ValoresIncompletos`) listing all
missing ids and MUST NOT write blank cells or produce a partially-filled workbook.

#### Scenario: A required simple value is missing

- GIVEN a required `campo` with `id="supervisor"` not present in `valores`
- WHEN `generar_reporte(definicion, valores)` is called
- THEN a `ValoresIncompletos` exception is raised listing `"supervisor"` among the missing ids
- AND no `.xlsx` bytes are returned

#### Scenario: Only one side of a required range value is missing

- GIVEN a required `rango-hora-inicio-fin` item with `id="descanso"`
- AND `valores` contains `descanso_inicio` but not `descanso_fin`
- WHEN `generar_reporte(definicion, valores)` is called
- THEN a `ValoresIncompletos` exception is raised listing `"descanso_fin"` among the missing ids

#### Scenario: Multiple missing ids are all reported together

- GIVEN two required ids without values in `valores`
- WHEN `generar_reporte(definicion, valores)` is called
- THEN the raised `ValoresIncompletos` exception lists both missing ids in a single failure, not
  only the first one encountered

### Requirement: Logo Swap

When `definicion.tipo.logo` is set, the system MUST remove the template's original
image from `ws._images` and insert the tipo's logo image at the same position/anchor, before
writing values. When `logo` is `None`, the system MUST leave the template's original logo (and
`ws._images`) untouched.

#### Scenario: Logo is present on the tipo

- GIVEN `definicion.tipo.logo` is set to a valid image file
- AND the template sheet has an original image anchored at a known position
- WHEN `generar_reporte(definicion, valores)` is called with complete `valores`
- THEN the exported sheet's image at that anchor is the tipo's logo, not the original template
  image

#### Scenario: Logo is absent on the tipo

- GIVEN `definicion.tipo.logo` is `None`
- AND the template sheet has an original image
- WHEN `generar_reporte(definicion, valores)` is called with complete `valores`
- THEN the exported sheet retains the original template image unchanged

### Requirement: Sheet-Only Export, No Workbook Rebuild

The system MUST export only the sheet named in `estructura["hoja"]` and MUST NOT rebuild the
workbook: it only writes cell values (and swaps the logo image when applicable) into the loaded
workbook, without recreating sheets, styles, merges, or other workbook structure.

#### Scenario: Only the declared sheet is exported

- GIVEN a template workbook with multiple sheets and `estructura["hoja"] = "Reporte"`
- WHEN `generar_reporte(definicion, valores)` is called with complete `valores`
- THEN the returned `BytesIO` contains a workbook whose only sheet is `"Reporte"`

#### Scenario: Untouched sheet content remains byte-identical in structure

- GIVEN a template with merged cell ranges and styling on the declared sheet outside the anchor
  cells
- WHEN `generar_reporte(definicion, valores)` is called with complete `valores`
- THEN merged ranges and styling outside the written anchor cells are preserved unmodified in the
  returned workbook

### Requirement: Return Value

The system MUST return a `BytesIO` object containing the generated `.xlsx` bytes, ready to be
written to a file or an HTTP response by the caller.

#### Scenario: Successful generation returns readable bytes

- GIVEN complete `valores` for all required ids and a valid template
- WHEN `generar_reporte(definicion, valores)` is called
- THEN the return value is a `BytesIO` whose contents can be re-opened via
  `openpyxl.load_workbook` without error

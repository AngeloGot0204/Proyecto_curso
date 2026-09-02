# Motor de Definición de Tipo de Reporte Specification

## Purpose

Defines the `tipos_reporte` app's engine: the `TipoDeReporte` and `DefinicionDeTipo` models, YAML-to-JSONField declarative definition loading, and the exhaustive activation-time validator required by ADR-0003 and ADR-0008. Adding a report type is configuration, never code. Backlog item #3.

## Out of Scope (non-goals)

- `.xlsx` document generation — see `generacion-reporte-excel`.
- Capture wizard / form rendering — see `wizard-captura`.
- The administration screens that drive this engine — see `administracion-tipos-reporte`.
- Field/item-level role permissions: the `roles` key is Excel-column metadata only, it grants nothing.

## Requirements

### Requirement: TipoDeReporte Model

The system MUST provide a `TipoDeReporte` model with `nombre`, a unique `codigo`, `version_formato`, an optional `logo` image, a required `plantilla` (`.xlsx`), an `activo` status, a nullable `definicion_activa` foreign key, and creation/update timestamps. A type MUST be created inactive.

#### Scenario: Type is created inactive

- GIVEN an administrator creates a `TipoDeReporte`
- WHEN the row is persisted
- THEN `activo` is `False` and `definicion_activa` is null

#### Scenario: codigo uniqueness is enforced

- GIVEN a `TipoDeReporte` with `codigo="RIR"` exists
- WHEN a second type is saved with the same `codigo`
- THEN the save MUST be rejected

### Requirement: DefinicionDeTipo Model and YAML Loading

The system MUST provide a `DefinicionDeTipo` storing `archivo_yaml`, the raw `yaml_fuente`, and the normalized `estructura` as a `JSONField`. Saving a definition MUST parse the YAML with PyYAML and populate `estructura`.

Malformed YAML MUST be rejected at save time with an actionable error, persisting nothing partially.

#### Scenario: Valid YAML populates estructura

- GIVEN an administrator uploads a syntactically valid YAML definition
- WHEN the definition is saved
- THEN `yaml_fuente` holds the raw text and `estructura` holds the parsed structure

#### Scenario: Malformed YAML is rejected

- GIVEN an administrator uploads YAML with a syntax error
- WHEN the save is attempted
- THEN the save MUST be rejected with an actionable message
- AND no `DefinicionDeTipo` row is persisted

### Requirement: Definition Names Its Sheet

The definition MUST declare a `hoja` key naming the worksheet it maps onto. It MUST NOT be inferred from a default, because the reference workbook carries a second, hidden report format in the same file (ADR-0002).

Activation MUST reject a definition whose declared `hoja` does not exist in the template, and MUST reject one that omits the key.

#### Scenario: Missing hoja key is rejected

- GIVEN a definition whose `estructura` has no `hoja` key
- WHEN activation is attempted
- THEN validation fails with rule `hoja-ausente`

#### Scenario: Declared sheet absent from template is rejected

- GIVEN a definition declaring `hoja: "No Existe"`
- WHEN activation is attempted against a template lacking that sheet
- THEN validation fails with rule `hoja-no-encontrada`

### Requirement: Closed Data-Type Catalog

The system MUST accept exactly these field data types: `texto`, `numero`, `fecha`, `hora`, `seleccion`, `booleano`, `rango-hora-inicio-fin`. Anything outside this set MUST be rejected at activation.

The catalog MUST be declared once and shared by both the models and the validator.

#### Scenario: Unknown data type is rejected

- GIVEN a definition declaring a field of type `moneda`
- WHEN activation is attempted
- THEN validation fails, reporting the offending field's location

### Requirement: Exhaustive Activation Validation

Activation MUST run every validation rule in one pass and accumulate all problems — never stop at the first error. The rules are:

- **R1** required structural fields present
- **R2** every declared data type is in the closed catalog
- **R3** every destination cell uses valid cell notation
- **R4** no two fields map to the same cell
- **R5** the template file and its declared sheet are readable
- **R6** every destination cell is a merge anchor (writing to a non-anchor cell of a merged range raises `AttributeError` in openpyxl — ADR-0002)
- **R7** attachment anchor slots use valid cell notation and stay within the allowed count

R1–R4 and R7 MUST be pure functions over a plain dict, with no database or filesystem access. R5–R6 require the template.

On any failure, the `TipoDeReporte` MUST remain exactly in its prior state, with no partial mutation.

#### Scenario: All problems reported in one pass

- GIVEN a definition with an unknown data type, an invalid cell notation and a cell collision
- WHEN activation is attempted
- THEN the result reports all three problems together
- AND the `TipoDeReporte` remains inactive

#### Scenario: Validation without a template skips R5-R6

- GIVEN a definition being checked while no template is supplied
- WHEN `validar_definicion` runs with `plantilla=None`
- THEN R1–R4 and R7 still run and R5–R6 are skipped

#### Scenario: Successful activation sets the active definition

- GIVEN a definition that passes every rule
- WHEN activation runs
- THEN `TipoDeReporte.activo` becomes `True` and `definicion_activa` points at that definition

### Requirement: Immutable Versions After Activation

Each successful activation MUST produce an immutable version. Once a `DefinicionDeTipo` leaves `borrador`, the fields `tipo_id`, `estructura`, `yaml_fuente` and `version` MUST be frozen and rejected on further edits. `version` is assigned once, at first activation, and MUST NOT be reassigned by a later re-activation of the same row.

Editing a definition in place while its `TipoDeReporte` is `activo` MUST be blocked. Deactivating makes a definition editable again, and a later activation increments the version.

#### Scenario: Frozen field edit is rejected

- GIVEN an activated `DefinicionDeTipo`
- WHEN a save attempts to change its `estructura`
- THEN the save MUST be rejected

#### Scenario: Version increments across activations

- GIVEN a type whose latest activated definition has `version=1`
- WHEN a new definition for that type is activated
- THEN the new definition receives `version=2`

### Requirement: Deletion Blocked After Any Successful Activation

Physical deletion of a `TipoDeReporte` or `DefinicionDeTipo` MUST be blocked once it has ever been activated, regardless of its current `activo` status, because activated definitions are referenced by existing `Reporte` rows. Deactivation remains available. Never-activated rows MAY be deleted.

#### Scenario: Previously activated type cannot be deleted

- GIVEN a `TipoDeReporte` that was activated and later deactivated
- WHEN deletion is attempted
- THEN the deletion MUST be blocked

#### Scenario: Never-activated draft can be deleted

- GIVEN a `DefinicionDeTipo` still in `borrador` that was never activated
- WHEN deletion is attempted
- THEN the row is deleted

### Requirement: Extending With a Second Report Type Requires No Code Change

Defining and activating a second, structurally different `TipoDeReporte` MUST NOT require any change to the validator, the models, or the generation engine.

#### Scenario: Second type activates through configuration alone

- GIVEN a second template and a YAML definition with a different section/field structure
- WHEN an administrator uploads and activates them
- THEN the type becomes active with no code change to `tipos_reporte` or `reportes`

### Requirement: File Storage for Template, Logo and YAML Uploads

`plantilla`, `logo` and `archivo_yaml` MUST be storable and readable back through Django's storage API — the local filesystem in development and tests, and Vercel Blob in production (see `config/storage.py`, ADR-0009). An uploaded template MUST be readable back by openpyxl. A non-image file uploaded as `logo` MUST be rejected as an invalid image.

#### Scenario: Uploaded template is readable back

- GIVEN an administrator uploads a valid `.xlsx` template
- WHEN the activation validator opens it
- THEN openpyxl reads the workbook and its declared sheet

#### Scenario: Non-image logo is rejected

- GIVEN an administrator uploads a text file as `logo`
- WHEN the form is validated
- THEN the upload MUST be rejected as an invalid image

## Dependency Note

`DefinicionDeTipo.estructura` is the sole source of truth that `wizard-captura` and `generacion-reporte-excel` read from — neither may hard-code a report type's structure. This capability depends on `usuarios-y-autenticacion` for admin-gated access.

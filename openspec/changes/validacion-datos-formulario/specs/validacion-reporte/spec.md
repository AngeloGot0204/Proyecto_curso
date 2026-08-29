# validacion-reporte Specification

## Purpose

Provide server-side aggregate validation of a `Reporte`'s persisted values, distinguishing blocking errors from non-blocking warnings, and a review screen (S-09) that surfaces both before generation.

## Requirements

### Requirement: Aggregate validation function

The system MUST provide `reportes/validacion.py::validar_reporte(reporte)`, which walks the `Reporte`'s `DefinicionDeTipo.estructura` nodes against persisted `ValorDeReporte` rows and returns two buckets: `errores` (blocking) and `advertencias` (non-blocking). Each item in either bucket MUST carry `identificador_de_campo` and `seccion_id`.

The obligatorio-missing-value detection MUST reuse `tipos_reporte/generador.py`'s existing obligatorio-detection logic (shared helper/function), and MUST NOT reimplement it independently.

#### Scenario: All obligatorio fields filled produces no errores

- GIVEN a `Reporte` whose `ValorDeReporte` rows satisfy every `obligatorio` field in its structure
- WHEN `validar_reporte(reporte)` is called
- THEN `errores` MUST be empty

#### Scenario: Missing obligatorio field produces an errore

- GIVEN a `Reporte` missing a value for one field marked `obligatorio`
- WHEN `validar_reporte(reporte)` is called
- THEN `errores` MUST contain one entry with that field's `identificador_de_campo` and its `seccion_id`

#### Scenario: Obligatorio detection matches the generator exactly

- GIVEN a `Reporte` and its persisted values
- WHEN `validar_reporte(reporte)`'s obligatorio check runs and `tipos_reporte/generador.py::_validar_completitud` runs against the same values
- THEN both MUST identify the same set of missing obligatorio fields

#### Scenario: Stray hora_fin<=hora_inicio produces an advertencia, not an errore

- GIVEN a `Reporte` with a `rango-hora-inicio-fin` field whose persisted `fin` value is less than or equal to its `inicio` value (e.g. persisted via a direct POST that bypassed client-side JS)
- WHEN `validar_reporte(reporte)` is called
- THEN `advertencias` MUST contain one entry for that field
- AND `errores` MUST NOT contain an entry for that field

#### Scenario: "No cumple" without observación produces an advertencia

- GIVEN a `Reporte` with a `seleccion` field whose persisted value is the exact string "No cumple" and no corresponding `{id}_observacion` value is persisted
- WHEN `validar_reporte(reporte)` is called
- THEN `advertencias` MUST contain one entry for that field

#### Scenario: "No cumple" with observación produces no advertencia for that item

- GIVEN a `Reporte` with a `seleccion` field whose persisted value is exactly "No cumple" and a non-empty `{id}_observacion` value is persisted
- WHEN `validar_reporte(reporte)` is called
- THEN `advertencias` MUST NOT contain an entry for that field

### Requirement: Review screen (S-09)

The system MUST expose `/reportes/<reporte_id>/revision/`, rendering a "Debes corregir" list from `errores` (each item linked to its owning `paso`/`seccion`) and an "Advertencias" list from `advertencias`, both produced by `validar_reporte`.

The "Generar" control MUST be disabled if and only if `errores` is non-empty. Actual generation triggering is out of scope (backlog #7); the control has no functional destination yet.

#### Scenario: Errores present disables Generar

- GIVEN a `Reporte` for which `validar_reporte` returns a non-empty `errores` bucket
- WHEN the user requests the revision view
- THEN "Debes corregir" MUST list each errore with a working link to its `paso`
- AND the "Generar" control MUST be disabled

#### Scenario: No errores enables Generar

- GIVEN a `Reporte` for which `validar_reporte` returns an empty `errores` bucket
- WHEN the user requests the revision view
- THEN the "Generar" control MUST NOT be disabled
- AND any non-empty `advertencias` MUST still be listed under "Advertencias"

## Out of Scope

- Backlog #7: actual `.xlsx` generation trigger behind "Generar".
- Backlog #9: offline S-09 (stays server-rendered).
- Backlog #11: unsupported adjunto format blocking (no adjuntos model exists yet).

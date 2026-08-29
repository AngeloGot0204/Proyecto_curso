# Delta for wizard-captura

## ADDED Requirements

### Requirement: Client-side hora range feedback

The `paso.html` template MUST include vanilla JavaScript (no library, per ADR-0001) that disables the "Siguiente" control whenever a `rango-hora-inicio-fin` pair's `fin` value is less than or equal to its `inicio` value.

#### Scenario: Invalid hora range disables Siguiente

- GIVEN a rendered step containing a `rango-hora-inicio-fin` field
- WHEN the user sets `fin` <= `inicio`
- THEN "Siguiente" MUST become disabled client-side

#### Scenario: Valid hora range re-enables Siguiente

- GIVEN a step where "Siguiente" was disabled due to `fin` <= `inicio`
- WHEN the user corrects the values so `fin` > `inicio`
- THEN "Siguiente" MUST become enabled again

### Requirement: Server-side non-blocking hora range re-check

On `paso` POST, the system MUST re-check any `rango-hora-inicio-fin` pair for `fin` <= `inicio` server-side, as defense-in-depth against a client that bypasses the JS check (e.g. a direct POST). This check MUST NOT block persistence or return a validation error; it exists to make the condition visible later at S-09 via `validar_reporte`.

#### Scenario: Direct POST with invalid hora range still persists

- GIVEN a step POST submitted directly (bypassing client-side JS) with `fin` <= `inicio` for a `rango-hora-inicio-fin` field
- WHEN the server processes the POST
- THEN the values MUST still be upserted into `ValorDeReporte`
- AND the response MUST NOT be a validation error

### Requirement: "No cumple" observación toggling

When a `seleccion` field's value is set to the exact string "No cumple", the system MUST reveal (client-side JS) a required `{id}_observacion` companion text field. On submission, this observación value MUST persist via the same two-key `ValorDeReporte` pattern already used for `rango-hora-inicio-fin` (i.e. `identificador_de_campo=f"{id}_observacion"`).

#### Scenario: Selecting "No cumple" reveals observación field

- GIVEN a rendered `seleccion` field
- WHEN the user selects the exact value "No cumple"
- THEN the `{id}_observacion` field MUST become visible and required client-side

#### Scenario: Observación persists under the companion key

- GIVEN a step POST where a `seleccion` field's value is "No cumple" and its `{id}_observacion` field has a value
- WHEN the server processes the POST
- THEN a `ValorDeReporte` row with `identificador_de_campo=f"{id}_observacion"` MUST be upserted with that value

## MODIFIED Requirements

### Requirement: Non-blocking obligatorio marker

For fields marked `obligatorio` in the structure, the system MUST render the HTML `required` attribute and a visual marker, and MUST NOT block submission server-side on missing values. This non-blocking guarantee also applies to the new hora-range and "No cumple" checks added by this change: none of the three pre-generation rules (missing obligatorio, invalid hora range, unacknowledged "No cumple") may block a step's POST. Blocking evaluation happens only at the S-09 review screen, via `validar_reporte`.
(Previously: only covered the obligatorio-missing-value case; now explicitly extends the non-blocking guarantee to the hora-range and "No cumple" checks introduced by this change.)

#### Scenario: Missing obligatorio field does not block persistence

- GIVEN a field marked `obligatorio` in the structure
- WHEN the step is submitted without a value for that field
- THEN the system MUST still upsert the other submitted values and MUST NOT return a validation error for the missing field

#### Scenario: Existing non-blocking test remains true

- GIVEN the existing test `test_post_paso_sin_valor_obligatorio_no_bloquea`
- WHEN this change's hora-range and "No cumple" server-side checks are added to the `paso` POST handler
- THEN that test MUST continue to pass unmodified in intent: a step POST missing an obligatorio value MUST NOT be blocked, regardless of what `validar_reporte` would later report for the same `Reporte`

## Out of Scope

- Backlog #7: visto bueno / actual `.xlsx` generation trigger.
- Backlog #9: offline S-09 (stays server-rendered).
- Backlog #11: unsupported adjunto format blocking (no adjuntos model exists yet).
- Any change to D8's non-blocking step-level POST semantics beyond adding the two new non-blocking checks described above.

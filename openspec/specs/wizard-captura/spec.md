# wizard-captura Specification

## Purpose

Provide a server-rendered, multi-step wizard that renders one HTML step per `seccion` of a `DefinicionDeTipo.estructura`, persisting captured values immediately without relying on session state.

## Requirements

### Requirement: One URL and dynamic form per section

The system MUST expose one URL per `seccion` and build a Django `Form` dynamically from that section's `campos`/`items`, mapping field types to widgets: `texto`→text, `numero`→number, `fecha`→date, `hora`→time, `seleccion`→select, `booleano`→checkbox, `rango-hora-inicio-fin`→two time inputs.

#### Scenario: Section renders with correct widgets

- GIVEN a `DefinicionDeTipo` whose structure declares a section with a `texto` field and a `rango-hora-inicio-fin` field
- WHEN the user requests that section's URL
- THEN the rendered form MUST include a text input for the `texto` field and two time inputs for the range field

#### Scenario: Section with no campos/items still renders

- GIVEN a section in `estructura` with an empty `campos`/`items` list
- WHEN the user requests that section's URL
- THEN the system MUST render the step shell without error, showing no fields, and MUST still allow navigation to the next step

### Requirement: Per-step durable persistence

The system MUST upsert `ValorDeReporte` rows on each step's POST, without storing wizard progress in the session.

#### Scenario: Step POST persists immediately

- GIVEN a rendered section form
- WHEN the user submits the form
- THEN each field's value is upserted into `ValorDeReporte` before the response is returned
- AND no wizard state is written to the session

### Requirement: GET rehydration from persisted rows

The system MUST populate a section's form initial data by reading existing `ValorDeReporte` rows for the current `Reporte`.

#### Scenario: Revisiting a completed step shows saved values

- GIVEN a `Reporte` with previously saved values for a section
- WHEN the user navigates back to that section's URL
- THEN the form MUST render pre-filled with the previously saved values

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

### Requirement: Non-blocking obligatorio marker

For fields marked `obligatorio` in the structure, the system MUST render the HTML `required` attribute and a visual marker, and MUST NOT block submission server-side on missing values. This non-blocking guarantee also applies to the new hora-range and "No cumple" checks added by this change: none of the three pre-generation rules (missing obligatorio, invalid hora range, unacknowledged "No cumple") may block a step's POST. Blocking evaluation happens only at the S-09 review screen, via `validar_reporte`.

#### Scenario: Missing obligatorio field does not block persistence

- GIVEN a field marked `obligatorio` in the structure
- WHEN the step is submitted without a value for that field
- THEN the system MUST still upsert the other submitted values and MUST NOT return a validation error for the missing field

#### Scenario: Existing non-blocking test remains true

- GIVEN the existing test `test_post_paso_sin_valor_obligatorio_no_bloquea`
- WHEN this change's hora-range and "No cumple" server-side checks are added to the `paso` POST handler
- THEN that test MUST continue to pass unmodified in intent: a step POST missing an obligatorio value MUST NOT be blocked, regardless of what `validar_reporte` would later report for the same `Reporte`

### Requirement: Authentication required

The system MUST block unauthenticated access to any wizard step, consistent with the existing `@login_required` convention.

#### Scenario: Unauthenticated request is redirected

- GIVEN a user who is not authenticated
- WHEN they request any wizard step URL
- THEN the system MUST redirect them to the login flow instead of rendering the step

## Out of Scope

- Required-field enforcement or "No cumple" warnings (backlog #6).
- Visto bueno / closing a report (backlog #7).
- Collaboration, invitations, or roles beyond creator-only access (backlog #8).
- Offline capture, service worker, IndexedDB (backlog #9).
- Sync and `numero_registro` assignment (backlog #10).

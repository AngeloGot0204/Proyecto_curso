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

### Requirement: Non-blocking obligatorio marker

For fields marked `obligatorio` in the structure, the system MUST render the HTML `required` attribute and a visual marker, and MUST NOT block submission server-side on missing values.

#### Scenario: Missing obligatorio field does not block persistence

- GIVEN a field marked `obligatorio` in the structure
- WHEN the step is submitted without a value for that field
- THEN the system MUST still upsert the other submitted values and MUST NOT return a validation error for the missing field

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

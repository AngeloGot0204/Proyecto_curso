# Seleccion Tipo Reporte Specification

## Purpose

Give an authenticated user (S-03) a screen listing active `TipoDeReporte`
options for starting a new report, submitting to the existing
`reportes_nuevo` route — the entry point reached from "Mis reportes" (S-02)
"+ Nuevo reporte".

## Requirements

### Requirement: Active Tipo De Reporte Listing

The system MUST list every `TipoDeReporte` with `activo=True` and a
`definicion_activa`, showing at minimum código and número de secciones per
type. The view MUST require authentication.

#### Scenario: Active types are listed

- GIVEN two active `TipoDeReporte` rows with distinct códigos
- WHEN an authenticated user requests the S-03 screen
- THEN both types are listed with their código and section count

#### Scenario: Anonymous user is redirected

- GIVEN no authenticated session
- WHEN a request is made to the S-03 URL
- THEN the user is redirected to the login flow

### Requirement: Inactive Types Shown Disabled

The system MUST render inactive `TipoDeReporte` rows (or those without a
`definicion_activa`) in the same list, visibly disabled, labeled "próximamente",
and MUST NOT allow submitting a new report for them.

An administrator MUST additionally see a "Definir" link on an inactive type,
routing to that type's detail screen in `administracion-tipos-reporte`.

#### Scenario: Inactive type cannot be selected

- GIVEN a `TipoDeReporte` with `activo=False`
- WHEN the S-03 screen is rendered
- THEN it appears disabled with a "próximamente" label and its selection
  control does not submit

#### Scenario: Administrator sees the define shortcut

- GIVEN an authenticated administrator and an inactive `TipoDeReporte`
- WHEN the S-03 screen is rendered
- THEN a "Definir" link to that type's administration detail screen is shown

### Requirement: Submits To Existing Nuevo Reporte Route

Selecting an active type MUST submit a POST to the existing `reportes_nuevo`
route, unchanged, creating the `Reporte` exactly as that route already does.
This screen MUST NOT duplicate `Reporte`-creation logic.

#### Scenario: Selecting an active type creates a report

- GIVEN an active `TipoDeReporte` "AUD-01"
- WHEN the user selects it on S-03
- THEN a POST is submitted to `reportes_nuevo` for that tipo and a new
  `Reporte` is created via the existing view logic

### Requirement: Form Supplies id_local For Idempotent Creation

Each type's submission form MUST carry an `id_local` field so the server-side
idempotency contract in `reporte-idempotent-creation` is actually reachable
from the interface. The value MUST be generated client-side on submit
(`crypto.randomUUID()`) and MUST stay stable across a resubmission of the
same rendered form, so a double click resolves to one `Reporte` rather than
two.

The submit control MUST additionally be disabled once submitted, as a
first-line guard that does not replace the server-side check.

#### Scenario: Double submit creates a single report

- GIVEN an authenticated user on the S-03 screen
- WHEN the same form is submitted twice with the same generated `id_local`
- THEN exactly one `Reporte` exists for that `id_local` and creador

#### Scenario: Separate submissions get separate identifiers

- GIVEN an authenticated user who creates a report and returns to S-03
- WHEN they submit the freshly rendered form again
- THEN a new `id_local` is generated and a second `Reporte` is created

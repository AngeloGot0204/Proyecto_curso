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

#### Scenario: Inactive type cannot be selected

- GIVEN a `TipoDeReporte` with `activo=False`
- WHEN the S-03 screen is rendered
- THEN it appears disabled with a "próximamente" label and its selection
  control does not submit

### Requirement: Submits To Existing Nuevo Reporte Route

Selecting an active type MUST submit a POST to the existing `reportes_nuevo`
route, unchanged, creating the `Reporte` exactly as that route already does.
This screen MUST NOT duplicate `Reporte`-creation logic.

#### Scenario: Selecting an active type creates a report

- GIVEN an active `TipoDeReporte` "AUD-01"
- WHEN the user selects it on S-03
- THEN a POST is submitted to `reportes_nuevo` for that tipo and a new
  `Reporte` is created via the existing view logic

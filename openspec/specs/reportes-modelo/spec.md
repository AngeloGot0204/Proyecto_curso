# reportes-modelo Specification

## Purpose

Define the persistence contract for capturing report data against a `DefinicionDeTipo`: one `Reporte` per capture session, one `ValorDeReporte` row per captured value, and the report's lifecycle including its removal.

## Requirements

### Requirement: Reporte creation

The system MUST create exactly one `Reporte` record per capture session, with a foreign key to `TipoDeReporte`, a foreign key snapshotting the `DefinicionDeTipo` version used, a `creador` reference, a `fecha_creacion` timestamp, and a minimal `estado` field.

#### Scenario: First wizard step creates the Reporte

- GIVEN an authenticated user starting a new capture for a `TipoDeReporte`
- WHEN the first wizard step is submitted
- THEN a `Reporte` row is created referencing that `TipoDeReporte`, the `DefinicionDeTipo` in effect, and the user as `creador`
- AND `fecha_creacion` is set and `estado` holds its initial minimal value

#### Scenario: Subsequent steps reference the existing Reporte

- GIVEN a `Reporte` already exists for the current capture session
- WHEN a later wizard step is submitted
- THEN the system MUST reuse the existing `Reporte` (identified via URL param) instead of creating a new one

### Requirement: ValorDeReporte per captured value

The system MUST persist one `ValorDeReporte` row per captured value, with a foreign key to `Reporte`, an `identificador_de_campo`, a `valor`, an `autor`, and a `fecha`.

#### Scenario: Simple field value is stored as one row

- GIVEN a `Reporte` and a section field of type `texto`, `numero`, `fecha`, `hora`, `seleccion`, or `booleano`
- WHEN the field's value is submitted
- THEN exactly one `ValorDeReporte` row is created or updated, keyed by `identificador_de_campo`, with `autor` and `fecha` recorded

### Requirement: rango-hora-inicio-fin dual-row contract

For any campo/item of type `rango-hora-inicio-fin`, the system MUST persist exactly two `ValorDeReporte` rows: one keyed `{id}_inicio` and one keyed `{id}_fin`.

#### Scenario: Time range field produces two rows

- GIVEN a section field with identifier `horario` and type `rango-hora-inicio-fin`
- WHEN start and end times are submitted
- THEN a `ValorDeReporte` row with `identificador_de_campo = "horario_inicio"` and another with `"horario_fin"` are both persisted

### Requirement: Soft Deletion via eliminado_en

`Reporte` MUST carry a nullable `eliminado_en` timestamp, null by default, marking the report as removed.

Removal MUST be a soft delete: it stamps `eliminado_en` on the `Reporte` row and MUST NOT run an actual `.delete()`. Every related row — `ValorDeReporte`, `Adjunto`, `Generacion`, `ParticipacionEnReporte`, `CambioDeValor`, `VistoBueno` — MUST stay intact, so the report's audit trail survives its removal and recovery stays possible at the database level.

Deletion is destructive from the user's point of view and MUST be presented as such: the interface offers no way to restore a removed report.

#### Scenario: Deletion stamps the timestamp without destroying rows

- GIVEN a `Reporte` with captured values, attachments and a change history
- WHEN the report is deleted
- THEN `eliminado_en` holds the deletion time
- AND every related `ValorDeReporte`, `Adjunto`, `Generacion`, `ParticipacionEnReporte`, `CambioDeValor` and `VistoBueno` row still exists

### Requirement: Deleted Reports Are Invisible Everywhere

Every access path to a `Reporte` MUST exclude rows with a non-null `eliminado_en` — the accessible-reports queryset backing "Mis reportes", the shared participant-access lookup, and each creator-scoped view (closure, invitation, deletion itself).

A deleted report MUST behave exactly as one that never existed: a request for it MUST answer 404, for the creator as well as for every invited participant. The system MUST NOT distinguish "deleted" from "never existed" in its responses.

#### Scenario: Deleted report disappears from the list

- GIVEN a deleted `Reporte` the requesting user created
- WHEN the user requests "Mis reportes"
- THEN the report appears in no bucket

#### Scenario: Creator gets 404 on a deleted report

- GIVEN a deleted `Reporte`
- WHEN its creator requests any of its views
- THEN the response is 404

#### Scenario: Invited participant gets 404 on a deleted report

- GIVEN a deleted `Reporte` with an invited participant
- WHEN that participant requests any of its views
- THEN the response is 404

### Requirement: Creator-Only Deletion With Confirmation Step

Deletion MUST be restricted to the report's `creador`, following the same creator-scoped pattern as closure and invitation: a report belonging to someone else — including one the requester was invited to — MUST 404 exactly like a nonexistent one.

`GET` on the deletion route MUST render a confirmation screen with no side effect, naming the report and stating plainly that the action cannot be undone from the interface. `POST` MUST perform the deletion and redirect to "Mis reportes" with a success message.

#### Scenario: Creator confirms deletion

- GIVEN a `Reporte` created by user A
- WHEN A requests the deletion route with `GET`
- THEN a confirmation screen is rendered and `eliminado_en` stays null

#### Scenario: Confirmed deletion redirects to the list

- GIVEN user A on the confirmation screen for their report
- WHEN A submits the confirmation `POST`
- THEN `eliminado_en` is stamped and the response redirects to "Mis reportes"

#### Scenario: Invited participant cannot delete

- GIVEN a `Reporte` created by user A with user B invited
- WHEN B requests the deletion route
- THEN the response is 404 and `eliminado_en` stays null

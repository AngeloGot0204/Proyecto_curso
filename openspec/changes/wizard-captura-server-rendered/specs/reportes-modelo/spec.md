# reportes-modelo Specification

## Purpose

Define the persistence contract for capturing report data against a `DefinicionDeTipo`: one `Reporte` per capture session, and one `ValorDeReporte` row per captured value.

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

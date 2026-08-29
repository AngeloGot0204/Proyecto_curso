# Cierre Reporte Specification

## Purpose

Let a `Reporte`'s creator give manual approval ("visto bueno") once the report is eligible for generation, transitioning it to a terminal `TERMINADO` state. This closure gate is a precondition for document generation but does NOT lock further editing of captured values.

## Requirements

### Requirement: VistoBueno Model

The system MUST provide a `VistoBueno` model recording who approved a `Reporte`'s closure and when.

The model MUST have a foreign key to `Reporte`, a foreign key `usuario` to `settings.AUTH_USER_MODEL`, and an auto-populated `fecha` timestamp.

#### Scenario: VistoBueno created on closure

- GIVEN a `Reporte` eligible for closure
- WHEN `cerrar_reporte` succeeds
- THEN one `VistoBueno` row exists for that `Reporte`, with `usuario` set to the requesting creator and `fecha` populated

### Requirement: EstadoDeReporte.TERMINADO Member

The system MUST add a `TERMINADO` member to `EstadoDeReporte`, additive to the existing `EN_PROGRESO` member with no column change required.

#### Scenario: Estado transitions to TERMINADO

- GIVEN a `Reporte` with `estado=EN_PROGRESO`
- WHEN `cerrar_reporte` succeeds
- THEN `Reporte.estado` becomes `TERMINADO`

### Requirement: Creator-Only Closure

The system MUST expose a POST-only `cerrar_reporte` view that only the report's creator may invoke, mirroring the creator-scoping pattern used by `paso` (`get_object_or_404(..., creador=request.user)`).

#### Scenario: Non-creator attempts closure

- GIVEN a `Reporte` created by user A
- WHEN user B (authenticated, not the creator) POSTs to `cerrar_reporte` for that report
- THEN the response is 404
- AND no `VistoBueno` row is created

#### Scenario: Creator closes an eligible report

- GIVEN a `Reporte` created by user A where `puede_generar` is True
- WHEN user A POSTs to `cerrar_reporte`
- THEN a `VistoBueno` is created, `estado` becomes `TERMINADO`, and the response redirects to `revision`

### Requirement: Server-Side Eligibility Re-Check

The system MUST re-validate `puede_generar` server-side inside `cerrar_reporte` before creating a `VistoBueno`, independent of any client-side gating in `revision.html`.

#### Scenario: Closure rejected when ineligible

- GIVEN a `Reporte` created by user A where `puede_generar` is False
- WHEN user A POSTs to `cerrar_reporte`
- THEN the request is rejected (no `VistoBueno` created, `estado` unchanged)

### Requirement: Post-Closure Editing Remains Open

The system MUST NOT lock or restrict edits to `ValorDeReporte` rows after a `Reporte` reaches `TERMINADO`. The wizard stays editable after closure; this is an explicit product decision, not an oversight.

#### Scenario: Editing a value after closure succeeds

- GIVEN a `Reporte` with `estado=TERMINADO`
- WHEN its creator submits an updated value through the existing wizard `paso` flow
- THEN the `ValorDeReporte` update succeeds with no closure-related restriction

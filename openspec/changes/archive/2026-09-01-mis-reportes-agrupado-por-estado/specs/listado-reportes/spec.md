# Delta for Listado Reportes

## ADDED Requirements

### Requirement: Creador/Compartido/Todos Filter

The system MUST support an independent `?relacion=` filter with exactly three
values — `creados` (`creador == request.user`), `compartidos` (accessible
only via `ParticipacionEnReporte`), `todos` (default, no restriction) —
applied to the access-scoped queryset BEFORE status-bucket grouping. This
filter is a single, non-nested level: it MUST NOT be crossed with the status
buckets to produce 3x3 sub-groups.

#### Scenario: Filter restricts before grouping

- GIVEN user A created R1 (missing fields) and was invited to R2 (visto bueno present)
- WHEN user A requests the list with `?relacion=creados`
- THEN only R1 is considered for bucketing and R2 does not appear in any group

#### Scenario: Default is todos

- GIVEN user A has access to R1 (created) and R2 (shared)
- WHEN user A requests the list with no `?relacion=` parameter
- THEN both R1 and R2 are considered for bucketing

### Requirement: Percent Avance Per Card

Each listed report MUST display a % avance computed as
(obligatory fields with a persisted `ValorDeReporte`) / (total obligatory
fields declared by the report's `DefinicionDeTipo.estructura`), reusing the
exact same obligatorio enumeration `tipos_reporte.generador._validar_completitud`
already uses (via `ValoresIncompletos.faltantes`) — never a separate
reimplementation. Optional fields MUST NOT count in either the numerator or
the denominator.

#### Scenario: Partial completion renders a percentage

- GIVEN a report's definicion declares 10 obligatory fields and 7 have a persisted value
- WHEN the list is rendered
- THEN the card shows 70% avance

#### Scenario: Percent avance matches wizard completeness

- GIVEN a report considered `puede_generar` by `validar_reporte`
- WHEN the list is rendered
- THEN the card shows 100% avance

### Requirement: Numero De Registro Or Local Chip Per Card

Each listed report card MUST show `numero_registro` when assigned, or a
`local` chip when `numero_registro` is not yet assigned (offline/unsynced
case per `sincronizacion-numero-registro`).

#### Scenario: Assigned numero_registro renders

- GIVEN a report with `numero_registro=123`
- WHEN the list is rendered
- THEN the card shows "123"

#### Scenario: Unsynced report renders local chip

- GIVEN a report whose `numero_registro` is not yet assigned
- WHEN the list is rendered
- THEN the card shows a `local` chip instead of a number

### Requirement: Fixed Nuevo Reporte Entry Point

The system MUST render a fixed "+ Nuevo reporte" action on the list screen
that links to the S-03 type-selection screen (`seleccion-tipo-reporte`
capability), regardless of filter/search state.

#### Scenario: CTA is always present

- GIVEN any combination of `?q=`, `?relacion=`, `?estado=` filters, including
  an empty result set
- WHEN the list is rendered
- THEN the "+ Nuevo reporte" action is present and links to the S-03 screen

## MODIFIED Requirements

### Requirement: Status Bucket Grouping

The system MUST group each listed report into exactly one of three computed
buckets — "en progreso", "listos para generar", "terminados" (per
BACKLOG.md #12's wording) — evaluated in this priority order (first match
wins):

1. **terminados** — a `VistoBueno` row exists for the report.
2. **listos para generar** — no `VistoBueno`, and no obligatory field is
   missing (`validar_reporte(reporte).puede_generar` is true, per
   `validacion-reporte`).
3. **en progreso** — no `VistoBueno`, and at least one obligatory field is
   missing, regardless of who has or has not authored values on the report.

Grouping is computed read-time from existing data (`ValorDeReporte`,
`VistoBueno`, `DefinicionDeTipo`) and MUST NOT introduce a new persisted
status field or migration. The bucket is the SAME for every user with access
to a given report — grouping MUST NOT depend on the requesting user's own
authorship history (no per-viewer attribution).
(Previously: grouped only by creador/participant relationship, with no
status-bucket concept; see REMOVED "Creator/Participant Grouping" and
REMOVED "Status Indicator Limited to Real Estado Values". A prior draft of
this requirement introduced a fourth "pendiente de otra parte" bucket keyed
off per-viewer `ValorDeReporte.autor` history — dropped as unnecessary; that
case now falls under "en progreso" for every viewer.)

#### Scenario: Closed report is terminado for any viewer

- GIVEN a report with a `VistoBueno` row and missing optional fields
- WHEN any user with access requests the list
- THEN the report is grouped as "terminados"

#### Scenario: Complete report awaiting closure

- GIVEN a report with no `VistoBueno` and no missing obligatory fields
- WHEN a user with access requests the list
- THEN the report is grouped as "listos para generar"

#### Scenario: Missing fields groups as en progreso regardless of authorship

- GIVEN a report with no `VistoBueno`, missing obligatory fields, where the
  creador has authored at least one value and invited user B has never
  authored any value
- WHEN user B requests the list
- THEN the report is grouped as "en progreso" for user B, the same bucket
  it would be in for the creador

### Requirement: Search and Estado Filter

The system MUST support a `?q=` search parameter matching against
`tipo__nombre`, `tipo__codigo`, and `creador__username` (case-insensitive,
partial match), and an `?estado=` filter parameter restricting results to a
single computed status bucket (`en_progreso` | `listo_para_generar` |
`terminado`), applied after bucket computation. Both
parameters MUST be optional and combinable with `?relacion=`; an
unrecognized `?estado=` value MUST NOT raise an error and MUST result in an
unfiltered-by-estado result set. `?estado=terminado` MUST continue to work
as a redirect target for the `cierre-reporte` closure flow.
(Previously: `?estado=` filtered on the raw `EstadoDeReporte` DB field
directly.)

#### Scenario: Search by tipo nombre

- GIVEN reports of type "Auditoría" and type "Inspección" both accessible to user A
- WHEN user A requests the list with `?q=auditoria`
- THEN only reports of type "Auditoría" are returned

#### Scenario: Filter by computed estado bucket

- GIVEN user A has access to reports in the "en progreso" and "terminado" buckets
- WHEN user A requests the list with `?estado=terminado`
- THEN only reports bucketed as "terminado" are returned

#### Scenario: Post-closure redirect lands in terminado

- GIVEN user A just closed a report via `cierre-reporte`
- WHEN the resulting redirect includes `?estado=terminado`
- THEN the just-closed report appears in the "terminado" group

## REMOVED Requirements

### Requirement: Creator/Participant Grouping

(Reason: replaced by the independent `?relacion=` filter — grouping is now
by computed status bucket, not creator/participant relationship.)
(Migration: use the ADDED "Creador/Compartido/Todos Filter" requirement.)

### Requirement: Status Indicator Limited to Real Estado Values

(Reason: superseded by the MODIFIED "Status Bucket Grouping" requirement,
which now derives a 3-value computed status instead of rendering the raw
2-value `EstadoDeReporte` field.)
(Migration: use the MODIFIED "Status Bucket Grouping" requirement.)

### Requirement: No numero_registro Column in List

(Reason: the proposal now requires showing `numero_registro` or a `local`
chip per card to help users find synced vs. unsynced reports.)
(Migration: use the ADDED "Numero De Registro Or Local Chip Per Card"
requirement.)

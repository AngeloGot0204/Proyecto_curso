# Listado Reportes Specification

## Purpose

Give a logged-in user a searchable, filterable, paginated "Mis reportes"
dashboard (S-02) listing every `Reporte` they can access (created or invited),
grouped by computed status bucket, plus the post-login "Inicio" landing (S-00)
that summarizes those same buckets as counts.

## Requirements

### Requirement: Access-Scoped Report List

The system MUST list only `Reporte` rows the requesting user can access,
using the query
`Reporte.objects.filter(Q(creador=usuario) | Q(participaciones__usuario=usuario)).distinct()`,
matching the existing access pattern used by the `paso`/`revision`/`generar`/
`participantes` views. The view MUST require authentication (`@login_required`
or equivalent).

#### Scenario: User sees only accessible reports

- GIVEN user A created report R1, was invited to report R2, and has no
  relation to report R3 (created by user B, no invitations)
- WHEN user A requests the "Mis reportes" list
- THEN R1 and R2 appear in the response and R3 does not

#### Scenario: Anonymous user is redirected

- GIVEN no authenticated session
- WHEN a request is made to the "Mis reportes" list URL
- THEN the user is redirected to the login flow and no report data is returned

### Requirement: Status Bucket Grouping

The system MUST group each listed report into exactly one of three computed
buckets — "en progreso", "listos para generar", "terminados" — evaluated in
this priority order (first match wins):

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

Every bucket MUST be rendered even when empty, so the screen's shape stays
stable across filter states.

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
case per `reporte-idempotent-creation`).

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

### Requirement: Delete Entry Point on Own Cards

Each card for a report the requesting user created MUST offer a delete action
routing to the deletion flow defined in `reportes-modelo`. Cards for reports
the user only participates in MUST NOT offer it.

Because the action is destructive, the card's control MUST require an explicit
confirmation before submitting.

Deleted reports never reach this screen — the access-scoped queryset already
excludes them (see `reportes-modelo`).

#### Scenario: Creator sees the delete action

- GIVEN user A created report R1
- WHEN A requests the list
- THEN R1's card offers a delete action

#### Scenario: Participant does not see the delete action

- GIVEN user B was invited to report R2 created by user A
- WHEN B requests the list
- THEN R2's card offers no delete action

### Requirement: Search and Estado Filter

The system MUST support a `?q=` search parameter matching against
`tipo__nombre`, `tipo__codigo`, and `creador__username` (case-insensitive,
partial match), and an `?estado=` filter parameter restricting results to a
single computed status bucket (`en_progreso` | `listo_para_generar` |
`terminado`), applied after bucket computation. Both
parameters MUST be optional and combinable with `?relacion=`; an
unrecognized `?estado=` value MUST NOT raise an error and MUST result in an
unfiltered-by-estado result set. `?estado=terminado` MUST work
as a redirect target for the `cierre-reporte` closure flow.

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

#### Scenario: Search and estado filter combine

- GIVEN user A has access to multiple reports of varying tipo and estado
- WHEN user A requests the list with both `?q=` and `?estado=` set
- THEN only reports matching both conditions are returned

### Requirement: Pagination and Default Ordering

The system MUST paginate results using Django's `Paginator` and MUST default
to ordering by `fecha_creacion` descending (most recent first) when no
explicit ordering is requested.

#### Scenario: Most recent report appears first

- GIVEN user A has access to three reports created at different times
- WHEN user A requests the list with no ordering parameter
- THEN the reports are returned ordered by `fecha_creacion` descending

#### Scenario: Results beyond one page are paginated

- GIVEN user A has access to more reports than fit on one page
- WHEN user A requests the list
- THEN the response includes only one page of results plus pagination
  controls/metadata to reach subsequent pages

### Requirement: Admin Override Explicitly Out of Scope

The system MUST NOT grant any user visibility into reports they neither
created nor were invited to, including users with administrative privileges.
This is a known, documented limitation of this capability, not a silent
omission — a future capability may add explicit admin override.

#### Scenario: Admin user without access does not see unrelated reports

- GIVEN an admin/staff user with no `creador` or `ParticipacionEnReporte`
  relation to report R4
- WHEN the admin user requests the "Mis reportes" list
- THEN R4 does not appear in the response

### Requirement: Inicio Landing Renders Bucket Counts

The system MUST serve `usuarios/views.py::inicio` (S-00) as the post-login
landing destination for authenticated users, rendering one count per status
bucket (en progreso / listo para generar / terminado) over the user's
accessible reports. Counts MUST be computed with the same
`reportes_accesibles` + `Exists(VistoBueno)` + `construir_tarjetas` +
`agrupar_por_bucket` pipeline the "Mis reportes" list uses, so the numbers can
never drift from that list — counting is `len()` over the same bucketed
result, never a separate aggregation query.

Each count MUST link to the "Mis reportes" list filtered by that bucket's
`?estado=` value.

#### Scenario: Logged-in user lands on Inicio with counts

- GIVEN an authenticated user with at least one accessible report
- WHEN the user reaches the post-login landing route
- THEN the "Inicio" view is served, showing a count per bucket
- AND each count links to `reportes_mis` filtered by that bucket

#### Scenario: Counts match the list

- GIVEN a user whose accessible reports bucket as 2 en progreso and 1 terminado
- WHEN the user views Inicio
- THEN the counts read 2, 0 and 1 respectively, matching what "Mis reportes"
  would group

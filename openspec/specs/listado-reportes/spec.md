# Listado Reportes Specification

## Purpose

Give a logged-in user a searchable, filterable, paginated "Mis reportes"
dashboard listing every `Reporte` they can access (created or invited),
grouped by relationship, replacing the placeholder `usuarios/views.py::inicio`
screen.

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

### Requirement: Creator/Participant Grouping

The system MUST label or group each listed report as "creados por mí"
(`creador == request.user`) or "compartidos conmigo" (accessible only via
`ParticipacionEnReporte`), without altering the underlying access-control
logic (`permisos.tiene_acceso` stays unchanged).

#### Scenario: Report grouped as created by me

- GIVEN user A created report R1
- WHEN user A requests the list
- THEN R1 is labeled/grouped as "creados por mí"

#### Scenario: Report grouped as shared with me

- GIVEN user A was invited to report R2 created by user B
- WHEN user A requests the list
- THEN R2 is labeled/grouped as "compartidos conmigo" and not as "creados por mí"

### Requirement: Status Indicator Limited to Real Estado Values

The system MUST render a status chip using only the two real
`EstadoDeReporte` values that exist on `Reporte` today (`en_progreso`,
`terminado`). The system MUST NOT display a derived "generado" indicator in
this list; that indicator is explicitly deferred and out of scope for this
capability.

#### Scenario: en_progreso report renders its real status

- GIVEN a report with `estado=en_progreso`
- WHEN the list is rendered
- THEN the status chip shows "en progreso" and no "generado" badge is shown

#### Scenario: terminado report renders its real status

- GIVEN a report with `estado=terminado`
- WHEN the list is rendered
- THEN the status chip shows "terminado" and no "generado" badge is shown

### Requirement: Search and Estado Filter

The system MUST support a `?q=` search parameter matching against
`tipo__nombre`, `tipo__codigo`, and `creador__username` (case-insensitive,
partial match), and a `?estado=` filter parameter restricting results to a
single `EstadoDeReporte` value. Both parameters MUST be optional and
combinable; an unrecognized `?estado=` value MUST NOT raise an error and
MUST result in an empty or unfiltered-by-estado result set (design decides
which).

#### Scenario: Search by tipo nombre

- GIVEN reports of type "Auditoría" and type "Inspección" both accessible to
  user A
- WHEN user A requests the list with `?q=auditoria`
- THEN only reports of type "Auditoría" are returned

#### Scenario: Filter by estado

- GIVEN user A has access to reports with `estado=en_progreso` and
  `estado=terminado`
- WHEN user A requests the list with `?estado=terminado`
- THEN only `terminado` reports are returned

#### Scenario: Search and estado filter combine

- GIVEN user A has access to multiple reports of varying tipo and estado
- WHEN user A requests the list with both `?q=` and `?estado=` set
- THEN only reports matching both conditions are returned

### Requirement: Pagination and Default Ordering

The system MUST paginate results using Django's `Paginator` and MUST default
to ordering by `fecha_creacion` descending (most recent first) when no
explicit ordering is requested. Page size is a design-level decision.

#### Scenario: Most recent report appears first

- GIVEN user A has access to three reports created at different times
- WHEN user A requests the list with no ordering parameter
- THEN the reports are returned ordered by `fecha_creacion` descending

#### Scenario: Results beyond one page are paginated

- GIVEN user A has access to more reports than fit on one page
- WHEN user A requests the list
- THEN the response includes only one page of results plus pagination
  controls/metadata to reach subsequent pages

### Requirement: No numero_registro Column in List

The system MUST NOT display `numero_registro` (or `id_local`) as a column or
field in the "Mis reportes" list. It remains visible only in the report
detail view.

#### Scenario: List omits numero_registro

- GIVEN a report with a populated `numero_registro`
- WHEN the list is rendered
- THEN `numero_registro` does not appear anywhere in the list rendering

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

### Requirement: Replaces Placeholder Landing View

The system MUST replace `usuarios/views.py::inicio` as the post-login landing
destination for authenticated users with reports, routing them to the "Mis
reportes" list instead of the placeholder screen.

#### Scenario: Logged-in user lands on the new list

- GIVEN an authenticated user with at least one accessible report
- WHEN the user reaches the post-login landing route
- THEN the "Mis reportes" list view is served, not the prior placeholder
  template

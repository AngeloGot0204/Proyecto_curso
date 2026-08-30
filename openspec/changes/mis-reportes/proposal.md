# Proposal: Mis Reportes (S-02, backlog #12)

## Intent

Users currently land on a placeholder screen (`usuarios/views.py::inicio`) that
explicitly defers to backlog #12 and carries no report data. There is no way
to see reports a user created or was invited to without navigating directly
by URL. With backlog #10 (`sincronizacion-numero-registro`) archived,
`Reporte.id_local`/`numero_registro` now exist and are populated, so the
full TECH-DESIGN scope for this screen is unblocked. This change replaces
`inicio` with a real "Mis reportes" dashboard: a searchable, filterable,
paginated list scoped to the user's accessible reports.

## Scope

### In Scope
- New list view in `reportes/views.py`, reusing the existing access query
  `Reporte.objects.filter(Q(creador=usuario) | Q(participaciones__usuario=usuario)).distinct()`.
- Visual grouping/labeling of results into "created by me" vs. "shared with
  me" (based on `creador == request.user` vs. participant-only access).
- Status chip using the 2 real `EstadoDeReporte` values (`en_progreso`,
  `terminado`) — no derived "generado" indicator in this slice.
- Search on `tipo__nombre`, `tipo__codigo`, `creador__username`; `?estado=`
  filter.
- Django `Paginator`, ordered by `fecha_creacion` descending (page size left
  to design).
- New template(s) under `reportes/templates/reportes/` — first list-view
  precedent in this app (will likely be reused by #13).
- `usuarios/views.py::inicio` replaced to route to the new view (or removed
  in favor of the new URL as the post-login landing target).
- Tests extending the existing access-control pattern in
  `reportes/tests/test_views.py`.

### Out of Scope
- "Generado" as a visible state/badge (derivable from
  `Generacion.objects.filter(reporte=...).exists()`) — deferred, tracked as
  a follow-up.
- `numero_registro` as a list column — shown only in report detail, not in
  this listing.
- Administrator intervention/override to view reports the admin didn't
  create or get invited to (PRD edge case) — explicitly out of scope; will
  be documented as a known limitation, not silently dropped.
- Any change to `Reporte`, `ParticipacionEnReporte`, or access-control logic
  itself (`permisos.tiene_acceso` stays as-is).

## Capabilities

### New Capabilities
- `listado-reportes`: "Mis reportes" dashboard — search, filter, paginate,
  and group-label (creator/participant) the reports a user can access.

### Modified Capabilities
- None (no existing spec covers `usuarios/views.py::inicio`; it is a
  placeholder being replaced, not a specified capability).

## Approach

Build a single list view reusing the proven creator-or-participant access
query (already used by `paso`/`revision`/`generar`/`participantes`, backlog
#8). Partition the queryset (or annotate/label in Python) into "created by
me" and "shared with me" groups for template rendering. Apply `?q=` search
across `tipo__nombre`/`tipo__codigo`/`creador__username` and `?estado=`
filter, then paginate with Django's `Paginator`, defaulting to
`fecha_creacion` descending. Point the post-login route at this view,
replacing `inicio`'s placeholder. No new model fields or migrations
required — this is a read-only aggregation view over existing data.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reportes/views.py` | New | List view with search/filter/pagination/grouping |
| `reportes/urls.py` | Modified | New route for the list view |
| `reportes/templates/reportes/` | New | List template(s), first in this app |
| `usuarios/views.py` | Modified | `inicio` replaced/redirected to new view |
| `reportes/tests/test_views.py` | Modified | New access/search/filter/pagination tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| No prior list/pagination convention — this becomes precedent for #13 | Med | Keep the view function-based and template structure simple/explicit so #13 can copy it directly; document the pattern in design.md |
| Admin-intervention gap (PRD edge case) left unaddressed | Low | Document explicitly as a known limitation in this proposal and design, not silently omitted |
| "Generado" indicator omission may look incomplete vs. original wireframe | Low | User-confirmed deferral; documented as explicit follow-up, not silent scope cut |

## Rollback Plan

Revert the `usuarios/views.py::inicio` route change (redirect back to the
placeholder template) and remove the new URL/view/templates. No migrations
are introduced, so rollback requires no data changes — a straightforward
code revert.

## Dependencies

- Backlog #10 (`sincronizacion-numero-registro`) — archived 2026-08-30,
  provides `id_local`/`numero_registro`. Satisfied.
- Backlog #8 (`colaboracion-reporte`) — provides the access-control pattern
  reused here. Already merged.

## Success Criteria

- [ ] A logged-in user sees only reports they created or were invited to,
      grouped as "created by me" / "shared with me".
- [ ] Search by report type name/code and creator username works.
- [ ] Filtering by `estado` (en_progreso/terminado) works.
- [ ] Results are paginated and ordered by most recent first.
- [ ] `usuarios/views.py::inicio` no longer serves a placeholder for
      logged-in users with reports.

# Proposal: Mis Reportes — Agrupado por Estado + Selección de Tipo (S-02/S-03)

## Intent

Backlog #12 was re-scoped: "Mis reportes" must stop being a flat
creator/participant split and become a status-driven dashboard, per
`DESIGN.md` §S-02/§7 and `DESIGN2.md`. Today's implementation
(`reportes/templates/reportes/mis_reportes.html`,
`reportes/views.py::mis_reportes`) groups only by "creados por mí" /
"compartidos conmigo", shows no progress signal, and has no entry point for
starting a new report even though `reportes_nuevo` already works. Users
cannot tell at a glance whether a report needs their input, is waiting on a
teammate, or is ready to close out.

## Scope

### In Scope
- Regroup the list into three fixed status buckets, computed the same for
  every viewer (no per-user attribution): "en progreso" (faltan campos
  obligatorios, sin importar quién los completó), "listo para generar"
  (todo completo, sin visto bueno), "terminado" (con visto bueno —
  permanente, sin expiración; el change paralelo `cierre-en-participantes`
  redirige aquí tras el cierre). (Nota: un borrador previo de esta
  propuesta incluía un cuarto bucket "pendiente de otra parte"; el
  spec/design finalizados lo descartaron por depender de atribución
  por-viewer — ver `design.md`.)
- New single-switch filter: creados-por-mí / compartidos-conmigo / todos,
  applied before grouping (one grouping level, not nested).
- Keep the existing text search (`?q=`).
- Each card shows % de avance (campos obligatorios llenos / total de campos
  obligatorios de la `DefinicionDeTipo` activa; campos opcionales no
  cuentan) and N° de registro, or chip `local` when `numero_registro` is not
  yet assigned.
- Fixed "+ Nuevo reporte" action leading to a new S-03 screen listing active
  `TipoDeReporte` (código, N° de secciones); inactive types shown disabled
  with "próximamente". Submitting a type posts to the existing
  `reportes_nuevo` route.

### Out of Scope
- Changing `Reporte.estado` model values or migrations for a new DB-level
  status — grouping is computed, not persisted.
- Admin override visibility (still deferred per existing spec).
- Any change to `cierre-en-participantes`'s own close/redirect logic (only
  coordinate on the "terminado" group naming/criteria).
- Desktop layout, offline-queue banner changes.

## Capabilities

### New Capabilities
- `seleccion-tipo-reporte`: S-03 screen listing active report types for
  starting a new report, wired to the existing `reportes_nuevo` POST route.

### Modified Capabilities
- `listado-reportes`: replaces creator/participant grouping with three
  computed status buckets, adds the creador/compartido filter switch, adds
  % avance and numero_registro/`local` chip per card, adds the fixed
  "+ Nuevo reporte" entry point.

## Approach

Compute grouping and % avance server-side from existing data
(`Reporte.estado`, `ValorDeReporte`, `VistoBueno`, `DefinicionDeTipo`) — no
new persisted status field. Reuse the `reportes/listado.py` pure-helper
pattern established by the prior `mis-reportes` change. S-03 is a thin new
view/template reusing `TipoDeReporte.activo`/`definicion_activa`.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/listado.py` | Modified | Status-bucket + % avance + filter helpers |
| `reportes/views.py::mis_reportes` | Modified | New grouping/filter/context |
| `reportes/templates/reportes/mis_reportes.html` | Modified | 4 groups, filter switch, progress/registro chips, CTA |
| `reportes/views.py`, `reportes/urls.py`, new template | New | S-03 type-selection screen |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| "terminado" group criteria drifts from `cierre-en-participantes`'s redirect target | Med | Coordinate naming/criteria explicitly during design |
| % avance mismatched vs. wizard's own completion notion | Low | Reuse the same obligatorio-field enumeration the wizard/validation already use |

## Rollback Plan

Revert view/template/listado.py to the prior creator/participant grouping;
S-03 route/view/template are additive and can be removed without touching
existing `reportes_nuevo` behavior.

## Dependencies

- Coordinate with parallel change `cierre-en-participantes` (backlog #8) on
  the "terminado" group's exact name/criteria.

## Success Criteria

- [ ] Reports render into the correct one of three status groups.
- [ ] Filter switch (creados/compartidos/todos) works standalone, one grouping level.
- [ ] Card shows accurate % avance and numero_registro or `local` chip.
- [ ] "+ Nuevo reporte" reaches S-03 and creates a report via `reportes_nuevo`.

# Proposal: Move Report Closure (VistoBueno) From Revision To Participantes

## Intent

Realign implementation with the documented product design (DESIGN.md S-10)
and the redefined BACKLOG.md #8: the participants screen (S-10), not the
revision screen (S-09), is the owner of closing a report. Today
`revision.html` (S-09) hosts "Cerrar reporte" (creates `VistoBueno`), which
contradicts S-10's documented spec ("botón 'Marcar como terminado' ...
reservado al creador del reporte") and BACKLOG #8's explicit note that this
button "vive ahí (no en revisión/S-09)". This is a screen-ownership
correction, not a cosmetic relocation: closure becomes a participants/
collaboration concern (who has access, who can approve) rather than a
validation concern.

## Scope

### In Scope
- Move the "Cerrar reporte" (`VistoBueno`-creating) form/button from
  `revision.html` to `participantes.html`, creator-only, hidden entirely
  (not disabled) for non-creators — mirroring the existing invite-form
  visibility pattern.
- Preserve the exact ineligibility reason text ("Corregí N errores primero")
  on the moved button, consistent with retrofit-visual-design2 D6.
- Change `cerrar_reporte`'s post-success redirect target from
  `reportes_revision` to `reportes_mis` ("Mis reportes" / S-02). The
  `?estado=terminado` filter already exists in `listado-reportes`; no new
  grouping UI is required here.
- Add a "Cerrar en Participantes →" link on `revision.html` pointing to
  `reportes_participantes`, replacing the removed closure form.
- Keep "Generar" on `revision.html` (S-09) unchanged — out of scope for
  relocation; only the closure action moves.
- Update `cierre-reporte` and `colaboracion-reporte` specs to reflect the new
  screen ownership.

### Out of Scope
- Any change to `puede_generar` validation logic, `VistoBueno` model shape,
  or `EstadoDeReporte` values.
- Moving/altering "Generar" (document download) placement.
- Building the "grupo terminado" visual grouping in `mis_reportes` —
  tracked separately by the parallel `mis-reportes-agrupado-por-estado`
  change. This proposal only relies on the existing `?estado=` filter
  already specified in `listado-reportes`. **Assumption, to be confirmed
  against that spec if it lands first**: no new state/grouping value is
  introduced here — `EstadoDeReporte.TERMINADO` is reused as-is.
- Any widening/narrowing of who may invoke `cerrar_reporte` (remains strictly
  creator-only, per existing `cierre-reporte` spec).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `cierre-reporte`: "Creator-Only Closure" and "Server-Side Eligibility
  Re-Check" requirements' redirect behavior changes (redirects to
  `reportes_mis`, not `reportes_revision`). "Revision View Access Widens
  With Invitations" requirement's framing of `revision` as "the
  closure/review screen" is corrected — revision keeps validation
  display and "Generar" but no longer performs closure.
- `colaboracion-reporte`: "Participants and History View" requirement gains
  ownership of the closure action (creator-only "Marcar como terminado"
  button, hidden for non-creators, with ineligibility reason text).

## Approach

Move the closure `<form>` block from `revision.html` to `participantes.html`,
gated by `{% if reporte.creador_id == request.user.id %}` (same pattern as
the existing invite form) instead of the disabled-attribute pattern used
today. `participantes` view gains the `resultado`/`puede_generar` context
(reuse `validar_reporte`, matching what `revision` already computes) so the
template can render the exact blocking reason. `cerrar_reporte` view logic is
untouched except its `redirect(...)` target. `revision.html` drops its
closure form and gains a plain link to `reportes_participantes`.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/templates/reportes/participantes.html` | Modified | Adds creator-only closure form with ineligibility reason |
| `reportes/templates/reportes/revision.html` | Modified | Removes closure form, adds "Cerrar en Participantes →" link |
| `reportes/views.py::participantes` | Modified | Adds `resultado`/`puede_generar` to context |
| `reportes/views.py::cerrar_reporte` | Modified | Redirect target changes to `reportes_mis` |
| `openspec/specs/cierre-reporte/spec.md` | Modified | Redirect target, revision-screen framing |
| `openspec/specs/colaboracion-reporte/spec.md` | Modified | Participants view owns closure action |
| `reportes/tests/` | Modified | Tests covering closure redirect target and template placement |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Redirect to `reportes_mis` assumes that view/URL is stable | Low | `reportes_mis` already exists (backlog #12, `listado-reportes` spec) |
| Parallel `mis-reportes-agrupado-por-estado` change may rename/regroup the "terminado" state concept | Medium | Documented as explicit assumption; this change only depends on the existing `?estado=` filter, not on new grouping UI |
| Existing tests hardcode closure-button location in `revision.html` | Medium | Test updates included in scope |

## Rollback Plan

Revert the template edits (move the form back to `revision.html`), revert
`cerrar_reporte`'s redirect target to `reportes_revision`, and revert the two
spec deltas. No migrations or model changes are involved, so rollback is a
pure code/template/spec revert with no data implications.

## Dependencies

- None blocking. Soft coordination noted with the parallel
  `mis-reportes-agrupado-por-estado` change regarding the "terminado" group
  naming (non-blocking assumption documented above).

## Success Criteria

- [ ] "Marcar como terminado" (closure) button appears only on
      `participantes.html`, creator-only, hidden (not disabled) for
      non-creators.
- [ ] `revision.html` no longer creates `VistoBueno`; it links to
      Participantes for closure and keeps "Generar" unchanged.
- [ ] Closing a report redirects to `reportes_mis`.
- [ ] Ineligibility reason text is preserved verbatim on the moved button.
- [ ] `cierre-reporte` and `colaboracion-reporte` specs reflect the new
      ownership; all existing scenarios still pass or are updated
      consistently.

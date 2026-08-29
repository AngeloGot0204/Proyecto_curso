# Proposal: Cierre manual (visto bueno) y generación del documento

## Intent

Report data capture (backlog #4-#6) is complete, but a report can never be formally closed or turned into its final `.xlsx` document. The S-09 review screen already shows `puede_generar`, but its "Generar" button is dead markup. This change closes that gap: it lets the report's creator give manual approval ("visto bueno"), and lets any authenticated user then generate and download the populated document, with a durable audit trail of who generated it and when.

## Scope

### In Scope
- `VistoBueno` model (FK/O2O to `Reporte`, `usuario` FK, `fecha`) — created only by the report's creator.
- `Generacion` model (FK to `Reporte`, `usuario` FK, `fecha`) — one row per successful generation; any authenticated user; no cap on repeats (audit log, not a lock).
- `EstadoDeReporte.TERMINADO` member, set when `VistoBueno` is created (additive migration).
- `reportes/valores.py::valores_de_reporte(reporte)` — shared helper extracted from the duplicated `{v.identificador_de_campo: v.valor ...}` one-liner in `validacion.py` and `views.py::paso`.
- `reportes/views.py::cerrar_reporte` (POST, creator-only via `get_object_or_404(..., creador=request.user)`): re-validates `puede_generar` server-side, creates `VistoBueno`, sets `estado=TERMINADO`, redirects to `revision`.
- `reportes/views.py::generar` (POST, `@login_required` only): requires an existing `VistoBueno`, re-checks `puede_generar` (defense in depth), builds `valores`, calls `generador.generar_reporte`, catches `ProblemaDeGeneracion` and redirects to `revision` (S-09) with a Django messages framework flash error — never a raw 500, never a standalone error page — creates a `Generacion` row on success, streams the `.xlsx` via `HttpResponse` + `Content-Disposition: attachment`.
- Two new routes: `/reportes/<reporte_id>/cerrar/`, `/reportes/<reporte_id>/generar/`.
- `revision.html`: wire "Generar" to the real endpoint, gated on `puede_generar` AND `VistoBueno` existing; add a creator-only "Cerrar reporte" action, gated on `puede_generar`.
- New test pattern for file-download responses (`Content-Disposition`/`Content-Type` assertions, `load_workbook(BytesIO(response.content))` round-trip).
- Strict TDD: tests first for models, views, and `valores_de_reporte`.

### Out of Scope
- Fine-grained roles/permissions beyond "any authenticated user can generate" (backlog #8).
- Offline capture (#9) and sync (#10).
- New Sentry wiring (#14 owns integration); this change only confirms exceptions are caught and never surface as a 500.
- Locking or regressing captured values after closure (undecided by ADR-0006, not required by any AC).

## Capabilities

### New Capabilities
- `cierre-reporte`: manual visto-bueno closure by the report creator, transitioning `Reporte.estado` to `TERMINADO`.
- `generacion-documento`: on-demand `.xlsx` generation/download for a closed report, with an audit trail (`Generacion`).

### Modified Capabilities
None — `puede_generar` validation logic is unchanged; it stays orthogonal to visto-bueno gating (both conditions required together).

## Approach

Follow TECH-DESIGN's documented data model literally: two entities (`VistoBueno`, `Generacion`), no forced "generated exactly once" semantics. Reuse the existing `generador.generar_reporte` (backlog #4, stable, untouched). Extract the duplicated `valores` dict-comprehension into one shared helper before wiring the new view, per strict TDD.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/models.py` | Modified | Add `VistoBueno`, `Generacion`, `EstadoDeReporte.TERMINADO` |
| `reportes/migrations/` | New | Additive migration(s) for the above |
| `reportes/valores.py` | Modified | Add `valores_de_reporte(reporte)` helper |
| `reportes/views.py` | Modified | Add `cerrar_reporte`, `generar`; refactor `paso`/`validacion.py` to reuse helper |
| `reportes/urls.py` | Modified | Two new routes |
| `reportes/templates/reportes/revision.html` | Modified | Wire "Generar"; add "Cerrar reporte" |
| `reportes/tests/` | New | Model, view, and helper tests; new file-download assertion pattern |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Unbounded `Generacion` rows from repeated downloads | Low | Accepted as audit log; no functional issue |
| `ProblemaDeGeneracion` not reaching Sentry | Medium | Verify ADR-0008 wiring in `config/settings.py`; catch-and-render regardless |
| Race: two closes/generates in parallel | Low | `get_object_or_404` + re-check `puede_generar` server-side on both endpoints |

## Rollback Plan

Both migrations are additive (new tables, new enum member) — revert by reverting the migration and the view/template changes; no data loss to existing `Reporte`/`ValorDeReporte` rows.

## Dependencies

- `tipos_reporte.generador.generar_reporte` (backlog #4, done, unchanged).

## Success Criteria

- [ ] Creator can close a `puede_generar`-eligible report; `estado` becomes `TERMINADO`.
- [ ] Any authenticated user can generate/download the `.xlsx` only after `VistoBueno` exists.
- [ ] `ProblemaDeGeneracion` never surfaces as a raw 500; user sees a clean error.
- [ ] Repeated generation creates one `Generacion` row per success, no errors.
- [ ] `revision.html` buttons are functionally wired and correctly gated.

## Proposal question round

These decisions were confirmed by the user before this proposal was written; flagging them here for visibility rather than as open questions:
1. **Who can generate?** Any authenticated user (not creator-restricted) — deferred fine-grained roles to #8.
2. **Is generation repeatable?** Yes, unlimited — each success logs a new `Generacion` row.

3. **Post-closure editing**: NOT locked in this slice — the wizard stays editable after `TERMINADO`. Freezing values on closure is out of scope, deferred as future work if needed.
4. **Generation failure UX**: on `ProblemaDeGeneracion`, redirect to `revision` (S-09) with a flash/error message, consistent with the rest of the wizard's navigation — never a standalone error page.

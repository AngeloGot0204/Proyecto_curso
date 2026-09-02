# Design: Move Report Closure (VistoBueno) From Revision To Participantes

> **Superseded**: this document's intent (drop closure from `revision.html`,
> keep it only on `participantes.html`) was never carried out that way in
> practice — closure ended up duplicated on both screens. The resolved
> state keeps "Marcar como terminado" and "Eliminar reporte" on
> `revision.html` / `mis_reportes.html` / `eliminar_reporte.html` only;
> `participantes.html` renders neither. Decisions below describing the
> closure form living on `participantes.html` no longer apply — see the
> delta spec's "Participants and History View" requirement for the current
> contract.

## Technical Approach

Screen-ownership correction, no model/URL changes. `reportes_cerrar`
(`POST /reportes/<id>/cerrar/`) keeps its URL, decorators, creator-only
`get_object_or_404(..., creador=request.user)` scoping and idempotent
`get_or_create` body; only its `redirect(...)` targets change. The closure
`<form>` moves from `revision.html`'s `.hoja__pie` into `participantes.html`,
gated by the invite-form pattern. `participantes` gains `resultado` in its
context by calling the already-imported `validar_reporte`, exactly as
`revision` does.

## Architecture Decisions

### Decision: Two distinct gating mechanisms, not one

| Gate | Mechanism | Rationale |
|---|---|---|
| Non-creator | `{% if reporte.creador_id == request.user.id %}` wrapper | Reuses the existing invite-form pattern in `participantes.html:21`; hides the form entirely, matching spec "no closure form at all" |
| Ineligible creator (`puede_generar` False) | `disabled` attribute + always-rendered `.acciones__razon` sibling | Preserves retrofit-visual-design2 D6 verbatim: `components.css:199` `.acciones__primario:disabled ~ .acciones__razon{display:block}` is a pure-CSS reveal; adding a template conditional here would break D6 |

**Rejected**: a single `{% if %}` for both. It would delete the D6 CSS
contract and lose the "Corregí N errores primero" text the spec requires.

### Decision: Button label becomes "Marcar como terminado"

**Choice**: rename from "Cerrar reporte" (revision's label) to the S-10 label
the `colaboracion-reporte` scenario asserts.
**Alternatives**: keep "Cerrar reporte" — rejected; the delta spec names the
new label explicitly. The ineligibility text stays verbatim.

### Decision: Both redirect branches leave `reportes_revision`

**Choice**: success → `reportes_mis`; ineligible-rejection → `reportes_participantes`.
**Alternatives**: change only the success branch (proposal's literal wording)
— rejected: a rejected close would bounce the user to a screen that no longer
owns closure, a dead end. Redirecting the error branch to the originating
screen keeps the flash message next to the control that produced it.

### Decision: `participantes` computes `resultado` unconditionally

**Choice**: call `validar_reporte(reporte)` for every request, creator or not.
**Alternatives**: compute only for the creator — rejected; a conditional adds
a branch to test for negligible cost, and `revision` already runs it per GET.

No ADR deviation: ADR-0006 (collaboration/permissions) is honoured —
`cerrar_reporte` stays creator-only and does **not** adopt `_reporte_accesible`.

## Data Flow

    Creator on S-10 ──POST reportes_cerrar──→ cerrar_reporte
                                                  │
                        get_object_or_404(creador=user) ──✗──→ 404
                                                  │
                          validar_reporte().puede_generar ──✗──→ flash error
                                                  │                    │
                                            VistoBueno + estado        ↓
                                              = TERMINADO      reportes_participantes
                                                  │
                                                  ↓
                                            reportes_mis (?estado=terminado exists)

## File Changes

| File | Action | Description |
|---|---|---|
| `reportes/templates/reportes/participantes.html` | Modify | Add creator-only closure `<form>` + `.acciones__razon` span |
| `reportes/templates/reportes/revision.html` | Modify | Delete closure form (l.53-59); relabel existing `Participantes` link (l.63) to "Cerrar en Participantes →" |
| `reportes/views.py::participantes` | Modify | Add `resultado: validar_reporte(reporte)` to context; update docstring |
| `reportes/views.py::cerrar_reporte` | Modify | Redirects → `reportes_mis` / `reportes_participantes`; docstring says `participantes.html` |
| `reportes/views.py` module docstring | Modify | Closure ownership sentence |
| `static/css/components.css:184-188` | Modify | Comment says `revision.html`; retarget to `participantes.html` (comment only) |
| `reportes/tests/test_views.py` | Modify | Migrate 5 revision-coupled tests (see below) |
| `openspec/specs/{cierre-reporte,colaboracion-reporte}/spec.md` | Modify | Applied at archive time |

## Interfaces / Contracts

```python
# participantes context gains one key; nothing else changes.
contexto = {"reporte": ..., "participaciones": ..., "cambios": ...,
            "resultado": validar_reporte(reporte)}
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Integration | Success redirect is `reportes_mis` | Update `test_cerrar_reporte_creador_exitoso:849` |
| Integration | Ineligible redirect is `reportes_participantes` | Extend `test_cerrar_reporte_rechazado_si_no_puede_generar` |
| Template | Creator sees form; invited participant sees none | New participantes tests mirroring `test_get_revision_no_creador_no_ve_boton_cerrar` |
| Template | `disabled` + `.acciones__razon` + "Corregí N errores primero" | **Migrate** D6 tests to participantes |
| Template | `revision.html` has no closure form, has the link, keeps Generar | New + existing `test_get_revision_con_visto_bueno_muestra_form_generar` |

**Blocking risk**: five tests assert `"disabled" in/not in` the *revision*
response (`:569`, `:598`, `:625`, `:663`, `:691`). That attribute exists on
revision **only** via the Cerrar button. Removing it silently breaks the
`"disabled" in"` assertions and makes the `not in` ones vacuous. All five must
move to `reportes_participantes` in the same work unit, not later.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Redirect targets are
`reverse()`-resolved named URLs with no user-supplied input.

## Migration / Rollout

No migration required. No model, URL, or schema change; pure view/template/test edit.

## Open Questions

- [ ] Ineligible-branch redirect to `reportes_participantes` extends the
      proposal, which scoped only the success redirect. Confirm before apply.
- [ ] Closure form still renders for the creator after `estado == TERMINADO`
      (current revision parity, idempotent POST). Deliberately unchanged;
      confirm this is intended on S-10.

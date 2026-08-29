# Proposal: Colaboración por invitación y edición abierta

## Proposal question round

The four open decisions flagged in `exploration.md` were confirmed by the user before this proposal was drafted (no further round needed):

1. `generar` narrows to creator-or-invited-participant (reverses #7's deferral).
2. Online simultaneous-edit lock ("en edición por X", 10-min timeout) is deferred — out of scope for #8.
3. `ParticipacionEnReporte` fields: `reporte` FK, `usuario` FK, `fecha_invitacion`, `unique_together(reporte, usuario)` — no role field.
4. Creator gets no `ParticipacionEnReporte` row; "is creator" is checked independently, mirroring `cerrar_reporte`.

## Intent

Today only the creator of a `Reporte` can see or edit it; `generar` is open to any authenticated user. ADR-0006 requires invitation-only access (creator + explicitly invited users) with fully open editing among participants, made acceptable by a mandatory per-field audit trail. Backlog #8 closes this gap: it introduces invitations, widens access checks accordingly, and adds the `CambioDeValor` history that is the trust mechanism behind open editing.

## Scope

### In Scope
- `ParticipacionEnReporte` model: FK `reporte`, FK `usuario`, `fecha_invitacion`, `unique_together(reporte, usuario)`. No role/responsibility field. No row for the creator.
- `CambioDeValor` model: FK `reporte`, `identificador_de_campo`, `valor_anterior`, FK `autor`, `fecha`. Written inside `guardar_valor` on every actual write (not on no-op deletes/no-change).
- FIFO-30 retention per `Reporte` (not per field): on the 31st row for a given report, delete that report's single oldest row, inside `transaction.atomic()` alongside the value write.
- Widen `paso` and `revision` view access from creator-only to creator-OR-invited-participant.
- Narrow `generar` from any-authenticated-user to creator-OR-invited-participant.
- `cerrar_reporte` unchanged (creator-only).
- New invite action: creator-only POST, username field, exact-match lookup on `Usuario.username`, idempotent (already-invited is a no-op), flash message on success or "user not found."
- New participants/history view (S-10-equivalent): invited-users list, creator shown as a label (not a participation row), "Compartir con…" form, `CambioDeValor` history most-recent-first. May extend `revision.html` or be a new template.
- Tests first (strict TDD) for models, the `guardar_valor` refactor, and view access-control changes.

### Out of Scope
- Online simultaneous-edit lock ("en edición por X", 10-min timeout) — deferred.
- User search/autocomplete for invitation — exact username only.
- Admin override for stuck/inaccessible reports.
- Email/notification infrastructure — in-app list only.

## Capabilities

### New Capabilities
- `colaboracion-reporte`: invitation model, invite action, participants list, and change-history view (S-10-equivalent).

### Modified Capabilities
- `reportes-modelo`: adds `ParticipacionEnReporte` and `CambioDeValor` models.
- `wizard-captura`: `paso`/`revision` access checks widen to creator-or-participant; `guardar_valor` gains audit-trail write + FIFO-30 trim.
- `generacion-documento`: `generar` access narrows from any-authenticated-user to creator-or-participant.

## Approach

Minimal invite-list model (exploration Approach 1): plain join table for participation, exact-username invite, widened access checks reusing the existing creator-check pattern, `CambioDeValor` write co-located in `guardar_valor`'s existing transaction, zero new notification infra. This is the smallest slice that literally satisfies ADR-0006 and the backlog ACs.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/models.py` | Modified | Add `ParticipacionEnReporte`, `CambioDeValor` |
| `reportes/valores.py::guardar_valor` | Modified | Read-before-write, `CambioDeValor` insert, FIFO-30 trim, `transaction.atomic()` |
| `reportes/views.py` | Modified | Widen `paso`/`revision`, narrow `generar`, add invite + participants/history views |
| `reportes/urls.py` | Modified | New routes for invite and participants/history views |
| New template | New | S-10-equivalent (participants, invite form, history) |
| `reportes/migrations/` | New | New migration for both models |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FIFO-30 trim needs a `pk__in` subquery (Django forbids `.delete()` on a sliced queryset) on a write-heavy path | Med | Boundary tests at 30th/31st write; isolate trim in one helper |
| `guardar_valor`'s transaction shape changes (adds read-before-write) | Low | Wrap value write + audit insert + trim in one `transaction.atomic()`, tests first |
| Narrowing `generar` reverses #7's explicit deferral | Low | Confirmed by user in this proposal round |
| No existing S-10 template — new UI surface, not wiring a dead button | Med | Keep template minimal, reuse `revision.html` patterns |

## Rollback Plan

Revert the migration (`reportes/migrations/000X_...`) and the associated view/template/URL changes; `paso`/`revision`/`generar` access checks revert to creator-only/any-authenticated via git revert of `views.py`. No destructive data migration is involved — new tables only, so rollback is a clean model/code revert.

## Dependencies

- None external. Builds on `Reporte`, `Usuario`, and `ValorDeReporte` from prior changes (#4–#7).

## Success Criteria

- [ ] Creator can invite a user by username; invited user then sees and can access the report.
- [ ] A non-invited user gets 404 on `paso`, `revision`, and `generar`, including direct-URL access.
- [ ] An invited (non-creator) participant can edit any section, matching creator's access.
- [ ] Every actual `guardar_valor` write creates a `CambioDeValor` row with author, field, previous value, timestamp.
- [ ] A report never holds more than 30 `CambioDeValor` rows (FIFO-30 verified at the 31st write boundary).
- [ ] Participants/history view lists invited users, the creator, and change history most-recent-first.

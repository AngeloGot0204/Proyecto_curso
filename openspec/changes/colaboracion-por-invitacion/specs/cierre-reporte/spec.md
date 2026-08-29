# Delta for cierre-reporte

## ADDED Requirements

### Requirement: Cerrar Reporte Access Is Unaffected By Invitations

The introduction of `ParticipacionEnReporte` MUST NOT widen `cerrar_reporte` access: it remains a POST-only view restricted to the `Reporte`'s creator only, unaffected by invitation status. This requirement makes explicit that `cerrar_reporte`'s existing creator-only check (see "Creator-Only Closure" below) does not change as part of the collaboration-by-invitation feature.

#### Scenario: Invited non-creator participant cannot close

- GIVEN a `Reporte` created by user A with user B invited via `ParticipacionEnReporte`
- WHEN user B (invited, not creator) POSTs to `cerrar_reporte`
- THEN the response is 404 and no `VistoBueno` row is created

### Requirement: Revision View Access Widens With Invitations

The `revision` view, which renders the closure/review screen, MUST widen its access check from creator-only to creator-OR-invited-participant, following the same "Participant Access Required" rule defined in the `wizard-captura` capability's delta for `paso`.

#### Scenario: Invited participant views revision

- GIVEN a `Reporte` created by user A with user B invited via `ParticipacionEnReporte`
- WHEN user B requests `revision` for that report
- THEN the response is 200

#### Scenario: Non-invited user is denied revision access

- GIVEN a `Reporte` created by user A with no invitation for user C
- WHEN user C (authenticated, not creator, not invited) requests `revision` for that report
- THEN the response is 404

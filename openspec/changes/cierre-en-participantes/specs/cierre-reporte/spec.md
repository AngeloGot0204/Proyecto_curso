# Delta for Cierre Reporte

## MODIFIED Requirements

### Requirement: Creator-Only Closure

The system MUST expose a POST-only `cerrar_reporte` view that only the report's creator may invoke, mirroring the creator-scoping pattern used by `paso` (`get_object_or_404(..., creador=request.user)`).
(Previously: successful closure redirected to `revision`.)

#### Scenario: Non-creator attempts closure

- GIVEN a `Reporte` created by user A
- WHEN user B (authenticated, not the creator) POSTs to `cerrar_reporte` for that report
- THEN the response is 404
- AND no `VistoBueno` row is created

#### Scenario: Creator closes an eligible report

- GIVEN a `Reporte` created by user A where `puede_generar` is True
- WHEN user A POSTs to `cerrar_reporte`
- THEN a `VistoBueno` is created, `estado` becomes `TERMINADO`, and the response redirects to `reportes_mis` ("Mis reportes")

### Requirement: Server-Side Eligibility Re-Check

The system MUST re-validate `puede_generar` server-side inside `cerrar_reporte` before creating a `VistoBueno`, independent of any client-side gating in `participantes.html`.
(Previously: independent of client-side gating in `revision.html`.)

#### Scenario: Closure rejected when ineligible

- GIVEN a `Reporte` created by user A where `puede_generar` is False
- WHEN user A POSTs to `cerrar_reporte`
- THEN the request is rejected (no `VistoBueno` created, `estado` unchanged)

### Requirement: Cerrar Reporte Access Is Unaffected By Invitations

The introduction of `ParticipacionEnReporte` MUST NOT widen `cerrar_reporte` access: it remains a POST-only view restricted to the `Reporte`'s creator only, unaffected by invitation status. This requirement makes explicit that `cerrar_reporte`'s existing creator-only check (see "Creator-Only Closure" above) does not change as part of the collaboration-by-invitation feature.

#### Scenario: Invited non-creator participant cannot close

- GIVEN a `Reporte` created by user A with user B invited via `ParticipacionEnReporte`
- WHEN user B (invited, not creator) POSTs to `cerrar_reporte`
- THEN the response is 404 and no `VistoBueno` row is created

### Requirement: Revision View Access Widens With Invitations

The `revision` view, which renders validation/document-generation status and links to the participants/closure screen, MUST widen its access check from creator-only to creator-OR-invited-participant, following the same "Participant Access Required" rule defined in the `wizard-captura` capability's delta for `paso`. `revision` MUST NOT create a `VistoBueno`; closure is owned by `participantes`.
(Previously: framed `revision` as "the closure/review screen" that performs closure.)

#### Scenario: Invited participant views revision

- GIVEN a `Reporte` created by user A with user B invited via `ParticipacionEnReporte`
- WHEN user B requests `revision` for that report
- THEN the response is 200

#### Scenario: Non-invited user is denied revision access

- GIVEN a `Reporte` created by user A with no invitation for user C
- WHEN user C (authenticated, not creator, not invited) requests `revision` for that report
- THEN the response is 404

#### Scenario: Revision links to Participantes for closure

- GIVEN a `Reporte` created by user A
- WHEN user A or an invited participant requests `revision`
- THEN the page renders a "Cerrar en Participantes →" link pointing to `reportes_participantes`
- AND the page renders no closure form and creates no `VistoBueno`

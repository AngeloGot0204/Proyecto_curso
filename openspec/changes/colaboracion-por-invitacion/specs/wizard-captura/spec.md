# Delta for wizard-captura

## ADDED Requirements

### Requirement: Participant Access Required

The system MUST allow access to any wizard `paso` view only to the `Reporte`'s creator or a user with a `ParticipacionEnReporte` row for that report. Any other authenticated user MUST receive a 404, matching the existing creator-only 404 pattern (no information disclosure via a 403 or redirect).

#### Scenario: Invited participant accesses a step

- GIVEN a `Reporte` created by user A with user B invited via `ParticipacionEnReporte`
- WHEN user B requests any `paso` URL for that report
- THEN the response is 200 and the step renders normally

#### Scenario: Non-invited authenticated user is denied

- GIVEN a `Reporte` created by user A with no invitation for user C
- WHEN user C (authenticated, not creator, not invited) requests any `paso` URL for that report, including via a direct URL
- THEN the response is 404

### Requirement: Value Writes Recorded to CambioDeValor

Every actual value write performed by `paso`'s POST handler through `guardar_valor` MUST create a `CambioDeValor` row per the `colaboracion-reporte` capability's FIFO-30 requirement, attributing `autor` to the submitting user (creator or invited participant).

#### Scenario: Participant edit is attributed correctly

- GIVEN an invited participant B editing a field on a `Reporte` created by A
- WHEN B submits a new value that differs from the stored one
- THEN the resulting `CambioDeValor` row has `autor=B` and `valor_anterior` equal to the value that was stored before this write

## MODIFIED Requirements

### Requirement: Authentication required

The system MUST block unauthenticated access to any wizard step, consistent with the existing `@login_required` convention. In addition to authentication, access is scoped to the `Reporte`'s creator or an invited participant, per the "Participant Access Required" requirement above.

(Previously: only `@login_required` was enforced; view-level scoping was creator-only implicitly, this requirement now explicitly cross-references the widened creator-or-participant check.)

#### Scenario: Unauthenticated request is redirected

- GIVEN a user who is not authenticated
- WHEN they request any wizard step URL
- THEN the system MUST redirect them to the login flow instead of rendering the step

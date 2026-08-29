# Delta for generacion-documento

## MODIFIED Requirements

### Requirement: Creator or Invited Participant May Generate

The system MUST expose `generar` as a POST-only, `@login_required` view restricted to the `Reporte`'s creator or a user with a `ParticipacionEnReporte` row for that report. Any other authenticated user MUST receive a 404 instead of generating a document.

This requirement supersedes and replaces the prior "Any Authenticated User May Generate" requirement in this spec, which allowed any authenticated user to generate regardless of creator/invitation status.

(Previously: "Any Authenticated User May Generate" — `generar` had no creator/participant restriction; any authenticated user could generate a document for a closed report.)

#### Scenario: Creator generates successfully

- GIVEN a `Reporte` created by user A, closed (has `VistoBueno`), `puede_generar` True
- WHEN user A POSTs to `generar`
- THEN generation succeeds, a `Generacion` row is created with `usuario=A`, and the `.xlsx` is streamed to A

#### Scenario: Invited participant generates successfully

- GIVEN a `Reporte` created by user A, closed (has `VistoBueno`), `puede_generar` True, with user B invited via `ParticipacionEnReporte`
- WHEN user B POSTs to `generar`
- THEN generation succeeds, a `Generacion` row is created with `usuario=B`, and the `.xlsx` is streamed to B

#### Scenario: Non-participant authenticated user is denied

- GIVEN a `Reporte` created by user A, closed (has `VistoBueno`), `puede_generar` True, with no invitation for user C
- WHEN user C (authenticated, not creator, not invited) POSTs to `generar`
- THEN the response is 404, no `.xlsx` is streamed, and no `Generacion` row is created

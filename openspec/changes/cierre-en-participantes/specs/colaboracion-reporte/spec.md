# Delta for Colaboracion Reporte

## MODIFIED Requirements

### Requirement: Participants and History View

The system MUST expose a view listing all invited users plus the creator (shown as a label, not a participation row), an invite form, and the `Reporte`'s `CambioDeValor` history ordered most-recent-first. This view MUST be accessible to the creator and to any invited participant.

The report closure action ("Marcar como terminado") stays exclusively on `revision.html`, submitting to `cerrar_reporte` — the participants/history view does not render a closure control.
(Superseded: this requirement briefly also gave `participantes` its own copy of the closure form; removed to keep the action in one place only.)

#### Scenario: View lists participants and creator label

- GIVEN a `Reporte` created by user A with user B invited
- WHEN user A or user B requests the participants/history view
- THEN the response lists B as an invited user and shows A labeled as creator

#### Scenario: History renders most-recent-first

- GIVEN a `Reporte` with multiple `CambioDeValor` rows across different `fecha` values
- WHEN a participant requests the participants/history view
- THEN the rendered history list is ordered by `fecha` descending

#### Scenario: Participants view renders no closure control

- GIVEN a `Reporte` created by user A with user B invited
- WHEN user A or user B requests the participants view
- THEN the response includes no "Marcar como terminado" closure form, regardless of role

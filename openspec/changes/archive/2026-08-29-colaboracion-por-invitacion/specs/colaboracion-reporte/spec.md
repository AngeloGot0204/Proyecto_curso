# Colaboracion Reporte Specification

## Purpose

Let a `Reporte`'s creator invite other users by exact username to gain full read/write access to that report, and record every actual value write as an immutable, FIFO-bounded audit trail visible to all participants.

## Requirements

### Requirement: ParticipacionEnReporte Model

The system MUST provide a `ParticipacionEnReporte` model with a foreign key `reporte` to `Reporte`, a foreign key `usuario` to `settings.AUTH_USER_MODEL`, an auto-populated `fecha_invitacion` timestamp, and `unique_together(reporte, usuario)`. The model MUST NOT include a role/responsibility field. The creator MUST NOT receive a `ParticipacionEnReporte` row; "is creator" is checked independently of participation, mirroring the `cerrar_reporte` creator check.

#### Scenario: Participation row created on invite

- GIVEN a `Reporte` created by user A
- WHEN user A invites user B by exact username
- THEN one `ParticipacionEnReporte` row is created with `reporte=that report`, `usuario=B`, and `fecha_invitacion` populated

#### Scenario: Creator has no participation row

- GIVEN a `Reporte` created by user A with no invitations
- WHEN the system checks whether A has access
- THEN access is granted via the creator check, not via any `ParticipacionEnReporte` row for A

### Requirement: CambioDeValor Model and FIFO-30 Retention

The system MUST provide a `CambioDeValor` model with a foreign key `reporte` to `Reporte`, `identificador_de_campo`, `valor_anterior`, a foreign key `autor` to `settings.AUTH_USER_MODEL`, and an auto-populated `fecha` timestamp. A row MUST be written on every actual value write inside `guardar_valor` (not on no-op deletes or unchanged values). Retention is FIFO-30 scoped per `Reporte` across all fields combined: writing a report's 31st `CambioDeValor` row MUST delete that report's single oldest row, inside the same `transaction.atomic()` as the value write.

#### Scenario: Value write creates history row

- GIVEN a `Reporte` and a field with no prior `CambioDeValor` entries
- WHEN a participant submits a new value for that field through the wizard
- THEN one `CambioDeValor` row is created with `autor` set to that participant, the field identifier, and current `fecha`

#### Scenario: First-time edit records empty valor_anterior

- GIVEN a field with no prior stored value
- WHEN a user writes the first value for that field
- THEN the created `CambioDeValor` row MUST still be recorded, with `valor_anterior` empty/null

#### Scenario: No-op write does not create history

- GIVEN a field whose stored value already equals the submitted value
- WHEN the same value is resubmitted
- THEN no new `CambioDeValor` row is created

#### Scenario: 31st write trims the oldest row

- GIVEN a `Reporte` that already has 30 `CambioDeValor` rows
- WHEN one more actual value write occurs for that report (any field)
- THEN a new `CambioDeValor` row is created, the single oldest row for that report is deleted, and exactly 30 rows remain

#### Scenario: FIFO-30 is scoped per Reporte, not per field

- GIVEN a `Reporte` with 30 `CambioDeValor` rows spread across multiple fields
- WHEN a write happens on a field that individually has fewer than 30 prior rows
- THEN the trim still evaluates the report's total row count and deletes the report's oldest row if the total exceeds 30

### Requirement: Creator-Only Invite Action

The system MUST expose a POST-only, `@login_required`, creator-only invite action taking a username field. It MUST resolve `Usuario.username` by exact match, be idempotent when the user is already invited, and set a flash message on success or on "user not found."

#### Scenario: Successful invite

- GIVEN a `Reporte` created by user A and an existing user B not yet invited
- WHEN user A POSTs the invite action with B's exact username
- THEN a `ParticipacionEnReporte` row for B is created and a success flash message is shown

#### Scenario: Inviting an already-invited user is idempotent

- GIVEN user B already has a `ParticipacionEnReporte` row for a `Reporte`
- WHEN the creator invites B again by the same username
- THEN no error occurs, no duplicate row is created, and exactly one `ParticipacionEnReporte` row for (that report, B) exists

#### Scenario: Inviting a nonexistent username

- GIVEN no user exists with username "nadie"
- WHEN the creator POSTs the invite action with username "nadie"
- THEN no `ParticipacionEnReporte` row is created and a "user not found" flash error message is shown

#### Scenario: Non-creator cannot invite

- GIVEN a `Reporte` created by user A
- WHEN a non-creator, non-participant authenticated user B POSTs the invite action for that report
- THEN the response is 404 and no `ParticipacionEnReporte` row is created

### Requirement: Participants and History View

The system MUST expose a view listing all invited users plus the creator (shown as a label, not a participation row), an invite form, and the `Reporte`'s `CambioDeValor` history ordered most-recent-first. This view MUST be accessible to the creator and to any invited participant.

#### Scenario: View lists participants and creator label

- GIVEN a `Reporte` created by user A with user B invited
- WHEN user A or user B requests the participants/history view
- THEN the response lists B as an invited user and shows A labeled as creator

#### Scenario: History renders most-recent-first

- GIVEN a `Reporte` with multiple `CambioDeValor` rows across different `fecha` values
- WHEN a participant requests the participants/history view
- THEN the rendered history list is ordered by `fecha` descending

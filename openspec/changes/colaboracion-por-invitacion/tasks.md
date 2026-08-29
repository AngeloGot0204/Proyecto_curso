# Tasks: Colaboración por invitación y edición abierta

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~550–600 (migration ~60, permisos.py ~15, views.py ~100, urls.py ~10, valores.py ~50, participantes.html ~60, revision.html ~5, conftest.py ~40, test_permisos.py ~40, test_valores.py ~80, test_views.py ~120) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (ask user: stacked-to-main vs feature-branch-chain) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Migration 0004 + `permisos.py::tiene_acceso` | PR 1 | `pytest reportes/tests/test_permisos.py -q` | `pytest reportes/tests/test_permisos.py -v` (creator/participant/stranger/anonymous cases) | Revert migration + delete `permisos.py`/`test_permisos.py`; no other file depends yet |
| 2 | `guardar_valor` refactor: audit insert + FIFO-30 trim | PR 2 | `pytest reportes/tests/test_valores.py -q` | `pytest reportes/tests/test_valores.py -v -k "cambio or fifo or historial"` | Revert `valores.py` diff; `CambioDeValor` table stays unused but harmless |
| 3 | Widen `paso`/`revision`, narrow `generar` via `_reporte_accesible` | PR 3 | `pytest reportes/tests/test_views.py -q -k "paso or revision or generar"` | `pytest reportes/tests/test_views.py -v -k "acceso or participante or no_creador"` | Revert `views.py` access-check hunks only; models/valores unaffected |
| 4 | Invite + participantes view/template/urls | PR 4 | `pytest reportes/tests/test_views.py -q -k "invitar or participantes"` | `pytest reportes/tests/test_views.py -v -k "invitar or participantes"` (full click-through: invite → 200 access → history render) | Revert new view/template/url additions; PR 1–3 stay functional standalone |

## Phase 1: Foundation — Models and Permission Predicate

- [x] 1.1 (RED) Write `reportes/tests/test_permisos.py`: `tiene_acceso` returns True for creator (no participation row), True for invited participant, False for stranger, False for unauthenticated user — spec "ParticipacionEnReporte Model" scenarios.
- [x] 1.2 Add `ParticipacionEnReporte` model to `reportes/models.py`: FK `reporte` (CASCADE, related_name `participaciones`), FK `usuario` (PROTECT, related_name `participaciones`), `fecha_invitacion` (auto_now_add), `Meta.constraints = [UniqueConstraint(fields=["reporte","usuario"], name="participacion_unica_por_reporte_y_usuario")]`.
- [x] 1.3 Add `CambioDeValor` model to `reportes/models.py`: FK `reporte` (CASCADE, related_name `cambios`), `identificador_de_campo` CharField(200), `valor_anterior` TextField(blank=True, null=True), FK `autor` (PROTECT, related_name `cambios_de_valor`), `fecha` (auto_now_add).
- [x] 1.4 Fix `Generacion` model docstring in `reportes/models.py` ("any authenticated user" → participant-scoped), per design File Changes.
- [x] 1.5 Generate `reportes/migrations/0004_participacion_cambiodevalor.py` (2× `CreateModel` + `AddConstraint`; deps on `0003_vistobueno_generacion` + `swappable_dependency(AUTH_USER_MODEL)`).
- [x] 1.6 (GREEN) Create `reportes/permisos.py` with `tiene_acceso(reporte, usuario) -> bool` per design D1; run 1.1's tests, confirm pass.
- [x] 1.7 (REFACTOR) Confirm no HTTP imports leak into `permisos.py` (pure predicate, mirrors `valores.py`/`validacion.py`).
- [x] 1.8 Add `participacion_factory(db, usuario_factory)` fixture to `reportes/tests/conftest.py` per design fixture strategy.

## Phase 2: guardar_valor Refactor — Audit Trail + FIFO-30

- [ ] 2.1 (RED) Add to `reportes/tests/test_valores.py`: first write on empty field → `CambioDeValor` row created with `valor_anterior is None` (spec "First-time edit records empty valor_anterior").
- [ ] 2.2 (RED) Add: overwrite of existing value → `CambioDeValor.valor_anterior` equals the prior stored value, `autor` set (spec "Value write creates history row").
- [ ] 2.3 (RED) Add: no-op write (same value resubmitted) → zero new `CambioDeValor` rows created (spec "No-op write does not create history"; design D4 load-bearing guard).
- [ ] 2.4 (RED) Add: delete-of-existing value (empty submit over a stored value) → history row still written.
- [ ] 2.5 (RED) Add: no-op delete (empty submit, no existing row) → zero rows created.
- [ ] 2.6 (RED) Add boundary test: 30 sequential writes on a report → exactly 30 `CambioDeValor` rows exist.
- [ ] 2.7 (RED) Add boundary test: 31st write on the same report → 30 rows remain, the single oldest row (by `-fecha, -id`) is gone, the newest row is present (spec "31st write trims the oldest row").
- [ ] 2.8 (RED) Add: FIFO-30 spans multiple fields on one report — 30 rows across several `identificador_de_campo` values, a write on a field with fewer prior rows still trims the report's oldest row (spec "FIFO-30 is scoped per Reporte, not per field").
- [ ] 2.9 Add `cambios_factory(reporte, n, autor)` fixture to `conftest.py` (back-dates `fecha` via `queryset.update()` per design fixture strategy).
- [ ] 2.10 (GREEN) Refactor `guardar_valor` in `reportes/valores.py`: wrap in `transaction.atomic()`, read `ValorDeReporte` before write to capture `valor_anterior`, keep existing empty-delete/non-empty-upsert behavior, insert `CambioDeValor` only on actual change, call `_recortar_historial(reporte)`.
- [ ] 2.11 (GREEN) Implement `_recortar_historial(reporte)` in `reportes/valores.py` per design D5: `order_by("-fecha", "-id")`, `values_list("pk", flat=True)[30:]`, materialize via `list(...)`, `pk__in` delete.
- [ ] 2.12 Run 2.1–2.8 tests, confirm all pass.
- [ ] 2.13 (REFACTOR) Confirm `guardar_valor`'s public signature is unchanged (`reporte, identificador_de_campo, valor, autor`) so existing direct callers in `test_valores.py` need no wrapper changes.

## Phase 3: Widen paso/revision, Narrow generar

- [ ] 3.1 (RED) Add to `reportes/tests/test_views.py`: invited participant B requests any `paso` URL → 200 (spec wizard-captura "Invited participant accesses a step").
- [ ] 3.2 (RED) Add: non-invited authenticated user C requests `paso` via direct URL → 404 (spec wizard-captura "Non-invited authenticated user is denied").
- [ ] 3.3 (RED) Add: invited participant B requests `revision` → 200 (spec cierre-reporte "Invited participant views revision").
- [ ] 3.4 (RED) Add: non-invited user C requests `revision` → 404 (spec cierre-reporte "Non-invited user is denied revision access").
- [ ] 3.5 (RED) Add `test_generar_participante_invitado_es_exitoso`: invited participant B POSTs `generar` → 200, `Generacion.usuario == B` (replaces half of `test_generar_no_creador_tambien_puede_generar` per design's identified reversal).
- [ ] 3.6 (RED) Add `test_generar_no_participante_devuelve_404`: non-participant authenticated user C POSTs `generar` → 404, no `Generacion` row created (spec generacion-documento "Non-participant authenticated user is denied").
- [ ] 3.7 Remove/rewrite `test_generar_no_creador_tambien_puede_generar` in `reportes/tests/test_views.py`, replaced by 3.5 + 3.6 per design's "Exactly one test asserts #7's reversal" analysis.
- [ ] 3.8 (RED) Add regression assertion confirming `test_paso_reporte_de_otro_usuario_da_404`, `test_get_revision_reporte_de_otro_usuario_da_404` still pass unchanged (stranger stays neither creator nor participant).
- [ ] 3.9 (RED) Add `test_cerrar_reporte_participante_invitado_devuelve_404` in `reportes/tests/test_views.py`: invited non-creator B POSTs `cerrar_reporte` → 404, no `VistoBueno` created (spec cierre-reporte "Invited non-creator participant cannot close").
- [ ] 3.10 (GREEN) Add `_reporte_accesible(reporte_id, usuario)` shim to `reportes/views.py` per design D1 (fetch via `get_object_or_404`, then `tiene_acceso` check, else raise `Http404`).
- [ ] 3.11 (GREEN) Switch `paso` view in `reportes/views.py` to use `_reporte_accesible`.
- [ ] 3.12 (GREEN) Switch `revision` view in `reportes/views.py` to use `_reporte_accesible`.
- [ ] 3.13 (GREEN) Switch `generar` view in `reportes/views.py` to use `_reporte_accesible` (narrows from any-authenticated-user).
- [ ] 3.14 Confirm `cerrar_reporte` keeps its strict `get_object_or_404(Reporte, pk=…, creador=request.user)` unchanged (does not use `_reporte_accesible`).
- [ ] 3.15 Update `reportes/views.py` module docstring (currently states creator-only D9) to reflect creator-or-participant access.
- [ ] 3.16 Add `sesion_de_invitado` fixture (local to `test_views.py`, mirrors `sesion_de_creador`) — logged-in invited non-creator client + reporte.
- [ ] 3.17 Run all Phase 3 tests, confirm all pass.

## Phase 4: Invite Action and Participantes View

- [ ] 4.1 (RED) Add `test_invitar_exitoso`: creator A POSTs invite with B's exact username → `ParticipacionEnReporte` row created, success flash message (spec "Successful invite").
- [ ] 4.2 (RED) Add `test_invitar_idempotente`: creator A invites already-invited B again → no error, exactly one `ParticipacionEnReporte` row exists (spec "Inviting an already-invited user is idempotent").
- [ ] 4.3 (RED) Add `test_invitar_usuario_inexistente`: creator A POSTs username "nadie" → no row created, "user not found" flash error (spec "Inviting a nonexistent username").
- [ ] 4.4 (RED) Add `test_invitar_no_creador_devuelve_404`: non-creator, non-participant B POSTs invite → 404, no row created (spec "Non-creator cannot invite").
- [ ] 4.5 (RED) Add `test_invitar_a_si_mismo_rechazado`: creator A invites their own username → error flash message, no `ParticipacionEnReporte` row for A created (design's self-invite rejection, protects "creator has no participation row").
- [ ] 4.6 (RED) Add `test_participantes_lista_invitados_y_creador`: creator A or invited B requests participantes view → response lists B as invited, shows A labeled as creator (spec "View lists participants and creator label").
- [ ] 4.7 (RED) Add `test_participantes_historial_mas_reciente_primero`: report with multiple `CambioDeValor` rows across different `fecha` → rendered history ordered descending (spec "History renders most-recent-first").
- [ ] 4.8 (RED) Add `test_participantes_no_participante_devuelve_404`: non-creator, non-participant user → 404 on participantes view.
- [ ] 4.9 (GREEN) Add `invitar` view to `reportes/views.py` per design's shown shape: `@login_required`, `@require_POST`, creator-only fetch, exact `username` lookup, self-invite rejection, `get_or_create` idempotency, `messages` framework, redirect to `reportes_participantes`.
- [ ] 4.10 (GREEN) Add `participantes` view to `reportes/views.py`: uses `_reporte_accesible`, `select_related` `ParticipacionEnReporte.usuario` and `CambioDeValor.autor` ordered `-fecha, -id`.
- [ ] 4.11 (GREEN) Add `reportes_invitar` and `reportes_participantes` URL routes to `reportes/urls.py`.
- [ ] 4.12 (GREEN) Create `reportes/templates/reportes/participantes.html`: creator label, invited-users list, creator-only invite form, `CambioDeValor` history table — new template per design D6 (not an extension of `revision.html`).
- [ ] 4.13 (GREEN) Add plain `<a href="{% url 'reportes_participantes' … %}">` link to `reportes/templates/reportes/revision.html` (no `disabled` substring — preserves `test_get_revision_sin_errores_habilita_generar`).
- [ ] 4.14 Add `reporte_con_participantes_factory` fixture to `conftest.py` (reporte + N invited users, usernames `invitado_0..N-1`).
- [ ] 4.15 Run all Phase 4 tests, confirm all pass.
- [ ] 4.16 (REFACTOR) Confirm `test_get_revision_sin_errores_habilita_generar` still passes unchanged after the `revision.html` link addition.

## Phase 5: Full Suite Verification

- [ ] 5.1 Run full `pytest reportes/` and confirm no regressions across `test_models.py`, `test_valores.py`, `test_views.py`, `test_permisos.py`.
- [ ] 5.2 Confirm `makemigrations --check` is clean (no missing migration for `0004`).
- [ ] 5.3 Confirm no threat-matrix items apply (design states N/A — no routing/shell/subprocess/VCS surface); no additional RED tests owed here.

## Key Learnings

1. Design's D4 no-op guard is load-bearing: without it, `paso`'s per-step full-field POST loop would exhaust the 30-row FIFO budget on unchanged resubmits.
2. `_reporte_accesible` reuses the fetch-then-check-then-404 pattern already established by `iniciar_reporte`/`paso`, avoiding a `MultipleObjectsReturned` risk from a joined `filter(Q(...)|Q(...))` queryset.
3. Exactly one existing test (`test_generar_no_creador_tambien_puede_generar`) captures the #7 reversal and must be split into two named tests, not silently deleted.
4. FIFO-30 trim requires materializing the `pk__in` subquery via `list()` because Django forbids `.delete()` on a sliced queryset and MySQL disallows self-referencing subselects.

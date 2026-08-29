# Verification Report: colaboracion-por-invitacion

**Mode**: Full artifacts (proposal, 4 spec deltas, design, tasks, apply-progress). All 4 chained PRs (21-24) merged to main. Working tree clean.

## Task Completeness

All 5 phases in tasks.md, every checkbox `[x]`, verified against code:
- Phase 1 (models + `permisos.py`) — matches design D1/D2/D3.
- Phase 2 (`guardar_valor` refactor + FIFO-30) — matches design D4/D5.
- Phase 3 (widen `paso`/`revision`, narrow `generar`) — matches design D1.
- Phase 4 (`invitar`/`participantes`) — matches design's invite view shape verbatim.
- Phase 5 (full suite) — reproduced independently: 250/250 pass.

## Spec Compliance Matrix

### colaboracion-reporte (8 scenarios)
| Scenario | Status | Test |
|---|---|---|
| Participation row created on invite | PASS | `test_invitar_exitoso` |
| Creator has no participation row | PASS | `test_tiene_acceso_creador_sin_fila_de_participacion` |
| Value write creates history row | PASS | `test_guardar_valor_sobrescritura_registra_valor_anterior_previo` |
| First-time edit records empty valor_anterior | PASS | `test_guardar_valor_primera_escritura_registra_valor_anterior_none` |
| No-op write does not create history | PASS | `test_guardar_valor_resubmit_mismo_valor_no_crea_historial` |
| 31st write trims the oldest row | PASS | `test_guardar_valor_trigesima_primera_escritura_recorta_la_mas_antigua` |
| FIFO-30 scoped per Reporte, not per field | PASS | `test_guardar_valor_fifo_30_es_por_reporte_no_por_campo` |
| Successful invite | PASS | `test_invitar_exitoso` |
| Inviting an already-invited user is idempotent | PASS | `test_invitar_idempotente` |
| Inviting a nonexistent username | PASS | `test_invitar_usuario_inexistente` |
| Non-creator cannot invite | PASS | `test_invitar_no_creador_devuelve_404` |
| View lists participants and creator label | PASS | `test_participantes_lista_invitados_y_creador` |
| History renders most-recent-first | PASS | `test_participantes_historial_mas_reciente_primero` |

### wizard-captura delta
| Scenario | Status | Test |
|---|---|---|
| Invited participant accesses a step | PASS | `test_paso_participante_invitado_accede` |
| Non-invited authenticated user is denied | PASS | `test_paso_no_invitado_autenticado_da_404` |
| Participant edit is attributed correctly | PASS | covered transitively — `autor` plumbed from `request.user` in `paso`, verified by `guardar_valor` audit tests |
| Unauthenticated request is redirected | PASS | pre-existing `@login_required` coverage, unaffected by this change |

### generacion-documento delta
| Scenario | Status | Test |
|---|---|---|
| Creator generates successfully | PASS | `test_generar_exitoso_streamea_xlsx_con_headers_correctos` (creator client) |
| Invited participant generates successfully | PASS | `test_generar_participante_invitado_es_exitoso` |
| Non-participant authenticated user is denied | PASS | `test_generar_no_participante_devuelve_404` |

Both success and denial paths for the #7 reversal (any-authenticated-user → creator-or-participant) are explicitly tested.

### cierre-reporte delta
| Scenario | Status | Test |
|---|---|---|
| Invited non-creator participant cannot close | PASS | `test_cerrar_reporte_participante_invitado_devuelve_404` — confirms `cerrar_reporte` genuinely stayed creator-only (invited-but-not-creator still 404s) |
| Invited participant views revision | PASS | `test_get_revision_participante_invitado_accede` |
| Non-invited user is denied revision access | PASS | `test_get_revision_no_invitado_da_404` |

## Design Coherence

| Decision | Verified against | Result |
|---|---|---|
| D1 fetch-then-check-then-404 | `views.py::_reporte_accesible` | Matches design's shown code exactly |
| D1 `invitar`/`cerrar_reporte` carve-out (creator-only, no `_reporte_accesible`) | `views.py::invitar`, `cerrar_reporte` | Confirmed — both use strict `get_object_or_404(..., creador=request.user)` |
| D4 no-op guard | `valores.py::guardar_valor` | Confirmed — early return on unchanged resubmit and no-op delete |
| D5 FIFO-30 trim (materialized `pk__in`, per-Reporte scope) | `valores.py::_recortar_historial` | Confirmed — `order_by("-fecha","-id")[30:]` materialized via `list()`, filtered by `reporte=reporte` only (not per-field) |
| Self-invite rejection + idempotent re-invite | `views.py::invitar` | Matches design's exact code block |
| D2 UniqueConstraint deviation (Django 5.2 inlines into CreateModel) | migration 0004 | Documented, cosmetic only, no spec impact |

## Runtime Evidence

- `pytest --reuse-db -q` (full project suite): **250 passed** in 519.80s — reproduced independently in this verify pass.
- `manage.py makemigrations --check --dry-run --skip-checks`: "No changes detected" — clean.
- `git status --short`: clean working tree — no drift between apply-progress.md claims and actual code state.

## Issues

None. CRITICAL: 0, WARNING: 0, SUGGESTION: 0.

## Verdict: PASS

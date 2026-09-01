# Tasks: Move Report Closure (VistoBueno) From Revision To Participantes

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~180-220 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Full closure-ownership move as one cohesive slice | PR 1 | `pytest reportes/tests/test_views.py -k "cerrar or participantes or revision"` | `pytest reportes/tests/test_views.py` | Single-PR `git revert`; no model/URL/migration to unwind |

## Phase 1: RED — Views redirects/context (`reportes/views.py`)

- [x] 1.1 Update `test_cerrar_reporte_creador_exitoso` (:849): assert redirect to `reportes_mis`.
- [x] 1.2 Extend `test_cerrar_reporte_rechazado_si_no_puede_generar` (:823): assert redirect to `reportes_participantes`.
- [x] 1.3 New test: `participantes` context includes `resultado == validar_reporte(reporte)`.
- [x] 1.4 Run and confirm 1.1-1.3 fail.

## Phase 2: GREEN — Views (`reportes/views.py`)

- [x] 2.1 `cerrar_reporte` (:305-321): ineligible branch → `redirect("reportes_participantes", reporte_id=reporte.id)`.
- [x] 2.2 `cerrar_reporte`: success branch → `redirect("reportes_mis")`.
- [x] 2.3 Update `cerrar_reporte` + module docstrings: closure owned by `participantes.html`.
- [x] 2.4 `participantes` (:432-436): add `"resultado": validar_reporte(reporte)` to `contexto`; update docstring.
- [x] 2.5 Confirm 1.1-1.3 GREEN.

## Phase 3: RED — Closure form on Participantes

- [x] 3.1 New test (mirrors `test_get_revision_no_creador_no_ve_boton_cerrar`): creator sees "Marcar como terminado" form on `reportes_participantes`; invited non-creator sees none.
- [x] 3.2 New test (mirrors D6 tripwire): ineligible creator sees `disabled` + `.acciones__razon` + "Corregí N errores primero" on `reportes_participantes`.
- [x] 3.3 New test: eligible creator has no `disabled` on `reportes_participantes`.
- [x] 3.4 New test (mirrors `test_cerrar_reporte_creador_exitoso`): eligible creator submits participantes form → `VistoBueno` created, `estado=TERMINADO`, redirect `reportes_mis`.
- [x] 3.5 Run 3.1-3.4, confirm fail (no form yet).

## Phase 4: GREEN — Closure form (`reportes/templates/reportes/participantes.html`)

- [x] 4.1 Inside `{% if reporte.creador_id == request.user.id %}` (after invite section, :21-33), add closure `<section>` form to `reportes_cerrar`, label "Marcar como terminado", `{% if not resultado.puede_generar %}disabled{% endif %}`, always-rendered `.acciones__razon` span — mirrors old `revision.html:53-59` verbatim except label.
- [x] 4.2 Confirm 3.1-3.4 GREEN.

## Phase 5: RED — Remove closure from Revision, add link

- [x] 5.1 New test: creator's `reportes_revision` GET renders no closure form / creates no `VistoBueno`.
- [x] 5.2 New test: `reportes_revision` response contains "Cerrar en Participantes →" link to `reportes_participantes`.
- [x] 5.3 Run 5.1-5.2, confirm fail.

## Phase 6: GREEN — `reportes/templates/reportes/revision.html`

- [x] 6.1 Delete closure `<form>` from `.hoja__pie` (:53-59); keep Generar form (:46-51).
- [x] 6.2 Relabel `Participantes` link (:63) to "Cerrar en Participantes →" (same href).
- [x] 6.3 Confirm 5.1-5.2 GREEN.

## Phase 7: Migrate `disabled`-coupled tests (`reportes/tests/test_views.py`)

- [x] 7.1 `:569` `"disabled" in ...`: move assertion to a `reportes_participantes` GET as creator; keep status/context checks on `reportes_revision`.
- [x] 7.2 `:598` `"disabled" not in ...`: same migration, `reportes_participantes`.
- [x] 7.3 `:625` (`disabled`/`.acciones__razon`/error text): retarget to `reportes_participantes`, or fold into 3.2 and delete the duplicate.
- [x] 7.4 `:663`/`:691` (tripwire with/without errors): retarget both branches to `reportes_participantes`, or fold into 3.3.
- [x] 7.5 Run full migrated set; confirm no test asserts `disabled` against `reportes_revision`.

## Phase 8: Cleanup and verification

- [x] 8.1 `static/css/components.css:184-188` comment: reference `participantes.html` (comment only).
- [x] 8.2 Run `pytest reportes/tests/test_views.py` full file, confirm all pass.
- [x] 8.3 Run full project test suite for other `revision`/`participantes`/`cerrar_reporte` coupling.
- [x] 8.4 Grep repo for stray "Cerrar reporte" label strings; confirm rename to "Marcar como terminado" is complete.

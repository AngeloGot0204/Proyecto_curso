# Proposal: Validación de datos del formulario

## Intent

The wizard-captura pipeline (#5) persists form values with no validation gate: `paso`'s POST discards `form.is_valid()` by design (D8), and no aggregate check exists before `.xlsx` generation besides `generador.py::_validar_completitud` (which only fires at generation time, too late for a good review UX). TECH-DESIGN.md requires three distinct pre-generation checks — missing required fields, invalid hora_fin/hora_inicio ranges, and unacknowledged "No cumple" checklist items — none of which the app currently surfaces to the user. This closes that gap with the review screen (S-09) that ADR-0007 made the sole pre-generation checkpoint.

## Scope

### In Scope
- Client-side JS (vanilla, no library, per ADR-0001) in `paso.html`: disable "Siguiente" when a `rango-hora-inicio-fin` pair has fin <= inicio.
- Server-side defense-in-depth re-check of the same rule on `paso` POST — non-blocking (D8 preserved), flagged for S-09.
- "No cumple" detection: exact string match on `seleccion`-type field values. On match, an `{id}_observacion` text companion field becomes required (JS-toggled visibility) and persists as `ValorDeReporte` with `identificador_de_campo=f"{id}_observacion"`, reusing the existing two-key pattern from `rango-hora-inicio-fin`.
- New `reportes/validacion.py::validar_reporte(reporte)` — walks `_iterar_nodos` against persisted `ValorDeReporte`, returns `errores` (missing obligatorio — blocking) and `advertencias` (No cumple without observation; stray hora_fin<=hora_inicio) buckets, each with `identificador_de_campo` + `seccion_id` link-back. Reuses `tipos_reporte/generador.py`'s obligatorio-detection logic — no reimplementation.
- New view/template `/reportes/<reporte_id>/revision/` (S-09): "Debes corregir" (errores, linked to `paso`) and "Advertencias" lists; "Generar" disabled when `errores` is non-empty (no real destination yet — #7 wires it).
- Tests first (strict TDD) for `validacion.py` and the S-09 view.

### Out of Scope
- Backlog #7: visto bueno / actual `.xlsx` generation trigger.
- Backlog #9: offline S-09 (stays server-rendered).
- Backlog #11: unsupported adjunto format blocking (no adjuntos model exists yet).
- Any change to D8's non-blocking step-level POST semantics.

## Capabilities

### New Capabilities
- `validacion-reporte`: server-side aggregate validation (`validar_reporte`) producing blocking errors and non-blocking warnings for a `Reporte`, reusing obligatorio-detection from the generator, plus the S-09 review screen that consumes it.

### Modified Capabilities
- `wizard-captura`: `paso.html` gains client-side hora range validation (Siguiente disabled) and "No cumple" observation-field toggling; `paso` POST gains a non-blocking server-side hora range re-check. No change to existing non-blocking obligatorio POST behavior.

## Approach

Three mechanisms per TECH-DESIGN's three rules (exploration Approach 3): (1) vanilla JS for immediate hora-range feedback, re-verified server-side but never blocking; (2) a new aggregate `validar_reporte` module reused by both S-09 and (later, #7) a pre-generation guard, sharing obligatorio logic with `_validar_completitud` to avoid drift; (3) "No cumple" as a presentational/observation-required warning, never blocking. D8's shipped non-blocking-per-step contract and its locking test (`test_post_paso_sin_valor_obligatorio_no_bloquea`) stay intact — blocking only happens at the S-09/generation gate.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reportes/templates/reportes/paso.html` | Modified | Vanilla JS: disable Siguiente on invalid hora range; toggle `_observacion` field on No cumple |
| `reportes/views.py` | Modified | Non-blocking server-side hora range check on POST; new `revision` view for S-09 |
| `reportes/validacion.py` | New | `validar_reporte(reporte)` aggregate check, errores/advertencias buckets |
| `reportes/templates/reportes/revision.html` | New | S-09 template: Debes corregir / Advertencias lists, disabled Generar |
| `reportes/urls.py` | Modified | Add `/reportes/<reporte_id>/revision/` route |
| `reportes/tests/test_views.py` | Modified | New tests; reconcile with `test_post_paso_sin_valor_obligatorio_no_bloquea` (must keep passing) |
| `reportes/tests/test_validacion.py` | New | TDD tests for `validar_reporte` |
| `tipos_reporte/generador.py` | Referenced, not modified | `validar_reporte` reuses its obligatorio-detection logic |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Drift between `validar_reporte` and `_validar_completitud` obligatorio checks | Med | Explicit code reuse (shared helper/function), not reimplementation; test both stay consistent |
| Regression of D8 non-blocking-per-step test | Med | Keep `paso` POST unchanged for obligatorio; only add non-blocking hora-range check; explicit reconciliation test pass |
| "No cumple" observation persistence collides with existing `_observacion`/rango key pattern | Low | Reuse the exact same `{id}_observacion` mechanism already proven for `rango-hora-inicio-fin` |
| S-09 "Generar" button has no real destination (deferred to #7) | Low | Explicitly scoped as no-op/disabled-only in this change; documented in spec |

## Rollback Plan

All changes are additive (new module, new view/template, new JS) except the `paso.html`/`paso` view edits, which are template/view-local and revertible via `git revert`. No schema/migration changes are introduced (observación reuses existing `ValorDeReporte` key pattern). If S-09 or `validacion.py` misbehaves, the route and template can be removed without affecting the existing wizard-captura flow.

## Dependencies

- Backlog #5 (wizard-captura) — merged, provides `_iterar_nodos`, `formularios.py`, `ValorDeReporte` persistence.
- `tipos_reporte/generador.py::_validar_completitud` — obligatorio-detection logic to reuse.

## Success Criteria

- [ ] Siguiente is disabled client-side (no library) when hora_fin <= hora_inicio, re-validated server-side without blocking POST.
- [ ] "No cumple" selection reveals a required observación field and persists it via the existing key-pair pattern.
- [ ] `validar_reporte` returns correct errores/advertencias, reusing generator obligatorio logic (no drift).
- [ ] S-09 view lists errores (linked to their paso) and advertencias; Generar is disabled iff errores is non-empty.
- [ ] `test_post_paso_sin_valor_obligatorio_no_bloquea` still passes unmodified in intent (step POST stays non-blocking).

## Proposal question round

All four open decisions from exploration were pre-confirmed by the user before this phase and encoded directly in scope above (vanilla JS for hora range with server-side defense-in-depth; exact-string "No cumple" detection persisted via the `{id}_observacion` key pattern; S-09 stays server-rendered, offline deferred to #9; `validar_reporte` must reuse — not reimplement — `_validar_completitud`'s obligatorio logic). No further question round was run. If any of these assumptions should be revisited, flag before `sdd-spec` proceeds.

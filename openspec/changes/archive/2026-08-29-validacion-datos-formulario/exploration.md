# Exploration: Validación de datos del formulario (backlog #6)

## Current State

Backlog #5 (merged) built the wizard-captura pipeline: `reportes/formularios.py` builds a dynamic `django.forms.Form` per section from `estructura` (design D4/D5/D8); `reportes/views.py::paso` renders it on `GET` (rehydrated from `ValorDeReporte` rows) and persists on `POST`; `reportes/valores.py` is a pure string codec plus `guardar_valor` upsert/delete — no validation hook of any kind.

**Confirmed gap** (the exact thing #6 must close):

- `reportes/formularios.py::_marcar_obligatorio` sets ONLY the HTML `required` widget attribute. Every Django field is constructed with `required=False` (`_campo_escalar`, `_campos_de_rango`), by explicit design (D8) — "blocking on a missing `obligatorio` value is explicitly out of scope (backlog #6)".
- `reportes/views.py::paso` POST branch: `form.is_valid()` is called but the code comment says outright *"every field is `required=False` (design D8) — never blocks; cleaned_data below always reflects the submitted values."* Its return value is discarded; there is no `if not form.is_valid(): ...` branch at all.
- `reportes/valores.py::guardar_valor` is pure persistence (upsert-or-delete by `None`/`""` membership test) — no validation hook point exists anywhere in this app today. `desde_texto`/`a_texto` are pure codec functions.
- `reportes/tests/test_views.py::test_post_paso_sin_valor_obligatorio_no_bloquea` explicitly locks in today's non-blocking behavior as a passing test — this test's assertions will need to change/coexist carefully once #6 introduces real blocking at the S-09/generation level.

There is currently **no server-side validation layer** between form submission and persistence, and no concept of "errors that block" vs. "warnings that don't" anywhere in `reportes/`.

## Affected Areas

- `reportes/formularios.py` — `_marcar_obligatorio`/`_campos_de_rango` is where `obligatorio` and the `rango-hora-inicio-fin` pair are known; any new validation rule needs `_iterar_nodos` traversal to stay in sync with the generator's own labeling.
- `reportes/views.py::paso` — the exact spot where `form.is_valid()` currently gets ignored; blocking-vs-non-blocking behavior branches here (and/or in a new S-09 view).
- `reportes/valores.py` — codec/persistence layer; likely untouched for pure format validation (Django field parsing already handles hora/fecha), but may need a hook if "No cumple" detection reads persisted values across the whole `Reporte`.
- `tipos_reporte/validacion.py` — `_iterar_nodos`, `TipoDeDato` catalog; no `CHECKLIST`/"no cumple" node type exists — that concept lives only as a domain VALUE (a `SELECCION` option), not a first-class type.
- `tipos_reporte/generador.py::_validar_completitud` (lines 91-96, called at line 204) — an EXISTING, SEPARATE completeness check that runs at `.xlsx` GENERATION time, raising `ValoresIncompletos` for missing `obligatorio` fields. This is a different validation moment than #6's wizard-time validation; #6 must not duplicate or silently diverge from it.
- `reportes/tests/test_views.py` — needs new tests for hora_fin > hora_inicio, format validation, and the "No cumple" warning path; `test_post_paso_sin_valor_obligatorio_no_bloquea` needs explicit reconciliation with the new blocking behavior.
- No S-09 template/view exists yet in `reportes/` — this is new UI work.

## Design/PRD Findings

**TECH-DESIGN.md "Validación de datos"** — four acceptance criteria:
1. Empty required field listed in S-09 with field link, blocks generation.
2. hora término < hora inicio marks the cell invalid, disables "Siguiente" until corrected (step-level UX, not the S-09 list).
3. "No cumple" item shows warning, requires observation, does not block.
4. Unsupported adjunto format blocks only the attachment (out of scope for #6).

**hora_termino > hora_inicio**: confirmed via `formularios.py::_campos_de_rango` + `DESIGN.md` S-06 — this is the **`rango-hora-inicio-fin` composite field's own two sub-values** validated against each other, NOT a cross-validation between two independent `campo` nodes. There is no separate pair-comparison rule type in the schema.

**"No cumple"**: confirmed via PRD.md and DESIGN.md S-05 — a **checklist item outcome value** (e.g. a `SELECCION`/`Sí-No` per-role checklist cell), not a distinct `TipoDeDato`. PRD: *"Un checklist tiene un ítem marcado 'No cumple' (falla): el sistema solo advierte al usuario, no bloquea... (queda registrado con su observación)."* DESIGN.md: *"Un 'No cumple' muestra una tarjeta ámbar informativa, nunca bloquea."* No schema support exists yet for "require an observation when No cumple" — new logic, likely keyed off a specific option string rather than a new type.

**Pantalla S-09**: full spec found in `DESIGN.md` and `adrs/0007-sin-vista-previa-en-la-aplicacion.md` — a **modal sheet with two lists**: "Debes corregir" (each item links to its exact field; "Generar" stays disabled while non-empty) and "Advertencias" ("No cumple" + atypical data; never blocks). ADR-0007 elevates S-09's importance: since S-11/S-12 preview screens were eliminated, S-09 plus free wizard-step navigation are the ONLY review mechanism before generating the `.xlsx`. No wireframe image exists in the repo — DESIGN.md prose is the only spec artifact. `REVISION-ADVERSARIAL.md` notes S-09 must work offline.

## Existing Test Conventions

`reportes/tests/` uses pytest + pytest-django, `@pytest.mark.django_db`, factory fixtures (`usuario_factory`, `reporte_factory`, `tipo_con_definicion_activa_factory`) from `conftest.py`, and a strict-TDD-authored docstring convention referencing backlog #/design decision/spec scenario per test module. New validation tests should follow this same pattern.

## Approaches

1. **Single server-side aggregate validation function checked at S-09 render time** (`reportes/validacion.py::validar_reporte(reporte)`) walking `_iterar_nodos` against persisted `ValorDeReporte` rows, returning blocking-errors + warnings buckets.
   - Pros: single source of truth for S-09 and a pre-generation guard; each error naturally carries `identificador_de_campo` for "enlace al campo".
   - Cons: needs its own traversal separate from (but must stay consistent with) `_validar_completitud`'s existing obligatorio logic — risk of drift if not shared.
   - Effort: Medium.

2. **Per-step blocking via `form.is_valid()`** — flip `obligatorio` to `required=True`, block each step's `POST` when invalid, add a `clean()` for hora_fin > hora_inicio.
   - Pros: minimal new code; leans on existing (currently ignored) `form.is_valid()` call.
   - Cons: directly contradicts design D8's non-blocking-per-step decision, already locked in by a passing test; doesn't produce S-09's cross-step aggregate list at all — wrong mechanism for requirement #1 and #3.
   - Effort: Low, but solves the wrong problem for 2 of 3 rules.

3. **Hybrid**: keep step-level non-blocking persistence (D8 intact) + client-side JS for hora_fin > hora_inicio (disable "Siguiente", supports offline) + new server-side aggregate check reused by S-09 view and a pre-generation guard, sharing obligatorio-detection logic with `_validar_completitud`.
   - Pros: matches each TECH-DESIGN bullet with its right mechanism; preserves #5's shipped/tested non-blocking invariant; offline-friendly for the one rule that needs immediate feedback.
   - Cons: broader surface area (JS/template + new validation module + new S-09 view/template); requires deliberate de-duplication against `_validar_completitud`.
   - Effort: Medium-High.

## Recommendation

Approach 3. TECH-DESIGN's four validation bullets map to three different mechanisms, not one: immediate client-side feedback for the range rule (offline-friendly, per REVISION-ADVERSARIAL.md), a step-independent aggregate check for missing-required + S-09's list, and a purely presentational non-blocking warning for "No cumple". Approach 2 would break the already-shipped, already-tested #5 non-blocking-per-step contract. The aggregate module should explicitly reuse (not reimplement) whatever obligatorio-detection logic `tipos_reporte/generador.py::_validar_completitud` already has to avoid the two checks silently disagreeing.

## Open Decisions (must be settled in proposal)
1. How is "No cumple" detected in the schema — exact option-string match? Which fields carry this concept?
2. Where is the "observación" for a "No cumple" captured — a new field on `ValorDeReporte`, or a separate model?
3. Must S-09's aggregate check work fully offline (client-side only) or can it hit the server? (#9 offline isn't built yet, so likely server-rendered for now — confirm.)
4. hora_fin > hora_inicio client-side validation: plain vanilla JS (per ADR-0001's minimal-JS constraint) vs. server-side-only check with page reload?

## Risks
- **Drift between two obligatorio checks**: `_validar_completitud` already raises `ValoresIncompletos` at generation time; #6 adds an earlier S-09 check. Independent implementations risk disagreement.
- **No schema support for "No cumple requires an observation"**: needs a decision on detection and where the observation is captured.
- **Regression risk for `test_post_paso_sin_valor_obligatorio_no_bloquea`**: any change must keep step-level `POST` non-blocking per design D8.
- **No wireframe image for S-09**; only DESIGN.md prose available. Offline requirement (S-09 must work offline per REVISION-ADVERSARIAL.md) needs explicit scoping — likely deferred since #9 isn't built.

## Key Learnings
1. `reportes/views.py::paso` calls `form.is_valid()` but discards the result — the wizard's non-blocking behavior is an explicit design D8 decision, not an oversight, confirmed by inline code comments.
2. "No cumple" is a checklist item's option value (Sí/No per role), not a distinct `TipoDeDato` in `tipos_reporte/models.py` — new logic for #6 must detect it by value, not by type.
3. `hora_termino > hora_inicio` refers to the existing `rango-hora-inicio-fin` composite field's own two sub-values, not a cross-validation between two separate campo nodes.
4. `tipos_reporte/generador.py::_validar_completitud` already validates obligatorio fields at `.xlsx` generation time — backlog #6 must reuse this logic rather than reimplement it independently.
5. S-09 is fully specified in `DESIGN.md` and `adrs/0007-...` as a two-list modal (blocking errors vs. non-blocking warnings), elevated in importance since preview screens S-11/S-12 were eliminated.

**Next**: sdd-propose

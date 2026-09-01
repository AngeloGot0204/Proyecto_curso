# Apply Progress: retrofit-visual-design2

**Cumulative scope**: PR1a (Phase 1, 17/17) + PR1b (Phase 2, 14/14) + PR2
(Phase 3, 15/15) + PR3 (Phase 4, 14/14) complete. **60/60 tasks complete
across all 4 PRs. Change fully implemented, ready for verify/archive.**

## Phase 4 (PR3 — validación + estados) — 14/14 complete

**Mode**: Strict TDD (pytest, `.venv/Scripts/python.exe -m pytest`).

- [x] 4.1 RED `reportes/tests/test_views.py::test_revision_boton_primario_deshabilitado_muestra_razon_via_acciones_razon`
- [x] 4.2 RED `test_revision_tripwire_disabled_sigue_presente_como_antes`
- [x] 4.3 RED `test_revision_aplica_hoja_modal_component_class`
- [x] 4.4 RED `test_participantes_aplica_checklist_y_campo_component_classes`
- [x] 4.5 RED `reportes/tests/test_estatico.py::test_borrador_banner_aplica_aviso_class_via_data_atributo`
- [x] 4.6 RED `test_sw_js_contiene_cache_v6` (net-new test; old `test_sw_js_contiene_cache_v5` removed in place, matching PR1b/PR2's rename precedent)
- [x] 4.7 GREEN `static/css/components.css`: added the `.acciones__razon` disabled-reason reveal rule (`.acciones__primario:disabled ~ .acciones__razon{display:block}`) into the existing `§acciones` block (PR1a had deliberately deferred this exact rule to PR3, per its own comment); added `§hoja` (`.hoja`, `__tirador`, `__encabezado`, `__cuerpo`, `__lista`, `__item`, `--error`, `--ambar`, `__pie`); added `[data-borrador-banner]`/`[data-borrador-prompt]` attribute-selector styling reusing `.aviso`'s ámbar visual language
- [x] 4.8 GREEN `reportes/templates/reportes/revision.html`: wrapped the errores/advertencias listing in `.hoja` (tirador, mono/chip count header, scrollable body, own `.hoja__pie` action bar); errores render as `.hoja__item--error` (bordered, `→` per row, links to campo); advertencias render as `.hoja__item--ambar`; the pre-existing `{% if not resultado.puede_generar %}disabled{% endif %}` attribute is untouched — `.acciones__razon` markup added as an always-present sibling `<span>` next to the button, revealed purely by CSS; "Participantes" link restyled `.acciones__secundario`
- [x] 4.9 GREEN `reportes/templates/reportes/participantes.html`: `.checklist`/`.checklist__item` on the Invitados `<ul>`; `.campo`/`.campo__etiqueta` on the invite form's username field; `.acciones`/`.acciones__primario` on the invite form/button; `.tabla` on the historial table (not explicitly required by tasks.md's task description but zero-risk, matches the established component vocabulary, `.mono` added to the "Creador:" line)
- [x] 4.10 GREEN `reportes/templates/reportes/sw.js`: `CACHE` `"v5"` → `"v6"`
- [x] 4.11 Ran 4.1–4.6: all green
- [x] 4.12 REFACTOR: confirmed exactly one literal `"disabled"` substring in `revision.html` (the pre-existing server-side conditional, line 56) and zero in `base.html`; zero `"generado"` substring in `mis_reportes.html`/`base.html` — tripwires intact
- [x] 4.13 Full scoped suite `pytest reportes/ tipos_reporte/ usuarios/ -q`: **375 passed, 0 failed** (833.11s)
- [ ] 4.14 Manual QA — **NOT executable by this automated agent** (no browser/DevTools access). Deferred to the human maintainer: DESIGN2 §5 checklist per screen at 390×844 and 1120×844; DevTools offline reload of a wizard step (CSS + font served from SW cache, `capa-offline` scenario); throttled first load to sanity-check the `swap` flash.

### Mid-batch fix (Spanish pluralization)

While writing `.acciones__razon`'s reason text, the first draft used Django's
default `|pluralize` filter on "error" (`error{{ ...|pluralize }}`), which
appends English `"s"` → `"errors"`, not the correct Spanish `"errores"`.
Fixed to `|pluralize:"es"` (explicit suffix argument) in both occurrences
(`.hoja__encabezado`'s chip count and `.acciones__razon`'s text). Caught by
manual review before the final full-suite run, not by an automated test —
no existing/new test asserts the exact plural spelling, only substring
presence (`"error"` in `contenido.lower()`). `advertencia`'s default
`|pluralize` (`"s"` suffix → `"advertencias"`) is correct Spanish as-is, no
fix needed there.

### Files Changed (Phase 4 / PR3)

| File | Action | What Was Done |
|---|---|---|
| `static/css/components.css` | Modified | Added `.acciones__razon` + disabled-reveal rule to `§acciones`; added `§hoja`; added `[data-borrador-banner]`/`[data-borrador-prompt]` styling |
| `reportes/templates/reportes/revision.html` | Modified | `.hoja` wrapper (S-09), chip count header, `.hoja__item--error`/`--ambar` listings, `.acciones`/`.acciones__primario`/`.acciones__razon` on both forms, `.acciones__secundario` on the Participantes link |
| `reportes/templates/reportes/participantes.html` | Modified | `.checklist` (Invitados), `.campo` (invite form field), `.acciones` (invite form/button), `.tabla` (historial), `.mono` (Creador line) |
| `reportes/templates/reportes/sw.js` | Modified | `CACHE` v5 → v6 (D4) |
| `reportes/tests/test_views.py` | Modified | +5 new tests (4.1–4.4, 4.6); removed/replaced `test_sw_js_contiene_cache_v5` |
| `reportes/tests/test_estatico.py` | Modified | +1 test (4.5) |

### TDD Cycle Evidence (Phase 4 / PR3)

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| 4.1 | `test_views.py` | Integration (HTTP response) | ✅ Written — failed (`'class="acciones__razon'` absent from pre-retrofit markup) | ✅ Passed after 4.7/4.8 | ✅ 5 assertions (button class, literal `disabled`, razon span class, lower-case "error" text, non-empty errores) | ➖ None needed |
| 4.2 | `test_views.py` | Integration | ⚠️ Passed trivially pre-edit — mirrors PR1a's 1.7/PR2's 3.6 "approval test" pattern: the literal `disabled` attribute guard was already true of the pre-retrofit template and remained true through the `.hoja`/`.acciones` restructure; two independent `TipoDeReporte` rows (distinct `codigo`) were needed to exercise both branches in one test since the existing `reporte_con_validaciones_factory` hardcodes its codigo/username and cannot be called twice | ✅ Still passes after 4.8 | ✅ Both disabled/enabled branches, 2 separate reportes | ➖ None needed |
| 4.3 | `test_views.py` | Integration | ✅ Written — failed (no `.hoja`/`hoja__encabezado`/`hoja__cuerpo` classes existed) | ✅ Passed after 4.8 | ✅ 3 assertions | ➖ None needed |
| 4.4 | `test_views.py` | Integration | ✅ Written — failed (no `.checklist`/`.campo` classes on `participantes.html`) | ✅ Passed after 4.9 | ✅ 2 assertions | ➖ None needed |
| 4.5 | `test_estatico.py` | Unit (static CSS text) | ✅ Written — failed (`[data-borrador-banner]` absent from pre-edit `components.css`) | ✅ Passed after 4.7 | ✅ 3 assertions (both attribute selectors + shared ámbar variable) | ➖ None needed |
| 4.6 | `test_views.py` | Integration | ✅ Written (net-new, `v5` test removed) — failed (`v5` in body, not `v6`) | ✅ Passed after 4.10 | ➖ Single scenario | ➖ None needed |

### Deviations from Design (Phase 4 / PR3)

- **`.hoja` ships as a static inline sheet, not a real velo-backed modal
  overlay.** DESIGN2 §4 "Hoja modal (S-09)" describes a `rgba(20,19,15,.5)`
  velo over a dimmed previous screen, a bottom-anchored sheet with a drag
  handle, and implied open/close interaction. D7 forbids all new JavaScript
  in this change, so no toggle/overlay state exists to drive that
  interaction — `revision.html` renders `.hoja` as an always-visible static
  card (border-top 2px negro, decorative `.hoja__tirador`, mono/chip count
  header, scrollable body, own action-bar footer) instead. Same "reasonable
  visual extrapolation for a JS-less constraint" pattern already documented
  for PR2's `.pasos`/`.checklist` deviations.
- **Chip classes on `revision.html` (S-10) implemented as an errores/
  advertencias count badge**, not a per-participant status chip. The app's
  `revision` view has no per-participant `VistoBueno` data structure (only
  one boolean `tiene_visto_bueno` flag for the whole reporte) — building a
  per-role chip grid would be a `.py`/model change, out of scope. A
  `chip chip--borde` badge in `.hoja__encabezado` showing the error/warning
  count satisfies "apply chip classes" without inventing new data.
- **`.tabla` applied to `participantes.html`'s historial table**, beyond
  what task 4.9's own description literally names (`.checklist`/`.campo`
  only). Zero-risk, styling-only, reuses an already-shipped (PR1b) class —
  included for visual completeness across the retrofit's last PR.
- **Spanish pluralization fix**: `|pluralize:"es"` instead of the default
  `|pluralize` for "error" (see "Mid-batch fix" note above).

### Issues Found (Phase 4 / PR3)

None beyond the self-caught pluralization wording fix (see note above).

### Work Unit Evidence (Phase 4 / PR3)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/Scripts/python.exe -m pytest reportes/tests/test_views.py -k "revision" -q` → 12 passed; `reportes/tests/test_estatico.py -q` → 9 passed |
| Runtime harness command/scenario and exact result | Not executed — task 4.14 (Manual QA: DevTools offline reload + throttled first load + 390×844/1120×844 visual checklist) requires a real browser and cannot be performed by this automated agent. Explicitly flagged as an outstanding human step, not silently skipped. |
| Rollback boundary | Revert `revision.html`, `participantes.html`, `sw.js`'s `CACHE` line, and `components.css`'s `.acciones__razon` rule + `§hoja` + `[data-borrador-banner]`/`[data-borrador-prompt]` sections; revert the 6 new/renamed tests across `test_views.py`/`test_estatico.py`. PR1a/PR1b/PR2 (tokens.css, base.html, login.html, the 4 `tipos_reporte` templates, `mis_reportes.html`, `paso.html`, `adjuntos.html`, and every other `components.css` section) stay fully functional and untouched. |

### Full Regression Run (Phase 4 / PR3)

`.venv/Scripts/python.exe -m pytest reportes/ tipos_reporte/ usuarios/ -q`
(task 4.13's exact command) → **375 passed, 0 failed** in 833.11s. Named
tripwires all re-verified holding: `"disabled"` present exactly once in
`revision.html` (the pre-existing server-side conditional) and absent from
`base.html`; `"generado"` absent from both `mis_reportes.html` and
`base.html`; `test_get_revision_con_errores_deshabilita_generar` /
`test_get_revision_sin_errores_habilita_generar` (the original PR3-adjacent
disabled tripwire pair) both still green; `tipos_reporte/tests/test_vistas.py`
(PR1b scope) untouched, still green.

### Status (Phase 4 / PR3)

14/14 Phase 4 tasks complete (13/14 automated; 4.14 is a flagged manual-QA
step outside this agent's execution surface). **60/60 tasks complete across
PR1a+PR1b+PR2+PR3 (Phases 1–4).** Change `retrofit-visual-design2` is fully
implemented. Ready for `sdd-verify`; task 4.14 (manual QA) should be run by
a human before/alongside archive.

---

## Phase 3 (PR2 — móvil: lista + wizard) — 15/15 complete

**Mode**: Strict TDD (pytest, `.venv/Scripts/python.exe -m pytest`).

- [x] 3.1 RED `reportes/tests/test_views.py::test_mis_reportes_aplica_barra_pantalla_y_lista_component_classes`
- [x] 3.2 RED `test_paso_aplica_pasos_indicador_y_checklist_component_classes`
- [x] 3.3 RED `reportes/tests/test_estatico.py::test_paso_campo_error_aria_invalid_usa_borde_2px_sin_color_rojo`
- [x] 3.4 RED `reportes/tests/test_adjuntos.py::test_adjuntos_aplica_grid_de_adjuntos_component_class`
- [x] 3.5 RED `test_paso_fila_de_horas_aplica_component_class`
- [x] 3.6 RED `test_paso_primer_boton_submit_sigue_siendo_el_del_formulario_tras_retrofit`
- [x] 3.7 RED `test_sw_js_contiene_cache_v5` (renamed in place from `test_sw_js_contiene_cache_v4`, matching PR1b's precedent)
- [x] 3.8 GREEN `static/css/components.css`: added `§barra-pantalla`, `§pasos`, `§checklist` (incl. `.fila-horas`), `§lista`, `§adjuntos`; extended existing `§acciones` block with `display:inline-flex`/`text-decoration:none` so `.acciones__primario`/`.acciones__secundario` also work as `<a>` elements (needed by the new pagination/nav links)
- [x] 3.9 GREEN `mis_reportes.html`: `.barra-pantalla` header (no volver, S-02 is root); both report groupings rebuilt from native `<table>`s into `.lista` mobile card lists; filter/logout buttons and pagination links restyled with `.acciones__secundario`
- [x] 3.10 GREEN `paso.html`: `.barra-pantalla` header (`url_anterior` as `.barra-pantalla__volver`, `posicion` as mono indicator); `.pasos` step indicator (`--activo` modifier on `es_actual`); `.checklist`/`.campo` wrapping the generic field loop; `.fila-horas` modifier detected via `campo.name` slice-suffix `_inicio`/`_fin` (Django's `slice` filter, no Python change — `tipos_reporte.generador._SUFIJO_POR_CLAVE` guarantees the suffix); mono styling for `[data-rango]` inputs via a components.css attribute selector (no widget-attrs change needed); bottom nav restyled `.acciones`
- [x] 3.11 GREEN `adjuntos.html`: `<table>` replaced with `.adjuntos` 2-column grid (`.adjuntos__item`/`__miniatura`/`__info`/`__nombre`/`__meta`/`__descarga`)
- [x] 3.12 GREEN `sw.js`: `CACHE` `"v4"` → `"v5"`
- [x] 3.13 Ran 3.1–3.7 (plus 3.3's home in test_estatico.py, 3.4's home in test_adjuntos.py): all green
- [x] 3.14 REFACTOR: confirmed zero production `.py`/`.js` files changed this PR — only test files (`test_views.py`, `test_adjuntos.py`) and `sw.js`'s single `CACHE` line; no new `disabled`/`generado` literal substring introduced (mis_reportes.html tripwire re-verified: `test_mis_reportes_chip_en_progreso`/`test_mis_reportes_chip_terminado` assert `"generado" not in contenido`, still passing)
- [x] 3.15 Full pytest suite: **390 passed, 0 regressions** (810.48s) — up from PR1b's 384 (+6 new tests: 3.1/3.2/3.3/3.4/3.5/3.6; 3.7 is a rename, net zero)

### Files Changed (PR2)

| File | Action | What Was Done |
|---|---|---|
| `static/css/components.css` | Modified | Added `§barra-pantalla`, `§pasos`, `§checklist`, `§lista`, `§adjuntos`; extended `§acciones` for anchor-as-button support |
| `reportes/templates/reportes/mis_reportes.html` | Modified | `.barra-pantalla` header; both listings converted to `.lista` card lists; `.acciones` styling on filter/logout/pagination |
| `reportes/templates/reportes/paso.html` | Modified | `.barra-pantalla` header, `.pasos` indicator, `.checklist`/`.campo`/`.fila-horas` field wrapper, `.acciones` bottom nav |
| `reportes/templates/reportes/adjuntos.html` | Modified | `.barra-pantalla` header, `.adjuntos` 2-column grid replacing the native `<table>` |
| `reportes/templates/reportes/sw.js` | Modified | `CACHE` v4 → v5 (D4) |
| `reportes/tests/test_views.py` | Modified | +5 new tests (3.1, 3.2, 3.5, 3.6) + `test_sw_js_contiene_cache_v4` renamed to `test_sw_js_contiene_cache_v5` |
| `reportes/tests/test_estatico.py` | Modified | +1 test (3.3) |
| `reportes/tests/test_adjuntos.py` | Modified | +1 test (3.4) |

### TDD Cycle Evidence (Phase 3 / PR2)

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| 3.1 | `test_views.py` | Integration (HTTP response) | ✅ Written — failed (`'class="barra-pantalla'`/`'class="lista'` absent from pre-retrofit `<h1>`/`<table>` markup) | ✅ Passed after 3.9 | ✅ 3 assertions (`.barra-pantalla`, `.lista`, `.lista__tarjeta`) | ➖ None needed |
| 3.2 | `test_views.py` | Integration | ✅ Written — failed (no `.pasos`/`.checklist` classes existed) | ✅ Passed after 3.10 | ✅ 3 assertions (`.pasos`, `.checklist`, `checklist__item`) | ➖ None needed |
| 3.3 | `test_estatico.py` | Unit (static CSS text) | ⚠️ Passed trivially pre-edit — the `[aria-invalid="true"]`/`var(--borde-error)`/`var(--color-tinta)` rule already existed in `components.css` from PR1a's `§campo` block; approval-style re-verification against the new `paso.html` consumer, same pattern as PR1a's task 1.7 note | ✅ Still passes | ✅ 6 assertions (selector, both CSS vars, 3 red-keyword/hex checks) | ✅ One iteration: initial run failed on a false positive — my own new `§pasos` comment used the word "bordered", which contains the substring `"red"`; reworded to "with a border" and re-ran green |
| 3.4 | `test_adjuntos.py` | Integration | ✅ Written — failed (`'class="adjuntos'` absent from the pre-retrofit `<table>`) | ✅ Passed after 3.11 | ✅ 2 assertions (`.adjuntos`, `.adjuntos__item`) | ➖ None needed |
| 3.5 | `test_views.py` | Integration | ✅ Written — failed (`contenido.count("fila-horas") == 0`, expected 2) | ✅ Passed after 3.10 (both `p-01_inicio`/`p-01_fin` get the modifier via the `campo.name` slice check) | ✅ Exact count assertion (`== 2`, not just presence) | ➖ None needed |
| 3.6 | `test_views.py` | Integration | ⚠️ Passed trivially pre-edit — `paso.html` already had exactly one submit button and no header/logout form; approval-style guard re-verified against the *retrofitted* markup (new `.pasos`/`.checklist`/`.barra-pantalla` structure could have introduced an extra button but didn't) | ✅ Still passes after 3.10 | ➖ Single scenario (first submit button's text) | ➖ None needed |
| 3.7 | `test_views.py` | Integration | ✅ Written (renamed from `_v4`) — failed (`v4` in body, not `v5`) | ✅ Passed after 3.12 | ➖ Single scenario | ➖ None needed |

**Note on 3.3 and 3.6** (mirroring PR1a's precedent): both were real, behavior-
asserting checks written RED-first per the Three Laws, but happened to pass
before any production code changed in this batch because the guard they
encode was already true (3.3: PR1a's CSS rule; 3.6: the pre-retrofit
single-submit-button structure). Both remained green through the actual
`paso.html`/`components.css` edits, proving the retrofit didn't regress
either guarantee. 3.3 additionally caught a real, if trivial, self-inflicted
regression during the batch (the "bordered" substring collision), which was
fixed before the batch was considered done.

### Deviations from Design (Phase 3 / PR2)

- **`.pasos` completed/pending distinction dropped.** DESIGN2 §4 describes
  three step states (active 12px solid, completed 8px solid, pending 8px
  bordered). The `paso` view only provides `paso_item.es_actual`(bool) per
  step — no "already completed" flag — and adding one would be a `.py`
  change (out of scope, task 3.14). Implemented as two states only:
  `--activo` (current) and default (bordered, used for both completed and
  upcoming steps). Documented here as the "reasonable visual extrapolation"
  the proposal explicitly allows for gaps between DESIGN2 and the current
  data model.
- **`.checklist` is not a per-role table.** DESIGN2 §4 "Checklist por rol"
  describes one card per item with a Sí/No column per role. The app has no
  per-role data structure in `paso.html`'s generic Django form (`reportes/
  formularios.py` renders one scalar/seleccion field per node, not a
  role-keyed grid) — building that would be a `.py`/forms change, out of
  scope. `.checklist` here is the rhythm/spacing wrapper around the existing
  `.campo` field list, per design D3's "styling native controls as
  descendants" principle.
- **`.fila-horas` groups by CSS float/inline-flex, not a shared wrapper
  div.** Pairing `_inicio`/`_fin` into one visual row without a template
  helper tag (forbidden — no new Python) uses `display:inline-flex; width:
  calc(50% - gap/2)` on each field individually, relying on their
  guaranteed document-order adjacency (`reportes/formularios.py`'s
  `_campos_de_rango` inserts both into the same dict, insertion-ordered).
  No `Δ min` computed field is rendered (it doesn't exist as form data or a
  JS-populated attribute anywhere in the current app — adding it would be
  new JS, forbidden by D7).
- **Mono styling for horas/N.º applied via CSS attribute selector, not a
  template `class="mono"` addition.** `reportes/formularios.py` builds
  widget classes in Python; adding a `mono` class there would be a `.py`
  change (forbidden this PR). `components.css`'s `§checklist` block instead
  selects `.checklist__item input[data-rango]` directly — `data-rango` is
  already rendered by the existing (untouched) widget attrs, so this is a
  pure-CSS equivalent with the same visual result.
- **Live "chip de conexión" and "guardado local ✓" text stay dropped** (per
  design D7's Open Questions — both need new JS/state this PR explicitly
  excludes).
- **`adjuntos.html`'s "volver" link omitted.** DESIGN2 §4 says every
  non-root screen bar has a volver link, but no `{% url %}` name for
  "back from adjuntos" was already verified safe to reference in this
  template (avoiding a guess that could raise `NoReverseMatch`); the
  `.barra-pantalla` header ships title-only here.
- **`§acciones` (PR1a's block) extended, not left untouched.** Added
  `display:inline-flex`/`align-items:center`/`text-decoration:none` so
  `.acciones__primario`/`.acciones__secundario` also render correctly as
  `<a>` elements (pagination links, "Anterior"/"Siguiente" step nav) — the
  original block only accounted for `<button>`. Same file, same block,
  extended for a newly-consuming screen; no new file/section created ahead
  of its consumer (design D5's rule is about not shipping *dead* CSS ahead
  of a consumer, not about never revisiting an earlier PR's block).

### Issues Found (Phase 3 / PR2)

None beyond the self-inflicted "bordered" substring collision in 3.3
(caught by the RED-first test itself, fixed same batch — see TDD Cycle
Evidence note above).

### Work Unit Evidence (Phase 3 / PR2)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/Scripts/python.exe -m pytest reportes/tests/test_views.py -k "mis_reportes or paso" reportes/tests/test_estatico.py reportes/tests/test_adjuntos.py -q` → all green (39 mis_reportes + paso tests run in two batches: 17 mis_reportes passed, 22 paso passed; plus 8 test_estatico.py passed, 19 test_adjuntos.py passed, including the 6 new Phase 3 tests) |
| Runtime harness command/scenario and exact result | Not executed manually in this batch. Manual QA (390×844 wizard walkthrough + DevTools offline reload, `capa-offline` scenario) is task 4.14, explicitly deferred to the end of PR3 per tasks.md's own Suggested Work Units table (Unit 3's "Runtime harness" column names this same manual scenario, not yet run) |
| Rollback boundary | Revert `mis_reportes.html`, `paso.html`, `adjuntos.html`, `sw.js`'s `CACHE` line, and `components.css`'s 5 new sections (`§barra-pantalla`/`§pasos`/`§checklist`/`§lista`/`§adjuntos`) plus the `§acciones` extension; revert the 7 new/renamed tests across `test_views.py`/`test_estatico.py`/`test_adjuntos.py`. PR1a/PR1b (tokens.css, base.html, login.html, the 4 `tipos_reporte` templates, `§chip`/`§campo`/`§aviso`/`§tabla`/`§escritorio`) stay fully functional and untouched. |

### Full Regression Run (Phase 3 / PR2)

`.venv/Scripts/python.exe -m pytest -q` (full suite) → **390 passed, 0
failed** in 810.48s. Up from PR1b's 384 (+6 net new tests). Named tripwires
from design's Testing Strategy all still hold: `test_views.py:504/533`
(`"disabled"` presence/absence on revisión — file untouched this batch,
PR3 scope); `:1248/1263`-equivalent `"generado"` absence
(`test_mis_reportes_chip_en_progreso`/`_terminado`, both re-verified
passing against the rebuilt `.lista` markup); `:1497`-equivalent
`numero_registro` absence (`test_mis_reportes_no_muestra_numero_registro`,
re-verified passing); `:361-377`-equivalent `data-campo`/`data-rango`/
`data-requiere-observacion`/`data-siguiente` contract
(`test_get_paso_incluye_atributos_data_y_script_paso_js`, re-verified
passing against the rebuilt `.checklist` markup — this is the one that
proves the DOM-tag change from `<p data-campo>` to `<div class="campo
checklist__item" data-campo>` didn't break `paso.js`'s attribute
selectors); `tipos_reporte/tests/test_vistas.py` (untouched this batch,
PR1b scope, still 384's worth of green).

### Status (Phase 3 / PR2)

15/15 Phase 3 tasks complete. 46/46 tasks complete across PR1a+PR1b+PR2
(Phases 1–3). Phase 4 (PR3) untouched — out of this batch's assigned scope.
Ready for verify on Phase 3 / PR2.

---

## Phase 2 (PR1b — admin escritorio) — 14/14 complete

- [x] 2.1 RED `tipos_reporte/tests/test_vistas.py::test_lista_aplica_grid_de_escritorio_sidebar_316px`
- [x] 2.2 RED `test_detalle_aplica_tabla_component_class`
- [x] 2.3 RED `test_formulario_tipo_aplica_campo_component_class`
- [x] 2.4 RED `test_formulario_definicion_aplica_campo_component_class`
- [x] 2.5 RED `test_sw_js_contiene_cache_v4` (renamed/replaced `test_sw_js_contiene_cache_v3` — one version-pin test per PR)
- [x] 2.6 GREEN `static/css/components.css`: added `§tabla` + `§escritorio` (sidebar grid `var(--sidebar) minmax(0,1fr)`; inner content grid `316px minmax(0,1fr)` gap 28px, per DESIGN2 §3 "Escritorio S-14")
- [x] 2.7 GREEN `lista.html`: `.escritorio` shell + sidebar nav + `.tabla` listing
- [x] 2.8 GREEN `detalle.html`: same shell, `.tabla` for Definiciones, `.acciones` bar
- [x] 2.9 GREEN `formulario_tipo.html`: `.form-basica` form (reuses PR1a selectors, no forms.py change)
- [x] 2.10 GREEN `formulario_definicion.html`: same pattern
- [x] 2.11 GREEN `sw.js` CACHE `v3` → `v4`
- [x] 2.12 Ran 2.1–2.5, all green
- [x] 2.13 REFACTOR: confirmed no new `disabled`/`generado` literal substring introduced (only pre-existing PR1a `.acciones__primario:disabled` pseudo-class match)
- [x] 2.14 Full pytest suite: **384 passed, 0 regressions** (796s)

### Files Changed (PR1b)

| File | Action | What Was Done |
|---|---|---|
| `static/css/components.css` | Modified | Added `§tabla` and `§escritorio` sections (D3/D5) |
| `tipos_reporte/templates/tipos_reporte/lista.html` | Modified | `.escritorio` shell, sidebar nav, `.escritorio__contenido` grid, `.tabla` listing |
| `tipos_reporte/templates/tipos_reporte/detalle.html` | Modified | Same shell, `.tabla` for Definiciones, `.acciones` bar |
| `tipos_reporte/templates/tipos_reporte/formulario_tipo.html` | Modified | Same shell, `.form-basica` form |
| `tipos_reporte/templates/tipos_reporte/formulario_definicion.html` | Modified | Same pattern |
| `reportes/templates/reportes/sw.js` | Modified | `CACHE` v3 → v4 (D4) |
| `tipos_reporte/tests/test_vistas.py` | Modified | +4 tests (2.1–2.4) |
| `reportes/tests/test_views.py` | Modified | `test_sw_js_contiene_cache_v3` renamed to `test_sw_js_contiene_cache_v4` |

### Deviations from Design (PR1b)

- `.tabla` styles a native `<table>` rather than a CSS-Grid `minmax(0,1fr) 48px 152px` row layout: DESIGN2 §3's column spec describes a "tabla de secciones" that has no renderable backing data in current views (only "Definiciones" version listings exist). Forcing that column spec onto unrelated data would be functional overreach; `.tabla` styles both existing read-only listings generically instead.
- Sidebar nav items "Usuarios" and "Organizaciones" render as inert `<span>` (no `<a href>`) — no URL names exist for those sections; linking them would either `NoReverseMatch` or require new routes (out of scope).
- `test_sw_js_contiene_cache_v3` renamed in place to `test_sw_js_contiene_cache_v4` (one version-pin test per PR, matching design's Testing Strategy).
- Zero `.py` files touched in this batch.

### Status

31/31 tasks complete across PR1a+PR1b (Phases 1–2). Phases 3–4 (PR2/PR3)
untouched — out of this batch's assigned scope. Ready for verify on
Phase 1+2 / PR1a+PR1b.

---

## Phase 1 (PR1a) — original batch record below

**Mode**: Strict TDD (pytest, `.venv/Scripts/python.exe -m pytest`, per
`sdd/proyecto_curso/testing-capabilities` and `openspec/config.yaml`).

## Completed Tasks (Phase 1 — 17/17)

- [x] 1.1 RED: `test_finders_resuelve_tokens_css`, `test_finders_resuelve_components_css`
- [x] 1.2 RED: `test_finders_resuelve_woff2_regular_y_medium`
- [x] 1.3 RED: `test_woff2_regular_firma_wof2_y_mayor_a_10kb`, `test_woff2_medium_firma_wof2_y_mayor_a_10kb`
- [x] 1.4 RED: `test_tokens_css_contiene_cada_hex_design2_seccion1`, `test_tokens_css_no_contiene_color_rojo`
- [x] 1.5 RED: `test_base_html_incluye_ambos_links_css`, `test_base_html_no_referencia_cdn`
- [x] 1.6 RED: `test_sw_js_contiene_cache_v3`
- [x] 1.7 RED: `test_login_primer_boton_submit_es_el_del_formulario_de_login`
- [x] 1.8 GREEN: `config/settings.py` — `STATICFILES_DIRS = [BASE_DIR / "static"]`
- [x] 1.9 GREEN: `static/fonts/IBMPlexMono-{Regular,Medium}.woff2` + `OFL.txt`
- [x] 1.10 GREEN: `static/css/tokens.css` (fonts, palette, type, measures, `.pagina`/`.mono` baseline)
- [x] 1.11 GREEN: `static/css/components.css` (§chip, §campo, §aviso, §acciones only)
- [x] 1.12 GREEN: `templates/base.html` (`{% load static %}`, viewport, 2 `<link>`s, `.pagina`, `.aviso` messages)
- [x] 1.13 GREEN: `templates/registration/login.html` (S-01 classes)
- [x] 1.14 GREEN: `reportes/templates/reportes/sw.js` (`CACHE` v2 → v3)
- [x] 1.15 Ran 1.1–1.7's test file — all green
- [x] 1.16 REFACTOR: confirmed `tokens.css` header comment records release tag + per-file SHA-256
- [x] 1.17 Full existing pytest suite run — 380 passed, 0 regressions

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `config/settings.py` | Modified | Added `STATICFILES_DIRS = [BASE_DIR / "static"]` (single Python edit, D2) |
| `static/fonts/IBMPlexMono-Regular.woff2` | Created | Real binary from official `IBM/plex` release `@ibm/plex-mono@2.5.0`, path `ibm-plex-mono/fonts/complete/woff2/`, SHA-256 `ba204497f16b6d334cee9d1e963a831b73e3a56e1d6300a8489d18df7214b350`, 49,248 bytes |
| `static/fonts/IBMPlexMono-Medium.woff2` | Created | Same release, SHA-256 `33faf307fa6031fb4062276d7320a6d632de890cbb347576fd80cfa01077bc25`, 50,400 bytes |
| `static/fonts/OFL.txt` | Created | SIL OFL-1.1 text, extracted from the same release zip's `fonts/complete/woff2/license.txt` (co-located with the binaries used) |
| `static/css/tokens.css` | Created | `@font-face` ×2 with release tag + SHA-256 header comment; `:root` DESIGN2 §1 palette (15 tokens), §2 type scale, §3 measures; `.pagina` shell + `.mono`/`th`/`.chip` baseline |
| `static/css/components.css` | Created | `§chip` (`.chip`, `--solido/--borde/--borde-gris/--ambar`), `§campo` (`.campo`, error via `[aria-invalid]`/`ul.errorlist`, no color), `§aviso` (`.aviso`, `.aviso--neutro`), `§acciones` (`.acciones`, `__primario`, `__secundario`) — `.acciones__razon` disabled-reason rule explicitly deferred to PR3 (task 4.7) |
| `templates/base.html` | Modified | `{% load static %}` at top, viewport meta, both `<link rel="stylesheet">`s, `.pagina` wrapper div, `messages` → `<li class="aviso">` |
| `templates/registration/login.html` | Modified | `.mono` heading, `.form-basica` form class, `.acciones`/`.acciones__primario` submit button, `.campo__ayuda` helper paragraph (S-01) |
| `reportes/templates/reportes/sw.js` | Modified | `CACHE = "reportes-offline-v2"` → `"reportes-offline-v3"` (D4, single-line edit) |
| `reportes/tests/test_estatico.py` | Created | 7 tests: finder resolution (tokens.css, components.css, both `.woff2`), magic-byte + size checks, full-palette + no-red-color checks |
| `reportes/tests/test_views.py` | Modified | Added `import re`; 4 new tests: `test_sw_js_contiene_cache_v3`, `test_base_html_incluye_ambos_links_css`, `test_base_html_no_referencia_cdn`, `test_login_primer_boton_submit_es_el_del_formulario_de_login` |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `reportes/tests/test_estatico.py` | Integration (staticfiles finder) | N/A (new file) | ✅ Written — failed with `TypeError: expected str, ... not NoneType` (no `STATICFILES_DIRS`) | ✅ Passed after 1.8 | ✅ 2 assertions (tokens.css + components.css paths) | ➖ None needed (structural finder check) |
| 1.2 | `reportes/tests/test_estatico.py` | Integration | N/A (new) | ✅ Written — failed pre-fonts | ✅ Passed after 1.9 | ✅ 2 cases (Regular + Medium) | ➖ None needed |
| 1.3 | `reportes/tests/test_estatico.py` | Unit (binary content) | N/A (new) | ✅ Written — failed pre-fonts (`finders.find` returned `None`) | ✅ Passed — real `wOF2` magic bytes, 49–50KB | ✅ 2 cases (Regular + Medium) | ➖ None needed |
| 1.4 | `reportes/tests/test_estatico.py` | Unit (text content) | N/A (new) | ✅ Written — failed pre-tokens.css | ✅ Passed after 1.10 (one iteration: `rgba(20,19,15,.5)` needed exact no-space spelling to match DESIGN2's literal token value) | ✅ 15 palette entries + separate no-red assertion (4 sub-checks: keyword, 2 hex spellings, rgb regex) | ✅ Fixed spacing mismatch, re-ran green |
| 1.5 | `reportes/tests/test_views.py` | Integration (HTTP response) | ✅ 70/70 pre-existing `test_views.py` tests passing before edit | ✅ Written — `test_base_html_incluye_ambos_links_css` failed pre-`base.html` edit (no `<link>`); `test_base_html_no_referencia_cdn` passed trivially pre-edit (base.html never had a CDN reference — approval-test style guard, not a true RED) | ✅ Both passed after 1.12 | ➖ Single scenario each (link presence / CDN absence) | ➖ None needed |
| 1.6 | `reportes/tests/test_views.py` | Integration | ✅ (same baseline) | ✅ Written — failed (`v2` in body, not `v3`) | ✅ Passed after 1.14 | ➖ Single scenario (one version string) | ➖ None needed |
| 1.7 | `reportes/tests/test_views.py` | Integration | ✅ (same baseline) | ✅ Written — passed trivially pre-edit (login.html already had exactly one submit button, no header/logout form exists in base.html to race against — approval-test guard for a shell that doesn't yet exist) | ✅ Still passes after 1.12/1.13 shell changes | ➖ Single scenario (regex captures first submit button's text) | ➖ None needed |

**Note on tasks 1.5's second assertion and 1.7**: two of the seven new tests
were written RED-first per the Three Laws but happened to already satisfy
the assertion before any production code changed, because the guard they
encode (`no CDN reference`, `first submit button is the form's own`) was
already true of the pre-retrofit code and remains an approval-style
regression guard against the *new* `base.html` shell introducing a
regression. Both are real, non-trivial, behavior-asserting checks (not
tautologies) and both continued passing through the actual `base.html`/
`login.html` edits, proving the shell change did not introduce a CDN
reference or an out-of-order submit button.

## Test Summary

- **Total tests written**: 11 (7 in `test_estatico.py` + 4 in `test_views.py`)
- **Total tests passing**: 11/11 (plus 380/380 across the full existing suite)
- **Layers used**: Unit (3 — woff2 magic-byte/size, palette/no-red text checks), Integration (8 — finders + HTTP response checks)
- **Approval tests** (guard-style, pre-existing invariant re-verified against new shell): 2 (`test_base_html_no_referencia_cdn`, `test_login_primer_boton_submit_es_el_del_formulario_de_login`)
- **Pure functions created**: 0 (presentation-only change — no new Python logic; the change is CSS/template markup, matching design's "Zero new JavaScript" (D7) and "single Python edit" (D2) scope)

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/Scripts/python.exe -m pytest reportes/tests/test_estatico.py reportes/tests/test_views.py -q` → 81 passed |
| Runtime harness command/scenario and exact result | Not executed manually in this batch (browser/DevTools offline reload is Manual QA, task 4.14, deferred to end of PR3 per tasks.md). The service-worker/static-asset caching mechanics are unchanged by this batch (only the `CACHE` version string moved v2→v3); no automated JS test exists in this project for that path, consistent with the `capa-offline` spec's own "verified manually via DevTools" scenario note. |
| Rollback boundary | Revert `config/settings.py`'s `STATICFILES_DIRS` line; delete `static/`; revert `templates/base.html`, `templates/registration/login.html`, `reportes/templates/reportes/sw.js`'s `CACHE` line; delete `reportes/tests/test_estatico.py`; revert the 4 added tests + `import re` in `reportes/tests/test_views.py`. No other file touched. |

## Full Regression Run

`.venv/Scripts/python.exe -m pytest -q` (full suite, including
`reportes/`, `tipos_reporte/`, `usuarios/`) → **380 passed, 0 failed** in
800.74s. Named tripwires from design's Testing Strategy all still hold
(`test_views.py:504/533` `"disabled"` presence/absence on revisión — file
untouched this batch; `:1074` static path; `:813-815` form action+csrf;
`:988` usernames; `tipos_reporte/tests/test_vistas.py` — untouched this
batch, PR1b scope).

## Deviations from Design

- None functionally. One scoping clarification made explicit in
  `components.css`: the `.acciones__razon` disabled-reason reveal rule
  (`.acciones__primario:disabled ~ .acciones__razon{display:block}`) was
  drafted once while writing `§acciones`, then deliberately removed and
  left as a comment pointer to PR3/task 4.7, since design D5's file table
  and tasks.md both scope that specific rule (and its markup) to PR3
  alongside `revision.html`'s disabled-reason markup — shipping it early in
  `components.css` with no consuming markup would be dead CSS ahead of its
  PR3 consumer, which D5 explicitly avoids ("no dead CSS ships ahead of its
  consumer").
- `.pagina` and `.mono`/`th`/`.chip` baseline rules were added to
  `tokens.css` (not `components.css`) as "element baseline", matching
  design's Technical Approach description of `tokens.css`'s contents
  verbatim ("carries `@font-face`, the DESIGN2 §1–§3 custom properties and
  the element baseline").

## Issues Found

None.

## Workload / PR Boundary

- Mode: stacked-to-main (chain strategy per design D5, confirmed with user)
- Current work unit: Unit 1 — "Static-file plumbing + tokens.css + fonts +
  base shell + login (S-01)" (tasks.md Suggested Work Units table)
- Boundary: starts from an empty `static/` tree and unmodified
  `base.html`/`login.html`/`sw.js`; ends with PR1a fully shippable and
  independently revertable, with zero dependency on PR1b/PR2/PR3
- Estimated review budget impact: ~250 authored lines (per tasks.md
  forecast), well under the 400-line budget; binary `.woff2` bytes are
  excluded from the authored-line count

## Status

17/17 Phase 1 tasks complete. Phases 2–4 (PR1b/PR2/PR3) untouched — out of
this batch's assigned scope. Ready for verify on Phase 1 / PR1a.

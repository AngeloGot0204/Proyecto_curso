# Design: Validación de datos del formulario

## Technical Approach

Three mechanisms, one per TECH-DESIGN rule (proposal Approach 3): a new pure-ish module `reportes/validacion.py` that re-reads persisted `ValorDeReporte` rows and returns two buckets; a new S-09 `revision` view/template that renders them; and a vanilla-JS layer in `paso.html` for immediate hora-range feedback and `_observacion` toggling. `paso`'s POST branch is **not** touched — D8's non-blocking contract and `test_post_paso_sin_valor_obligatorio_no_bloquea` stay literally unchanged.

## Architecture Decisions

### Decision: Obligatorio reuse via `_validar_completitud` exception translation

| Option | Tradeoff |
|---|---|
| Import `generador._validar_completitud`, catch `ValoresIncompletos`, map `.faltantes` → errores | Zero drift *by construction* (same function, same membership semantics); crosses a `_`-private boundary; exception as control flow |
| Extract a public `faltantes_obligatorios()` in `generador.py`, call from both | Cleaner API, but modifies `generador.py` — proposal's Affected Areas pins it as "Referenced, not modified" |
| Re-walk `_iterar_nodos` + `nodo.get("obligatorio")` in `reportes` | Rejected: exactly the drift the proposal forbids |

**Choice**: option 1. `validar_reporte` builds `valores` from the rows, calls `_validar_completitud(estructura, valores)` inside `try/except ValoresIncompletos`, and turns `error.faltantes` into errores entries. Our own traversal supplies only *presentation* metadata (`seccion_id`, label) — never the required/not-required decision. A locking test asserts both agree (spec scenario 3). If `generador.py` is ever refactored, promote to option 2.

### Decision: server-side hora re-check lives only in `validar_reporte`

`paso` POST gains no check. A POST-time check that neither blocks (D8) nor persists a flag would be dead code; the persisted stray value is caught at the S-09 gate, which is where the flag is consumed. This *is* the defense in depth: the server never trusts JS because `validar_reporte` re-derives the verdict from persisted rows. Refines the proposal's Affected Areas wording (views.py POST unchanged) with the same guarantee and less regression surface.

### Decision: "No cumple" = `seleccion` nodes only, exact string

Match `tipo == SELECCION and valor == "No cumple"` (exact, case-sensitive, on the persisted string). `texto` fields rejected: free prose has no closed option catalog and would false-positive. Companion row key `f"{nodo['id']}_observacion"`, reusing the proven suffix pattern from `rango-hora-inicio-fin`.

### Decision: `_observacion` as a real form field, not view-special-cased

`construir_formulario_seccion` injects the companion `CharField` into the section form. `paso`'s existing `for nombre_campo in form.fields` loop then persists and rehydrates it with **zero view changes**. It is not an `estructura` node, so `_validar_completitud` never requires it and `_escribir_valores` never writes it (no `celda`).

## Interfaces / Contracts

```python
# reportes/validacion.py — mirrors tipos_reporte.validacion's frozen-dataclass
# + stable `regla` id convention.
_VALOR_NO_CUMPLE = "No cumple"
_SUFIJO_DE_ETIQUETA = {"_inicio": " — Inicio", "_fin": " — Fin"}

@dataclass(frozen=True)
class ProblemaDeReporte:
    regla: str          # valor-obligatorio-faltante | rango-hora-invalido | no-cumple-sin-observacion
    identificador_de_campo: str   # the exact ValorDeReporte key → anchor #id_<key>
    seccion_id: str               # → reverse("reportes_paso", [reporte.id, seccion_id])
    etiqueta: str                 # human link text
    mensaje: str                  # reworkable prose; never asserted in tests

@dataclass(frozen=True)
class ResultadoDeRevision:
    errores: tuple[ProblemaDeReporte, ...]
    advertencias: tuple[ProblemaDeReporte, ...]
    @property
    def puede_generar(self) -> bool: return not self.errores

def validar_reporte(reporte) -> ResultadoDeRevision: ...
```

Named `ResultadoDeRevision`, not `ResultadoDeValidacion`, to avoid shadowing `tipos_reporte.validacion.ResultadoDeValidacion`.

## Data Flow

```
ValorDeReporte rows ──→ valores {clave: texto}
estructura ──→ _indice_de_campos() {clave: (seccion_id, etiqueta, nodo)}
      │            (per section: _iterar_nodos({"secciones": [seccion]}), claves_de_valor(nodo))
      ├─→ generador._validar_completitud(estructura, valores)
      │        └─ ValoresIncompletos.faltantes ──→ errores  (via índice for metadata)
      ├─→ rango nodes: desde_texto(TimeField(), fin) <= inicio ──→ advertencias
      └─→ seleccion nodes: valores[id] == "No cumple"
               and not valores.get(f"{id}_observacion","").strip() ──→ advertencias
                                                                          │
   revision view ──→ revision.html (2 lists, Generar disabled iff errores) ┘
```

`validar_reporte` algorithm, in order: (1) `valores = {v.identificador_de_campo: v.valor for v in ValorDeReporte.objects.filter(reporte=reporte)}` — one query; membership means "provided", since `guardar_valor` deletes empties. (2) Build `_indice_de_campos`. (3) Obligatorio pass (above). (4) For each `RANGO_HORA_INICIO_FIN` node, take `claves_de_valor(nodo)` → `(inicio, fin)`; if both present, parse via `desde_texto(forms.TimeField(), texto)` (same-field-parses-back rule, design D2); skip if either parses to `None`; if `fin <= inicio` append an advertencia keyed on the `_fin` clave. (5) "No cumple" pass. Errores and advertencias are each returned in `estructura` order (wizard order).

## File Changes

| File | Action | Description |
|---|---|---|
| `reportes/validacion.py` | Create | `validar_reporte`, `ProblemaDeReporte`, `ResultadoDeRevision`, `_indice_de_campos` |
| `reportes/views.py` | Modify | Add `revision` view only (`@login_required` + `get_object_or_404(Reporte, pk=…, creador=request.user)`, per D9); `paso` untouched |
| `reportes/urls.py` | Modify | `path("<int:reporte_id>/revision/", views.revision, name="reportes_revision")` |
| `reportes/templates/reportes/revision.html` | Create | Two `<ul>`s; `<button type="button" {% if not puede_generar %}disabled{% endif %}>Generar</button>` |
| `reportes/templates/reportes/paso.html` | Modify | Wrap each field in `<p data-campo="{{ campo.name }}">`; `{% load static %}` + `<script src="{% static 'reportes/paso.js' %}" defer></script>`; `data-siguiente` on the nav anchor |
| `reportes/static/reportes/paso.js` | Create | Vanilla JS (ADR-0001: no library, no build step) |
| `reportes/formularios.py` | Modify | Range widget attrs; `_observacion` companion field + `data-requiere-observacion` |
| `reportes/tests/conftest.py` | Modify | `estructura_con_validaciones` fixture |
| `reportes/tests/test_validacion.py` | Create | TDD unit tests |
| `reportes/tests/test_views.py` | Modify | S-09 view tests + a D8 regression test for the new rule |

### `formularios.py` changes (the JS contract)

- `_campos_de_rango`: each `TimeField` widget gets `attrs["data-rango"] = nodo_id` and `attrs["data-rango-extremo"] = "inicio" | "fin"` (signature grows a `nodo_id` param). JS groups by attribute, not by name-suffix guessing.
- `construir_formulario_seccion`, when `tipo == SELECCION and _VALOR_NO_CUMPLE in (opciones or [])`: the select gets `attrs["data-requiere-observacion"] = f"{id}_observacion"`, and a companion `forms.CharField(required=False, label=f"{etiqueta} — Observación", widget=TextInput(attrs={"data-observacion-de": clave}))` is added right after it. `required=False` in Python is mandatory (D8); the JS toggles the *HTML* `required` attribute only.

### `paso.js` behaviour

`DOMContentLoaded` → run both toggles once (covers GET rehydration), then bind `change`/`input`.
- **Rango**: group `[data-rango]` inputs by value. `<input type="time">` values are `"HH:MM"` strings, so a plain lexicographic `fin <= inicio` comparison is exact — no parsing. On violation: set `aria-invalid`, show a `role="alert"` message next to the `fin` input, `disabled = true` on the form's submit button, and `aria-disabled="true"` + a `preventDefault` click guard on the `[data-siguiente]` anchor. Any pair invalid disables; all valid re-enables.
- **No cumple**: for each `[data-requiere-observacion]` select, find `p[data-campo="<value>"]`; if `select.value === "No cumple"` → unhide + set `input.required = true`; else → hide, clear `input.value`, and **always** remove `required` (a hidden `required` input would block native submission).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `validar_reporte` — 6 spec scenarios | `@pytest.mark.django_db`, new `estructura_con_validaciones` fixture (obligatorio `texto`, `seleccion` with `["Cumple","No cumple"]`, obligatorio `rango-hora-inicio-fin`) passed to `tipo_con_definicion_activa_factory(estructura=…)` + `reporte_factory`; `ValorDeReporte.objects.create(...)` directly to set up persisted state |
| Unit | Anti-drift lock | One test calls `validar_reporte` and `_validar_completitud` on the same `valores`; asserts `{e.identificador_de_campo for e in errores if e.regla=="valor-obligatorio-faltante"} == set(exc.faltantes)` |
| Integration | S-09 view | Reuse `sesion_de_creador`/`cliente_autenticado`: 200 for creador, 404 for another user (D9), redirect for anon; `assertContains` the `reportes_paso` link URL; `disabled` present iff errores |
| Integration | `formularios.py` attrs | Assert `f"{id}_observacion" in form.fields` and that `paso` GET HTML contains `data-rango` / `data-requiere-observacion` |
| Regression | D8 | `test_post_paso_sin_valor_obligatorio_no_bloquea` unchanged; new `test_post_paso_con_rango_invalido_no_bloquea` asserts 302 + both values persisted |
| JS | — | No JS test runner exists in the project; JS is covered only by asserting the rendered contract (attributes + `<script>` tag). Explicitly accepted. |

## Threat Matrix

N/A — no shell command, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The new URL is a Django route, not filesystem/`git` path routing. Web-boundary notes: the `revision` view reuses `paso`'s creator-scoped `get_object_or_404` (a foreign `Reporte` 404s exactly like a nonexistent one, leaking nothing); all problem text renders through Django's default autoescaping; no new deserialization surface.

## Migration / Rollout

No migration required. `{id}_observacion` reuses the existing `ValorDeReporte` key pattern.

## Open Questions

- [ ] `{id}_observacion` has no `celda`, so it is captured but never written to the `.xlsx`. Accepted for this change (generation is #7); a future definition-schema key would be needed to place it.
- [ ] `_SUFIJO_DE_ETIQUETA` restates the `" — Inicio"/" — Fin"` labels already in `formularios._campos_de_rango`. Accepted duplication (two literals, no logic); factor out only if a third consumer appears.

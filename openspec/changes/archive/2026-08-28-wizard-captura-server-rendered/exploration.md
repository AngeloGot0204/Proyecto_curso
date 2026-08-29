# Exploration: Wizard de captura server-rendered (backlog #5)

## Current State

**ADR-0001** settles the wizard's architecture: Django reads the declarative `DefinicionDeTipo` (backlog #3) and **renders the complete wizard form as HTML server-side** — never ships YAML/JSON to the browser for client-side interpretation. That same server-rendered HTML is what the future offline service worker (ADR-0004/backlog #9) will cache — out of scope here, but the reason rendering is constrained to "one HTML document, no client-side templating engine."

Strong-field validation happens on sync per ADR-0001; backlog explicitly separates "renders the multi-step form" (#5) from "field validation" (#6). TECH-DESIGN.md's "Validación de datos" acceptance criteria belong to #6, not #5.

**`DefinicionDeTipo.estructura` schema** (confirmed in `tipos_reporte/tests/conftest.py::definicion_valida`, `tipos_reporte/validacion.py`):

```json
{
  "tipo": "instalacion-resinas",
  "plantilla": "JME.PC-0001.F1.xlsx",
  "hoja": "REPORTE",
  "secciones": [
    {"id": "datos-generales", "titulo": "Datos generales",
     "campos": [{"id": "turno", "etiqueta": "Turno", "tipo": "seleccion",
                 "opciones": ["Día", "Noche"], "obligatorio": true, "celda": "M12"}]},
    {"id": "proceso-instalacion", "titulo": "Proceso de instalación",
     "roles": ["construccion-jme", "qa-subterra"],
     "items": [{"id": "p-01", "texto": "Se verifica ángulo de perforación.",
                "tipo": "rango-hora-inicio-fin", "celda_inicio": "M25", "celda_fin": "P25"}]}
  ]
}
```

Two node shapes per `seccion`: `campos` (label key `etiqueta`) and `items` (label key `texto`). `roles` on a section is descriptive metadata only — ADR-0006 already settled that editing is open, not role-restricted, so the wizard can ignore `roles` for rendering.

**Closed `TipoDeDato` catalog** and what each needs to render:

| `tipo` | Needed keys | Natural HTML control |
|---|---|---|
| `texto` | `celda` | `<input type="text">` |
| `numero` | `celda` | `<input type="number">` |
| `fecha` | `celda` | `<input type="date">` |
| `hora` | `celda` | `<input type="time">` |
| `seleccion` | `celda`, `opciones` (required by R1) | `<select>` |
| `booleano` | `celda` | checkbox or Sí/No radio — **unspecified, open decision** |
| `rango-hora-inicio-fin` | `celda_inicio`, `celda_fin` (no single `celda`) | two `<input type="time">` — composite item, ties to #4's value-contract decision (two independent keys) |

`obligatorio` (bool) can mark an input `required`/starred for UX, but enforcing it server-side is #6's job. `id` is the stable key for `<name>` and future `ValorDeReporte.identificador_de_campo`.

**`Reporte`/`ValorDeReporte` do NOT exist yet** — confirmed: only `usuarios/models.py` and `tipos_reporte/models.py` exist; `INSTALLED_APPS` lists only those two apps. Matches #4's own exploration finding. **#5 is the natural first owner** since the wizard needs somewhere to persist step data.

**TECH-DESIGN.md** highlights:
- `Reporte`: local-origin idempotency ID and `numero_registro` via DB sequence belong to ADR-0004/offline (#9/#10), not #5 (no offline yet). `tipo`, `creador`, `fecha`, closure state, and the **`DefinicionDeTipo` version active at creation** are #5-relevant.
- `ValorDeReporte`: generic storage — reporte, field id, value, author, date; no role field (ADR-0006, open editing).
- Lifecycle: `borrador local → en progreso (sincronizado) → completo → terminado (visto bueno) → generado`. Without offline, every `Reporte` #5 creates is already server-persisted — effectively starts at/near `en progreso`.
- "Navegar hacia atrás entre pasos sin perder datos" is listed under offline acceptance but is a baseline usability bar #5 must meet regardless.
- #5's core acceptance criterion verbatim: server-rendered wizard, no per-tipo code.

**`usuarios` app conventions**: `usuarios/views.py::inicio` — thin FBV, `@login_required`, explicit scope-guard docstring ("this view must accumulate no X-domain logic … backlog item #N replaces it"). `usuarios/urls.py` — flat `path()` list, `include()`d from `config/urls.py`, no namespacing. Session auth via `django.contrib.auth`, `SESSION_COOKIE_AGE = 604800`. No existing precedent for multi-step/session-draft state — the wizard is the first place this is needed; `django-formtools` is not in `requirements.txt`.

**Templates/static**: `templates/base.html` is bare HTML5 with `title`/`extra_head`/`content` blocks, no CSS framework, no JS bundler (ADR-0001 explicitly: "sin frameworks de frontend ni build pipeline"). `TEMPLATES.DIRS` + `APP_DIRS=True` both work but `usuarios` keeps templates project-level, so no per-app-template precedent yet.

**Test conventions**: pytest-django, `@pytest.mark.django_db`/`db` fixture, `client.login()` + `client.post(reverse(...))` pattern, fixture-factory-returns-fresh-copy pattern. Strict TDD enabled project-wide.

## Affected Areas
- New app (e.g. `reportes/`) — `models.py` (`Reporte`, `ValorDeReporte`), `views.py`, `urls.py`, `templates/reportes/*.html`.
- `config/settings.py` — register new app in `INSTALLED_APPS`.
- `config/urls.py` — `include()` new app's urls.
- `tipos_reporte/models.py` (read-only) — `DefinicionDeTipo.estructura`/`TipoDeDato` are the render source.
- `templates/base.html` — may gain new blocks for step-navigation shell.
- `adrs/0001-arquitectura-de-componentes.md`, `TECH-DESIGN.md` — authoritative constraints.

## Recommended Approach
Custom multi-step view: one URL per section, one Django `Form` built dynamically per section from `campos`/`items`, `ValorDeReporte` upserted per step's POST. No new dependency (matches ADR-0001's "no frontend framework, minimal JS" constraint), per-step DB persistence (not session) is offline-migration-friendly later, independently testable steps.

Rejected: `django-formtools SessionWizardView` (new dependency; session-bound data isn't durable until final submit, working against future offline/sync needs). Rejected: single long form with JS-only step switching (conflicts with "back navigation must not lose data"; no natural partial-save point).

## Open Decisions (must be settled in proposal/design)
1. `Reporte`/`ValorDeReporte` field shape (`Reporte.tipo`, `creador`, `estado`, `definicion` FK to the version active at creation; `ValorDeReporte.reporte`, `identificador_de_campo`, `valor`, `autor`, `fecha`).
2. `rango-hora-inicio-fin` value contract in `ValorDeReporte` rows — two independent rows (`{id}_inicio`/`{id}_fin`), consistent with #4's decision for the generator's values dict.
3. `booleano` rendering: checkbox vs. Sí/No radio.
4. Per-step form-construction strategy (dynamic Django `Form` from `estructura` node list).
5. Explicit non-goals list: no required-field blocking, no "No cumple" warnings, no visto bueno gating, no invitation/permission checks beyond "creator only" — all reserved for #6/#7/#8.
6. `obligatorio` boundary: #5 may mark fields visually/`required` HTML attribute only; server-side blocking-on-missing-value belongs to #6.

## Risks
- `Reporte`/`ValorDeReporte` don't exist yet — #5 is the first item that must define their shape, and #7/#8/#9 all depend on getting this right the first time.
- `rango-hora-inicio-fin` value contract still undecided at the model layer (flagged by #4's exploration too).
- No established per-app-template or CSS/JS convention exists to build a genuinely multi-step, mobile-usable wizard on top of.
- `booleano` rendering unspecified by both `TipoDeDato` and TECH-DESIGN.md.
- Scope-creep risk: TECH-DESIGN.md interleaves wizard/validation/offline/collaboration acceptance criteria in prose — the proposal must explicitly exclude #6/#7/#8/#9 concerns.

## Key Learnings
1. `Reporte` and `ValorDeReporte` still do not exist anywhere in the repo as of backlog #5's exploration, confirming #4's earlier finding.
2. ADR-0001 explicitly frames the wizard as fully server-rendered HTML with no client-side interpretation of the JSON definition, and that same HTML is what offline caching (ADR-0004) will later reuse.
3. `DefinicionDeTipo.estructura` nodes split into `campos` (label key `etiqueta`) and `items` (label key `texto`), and `rango-hora-inicio-fin` is the only type using `celda_inicio`/`celda_fin` instead of a single `celda`.
4. No per-app-template, CSS, or JS convention exists in the repo yet; `usuarios` keeps templates project-level with zero styling, and ADR-0001 forbids any frontend framework or build pipeline.

**Next**: sdd-propose

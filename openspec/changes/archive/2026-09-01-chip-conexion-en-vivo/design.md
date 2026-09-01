# Design: Live Connection Chip in Screen Bar

## Technical Approach

One dedicated vanilla-JS IIFE (`static/js/conexion-chip.js`) renders the
`.barra-pantalla` connection chip. It is loaded once from `templates/base.html`
with `defer`, so it runs after DOM parse and before `DOMContentLoaded` — the
synchronous initial `navigator.onLine` read the spec requires, with no event
wait. It then binds `online`/`offline` on `window`; both handlers re-read
`navigator.onLine` (single source of truth) and repaint the same node.

The chip markup lives in one shared partial (`templates/_chip_conexion.html`)
included by the three templates that render `.barra-pantalla`
(`paso.html`, `mis_reportes.html`, `adjuntos.html`), in DESIGN2 §4 bar order:
volver · título · indicador · **conexión** · avatar. `login.html` has no bar,
includes nothing, and the script no-ops there (Scenario "Chip does not appear
on the login screen"). ADR-0001 holds: no framework, no build step, no new
dependency, no backend change.

## Architecture Decisions

### Decision: Script included once in `base.html`, not per template

**Choice**: `<script src="{% static 'js/conexion-chip.js' %}" defer>` in
`base.html` `<head>`.
**Alternatives considered**: a `{% block extra_head %}` tag repeated in each of
the three bar templates.
**Rationale**: the per-template variant drifts — a new bar screen silently
ships a dead chip. `defer` guarantees the chip node exists at run time, matching
`paso.html`'s existing `defer` convention. Cost is one extra ~1KB request on
`login.html`, where the module returns immediately.

### Decision: Chip renders `hidden`, JS reveals it

**Choice**: the partial ships `hidden` with no state class; JS sets state, then
removes `hidden`.
**Alternatives considered**: server-render a default `en línea` chip and let JS
correct it.
**Rationale**: the server cannot know client connectivity. A default `en línea`
chip is a lie with JS disabled; a hidden chip degrades to "no claim", the honest
option for a field tool whose whole premise is that offline is normal.

### Decision: Reuse `.chip--borde` / `.chip--borde-gris`, no new class

**Choice**: `offline` → `.chip .chip--borde` (borde negro, DESIGN2 §4 weight for
`offline`); `en línea` → `.chip .chip--borde-gris` (neutral weight). One new
layout-only rule `.barra-pantalla__conexion { flex-shrink: 0; }`.
**Alternatives considered**: hide the chip entirely when online.
**Rationale**: hiding causes a bar-layout jump on every state flip and makes the
login-screen scenario untestable by presence. No new visual language is added.

### Decision: Strict isolation from `paso-offline.js`

**Choice**: separate file, separate IIFE, no `window.*` export, DOM contract
`[data-chip-conexion]` only.
**Rationale**: `paso-offline.js` registers **no** `online`/`offline` listener —
its `navigator.onLine` read is one-shot inside `intentarEnvio()` at submit time
(`paso-offline.js:186`), and its UI lives in `[data-borrador-banner]` /
`[data-borrador-prompt]` nodes inserted before the `<form>`. The only shared
surface is a read-only `navigator.onLine` read. Disjoint DOM, disjoint globals,
disjoint events — the chip cannot alter submit gating or draft state.

**ADR/decision deviation flagged**: this supersedes the archived
`retrofit-visual-design2` D7 ("zero new JavaScript") and the
`components.css` §barra-pantalla comment "No live chip de conexión (D7)", which
must be updated in the same change. ADR-0004 is extended in visibility only.

## Data Flow

    load ──→ conexion-chip.js (defer)
                │ read navigator.onLine (sync)
                ▼
         [data-chip-conexion] ──→ class + text + unhide
                ▲
    window "online"/"offline" ──┘ (re-read navigator.onLine)

    paso-offline.js ──→ [data-borrador-*]   (independent, submit-time only)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `static/js/conexion-chip.js` | Create | IIFE: sync init read + `online`/`offline` listeners |
| `templates/_chip_conexion.html` | Create | Shared hidden chip node |
| `templates/base.html` | Modify | `defer` script tag in `<head>` |
| `reportes/templates/reportes/paso.html` | Modify | Include partial after `__indicador` |
| `reportes/templates/reportes/mis_reportes.html` | Modify | Include partial before `__avatar` |
| `reportes/templates/reportes/adjuntos.html` | Modify | Include partial after `__titulo` |
| `static/css/components.css` | Modify | `.barra-pantalla__conexion` flex rule; fix stale D7 comment |
| `reportes/tests/test_estatico.py` | Modify | Static-asset + module-contract assertions |
| `reportes/tests/test_views.py` | Modify | Chip presence on 3 screens, absence on login |

## Interfaces / Contracts

```html
<span class="chip barra-pantalla__conexion" data-chip-conexion hidden></span>
```

```js
// state → (class, text); textContent only, never innerHTML (no user data)
offline    → "chip chip--borde"       "offline"
en línea   → "chip chip--borde-gris"  "en línea"
// data-estado="offline|en-linea" mirrors state for tests/CSS hooks
```

## Testing Strategy

No JS test runner exists in this project (precedent: `paso-offline.js` header).

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (static) | `finders.find("js/conexion-chip.js")` resolves; source contains `navigator.onLine`, both `addEventListener` events, `textContent`, no `data-borrador-` reference | `test_estatico.py`, mirroring existing finder/content tests |
| Integration | Chip node present in `paso`/`mis_reportes`/`adjuntos` responses in DESIGN2 bar order; absent on `/login/`; script tag present in `base.html` output | `test_views.py` Django test client |
| Manual | Initial state offline/online; live flip via DevTools throttling; `paso-offline.js` banner unchanged during flips | DevTools script in `tasks.md` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Chip text is a static literal
written with `textContent`; no user input reaches the DOM.

## Migration / Rollout

No migration required. Rollback = revert the two new files and the template/CSS
edits; no state to reconcile.

## Open Questions

- None blocking.

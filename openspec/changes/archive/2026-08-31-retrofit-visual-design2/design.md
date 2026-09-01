# Design: Visual retrofit to DESIGN2 (S-01…S-14, backlog #15)

## Technical Approach

Two hand-written stylesheets and zero new JavaScript. `static/css/tokens.css`
carries `@font-face`, the DESIGN2 §1–§3 custom properties and the element
baseline; `static/css/components.css` carries the 8 DESIGN2 §4 blocks. Both are
linked once from `templates/base.html`; the other 10 templates only gain class
attributes. Every *dynamic* visual state binds to an attribute the existing code
already sets (`:disabled`, `[aria-invalid]`, `[data-borrador-banner]`,
`ul.errorlist`), so no `.py` and no `.js` file changes behaviour. The single
Python edit is `STATICFILES_DIRS` (D2); the single `sw.js` edit is the cache
version (D4). Delivered as 3 stacked-to-main PRs (D5).

## Architecture Decisions

### D1 — `tokens.css`: one `:root`, Spanish names mirroring DESIGN2's tables

| Option | Tradeoff |
|---|---|
| Generic English tokens (`--color-bg`, `--color-ink`) | Breaks the 1:1 diff against DESIGN2 §1's own token column; the repo is Spanish-first in every identifier |
| Per-screen token files | 11 `<link>`s / SW entries, no build step to concatenate |
| **Chosen**: single `:root`, `--{grupo}-{nombre DESIGN2}` | Matches the spec's own examples (`var(--color-tinta)`, `var(--color-ambar-borde)`); a reviewer checks the file row-by-row against §1 |

Groups, in DESIGN2 section order. **Color (§1)**: `--color-fondo` `#f4f3f1`,
`--color-superficie` `#ffffff`, `--color-tinta` `#14130f`, `--color-tinta-2`
`#4a463f`, `--color-tinta-mono` `#6f6a61`, `--color-linea` `#d9d5cf`,
`--color-linea-interna` `#eeece8`, `--color-bloqueado-fondo` `#d9d5cf`,
`--color-bloqueado-texto` `#8b867d`, `--color-ambar-borde` `#b06a00`,
`--color-ambar-borde-suave` `#e0bd7c`, `--color-ambar-fondo` `#fdf1dc`,
`--color-ambar-texto` `#7a5a1c`, `--color-velo` `rgba(20,19,15,.5)`,
`--color-punteado` `#a8a29a`. **Type (§2)**: `--fuente-ui`, `--fuente-mono`,
`--txt-login|titulo-escritorio|titulo|wizard|valor|tarjeta|etiqueta`
(26/22/19/17/16/14/13px), `--mono-paso|meta|chip` (12/11/10px), `--ls-chip`.
**Measure (§3)**: `--pad-lateral|lista`, `--gap-1…4`,
`--alto-campo|boton|casilla|fila|barra`, `--pad-scroll`, `--sidebar`,
`--borde`, `--borde-error`. No `prefers-color-scheme`, no breakpoint overrides
of colour: §1 states "ningún otro color".

### D2 — Self-hosted fonts + the `STATICFILES_DIRS` prerequisite

`config/settings.py` defines only `STATIC_URL`/`STATIC_ROOT`, so the project
runs on `AppDirectoriesFinder` alone. **A repo-root `static/` directory is
invisible to `{% static %}` and to `collectstatic` today** — the spec's paths
404 in production without `STATICFILES_DIRS = [BASE_DIR / "static"]`. That one
line ships in PR1. Alternatives rejected: parking shared assets in
`reportes/static/reportes/` (wrong ownership — `base.html`, `login.html` and
`tipos_reporte` are not `reportes`) and creating a `ui` Django app for two files.
WhiteNoise's `CompressedStaticFilesStorage` skips already-compressed `.woff2`
and gzips the CSS; `vercel.json` already runs `collectstatic`.

Fonts: two faces only, matching §2's "IBM Plex Mono 400/500" —
`static/fonts/IBMPlexMono-Regular.woff2`, `IBMPlexMono-Medium.woff2`, plus
`static/fonts/OFL.txt` (OFL-1.1 requires shipping the licence). Sourced by hand
once from the official `IBM/plex` GitHub release
(`IBM-Plex-Mono/fonts/complete/woff2/`); the release tag and each file's
SHA-256 are recorded in `tokens.css`'s header comment so a reviewer can
re-download and compare bytes. Rejected: Google Fonts CDN (spec forbids; breaks
offline-first), third-party subsetter services (unverifiable provenance),
`fonttools`/`pyftsubset` subsetting (introduces a build step and a dev
dependency into a build-less project).

```css
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:400;
  src:url("../fonts/IBMPlexMono-Regular.woff2") format("woff2");font-display:swap}
```

`font-display: swap` over `optional`/`block`: field metadata must be legible
immediately, and only 10–12px mono runs reflow. After the first online visit the
SW serves the font from cache, so the swap flash is a one-time cost. `--fuente-ui`
needs no asset: `"Helvetica Neue", Helvetica, Arial, system-ui, sans-serif`.

### D3 — `components.css`: BEM-lite, Spanish blocks, descendant selectors

| Option | Tradeoff |
|---|---|
| Hand-written utility layer | No preprocessor and no purge step: unbounded, untraceable, and 6–10 classes per element inflate every template diff against the 400-line budget |
| Per-widget classes via `attrs={"class": …}` | Requires editing `reportes/forms.py` / `tipos_reporte/forms.py` — Python changes in a presentation-only change |
| **Chosen**: 8 BEM blocks (`bloque__elemento--modificador`), one file section per DESIGN2 §4 component, styling native controls as descendants | One class per component, 1:1 reviewable against §4; `{{ campo }}` / `{{ form.as_p }}` keep rendering Django's default widgets untouched |

Blocks: `.barra-pantalla`, `.pasos`, `.campo`, `.checklist`, `.chip`, `.aviso`,
`.acciones`, `.hoja`. Controls are reached as `.campo input, .campo select,
.campo textarea`; `as_p` output as `.form-basica p`; JS-injected DOM by
attribute selector (`[data-borrador-banner]`, `[data-borrador-prompt]`) so
`paso-offline.js` is never edited. `:has()` is not used for anything
load-bearing (field-device Safari floor); `:disabled`, `[aria-invalid]`,
`:checked` and sibling combinators cover every live state.

### D4 — Service worker: no precache list, bump `CACHE` per PR

`sw.js` has **no precache** — `install` only calls `skipWaiting()`, and every
`/static/` GET is already cache-first at runtime (`sw.js:112-135`). The new CSS
and `.woff2` match `pathname.indexOf("/static/") === 0` the moment the browser
requests them, so the `capa-offline` delta is satisfied with **zero** logic
change. The only edit is `var CACHE = "reportes-offline-v2"` → `v3` (PR1), `v4`
(PR2), `v5` (PR3): filenames are unhashed (`CompressedStaticFilesStorage`, not
the Manifest variant), so cache-first would otherwise serve a returning user
last PR's `components.css` forever. `activate` already deletes every non-current
cache. No deviation from ADR 0004 — network-first for step HTML, cache-first for
statics, GET-only, version-bump invalidation all stand.

Rejected: `install`-time `cache.addAll([...])` (a single 404 rejects the install
and kills the whole SW, and it widens the cache scope the delta forbids);
switching to `CompressedManifestStaticFilesStorage` (deploy-wide storage change
with strict-reference failures — recorded as a follow-up); `?v=` query strings
(hand-maintained duplicate of the CACHE bump). Carried-over limitation: assets
cache lazily, so a first-ever visit made offline renders unstyled — identical to
today's `paso.js` behaviour and already worded into the delta scenario.

### D5 — PR chain (stacked-to-main), sliced by CSS dependency

**Confirmed with user**: PR1 split into PR1a/PR1b — foundation and admin desktop
are different review surfaces (global visual base vs. an isolated desktop-only
screen set), and splitting keeps each PR in-focus and independently revertable
without waiting on a `size:exception`.

| PR | Ships | Est. authored lines |
|---|---|---|
| **PR1a** cimientos | `STATICFILES_DIRS`; `static/fonts/*` (binary, 0 diff lines) + `OFL.txt`; full `tokens.css`; `components.css` §chip/§campo/§aviso/§acciones; `base.html` shell; `login.html` (S-01); `CACHE`→v3 | ~250 |
| **PR1b** admin escritorio | `components.css` §.tabla + desktop grid; 4 `tipos_reporte` templates (S-14, sidebar 232 + `316px minmax(0,1fr)`); `CACHE`→v4 | ~200 |
| **PR2** móvil: lista + wizard | `components.css` §barra-pantalla/§pasos/§checklist + §6.b hour row and attachment grid; `mis_reportes.html` (S-02); `paso.html` (S-04…S-08); `adjuntos.html`; `CACHE`→v5 | ~330–400 |
| **PR3** validación + estados | `components.css` §hoja + `[data-borrador-banner]`/`[data-borrador-prompt]` + disabled-reason rule; `revision.html` (S-09 sheet, S-10); `participantes.html` (S-10); `CACHE`→v6 | ~250 |

`tokens.css` is a hard dependency of all 11 templates, so it lands first in
PR1a. Each PR adds only the component sections its own screens consume — no
dead CSS ships ahead of its consumer, and each slice reverts cleanly. PR3
follows PR2 because the sync banner is injected next to `paso.html`'s form.

### D6 — Error by border weight, and mono, as pure CSS

Error state resolves to `border-width: var(--borde-error); border-color:
var(--color-tinta)` from three selectors, none of which needs new markup logic:
`[aria-invalid="true"]` (already set by `paso.js:95` for S-06's blocking hour
error), Django's own `ul.errorlist` (login and the two `tipos_reporte` forms),
and `.campo--error` where a template already renders errors. `paso.html` gets
**no** `{{ campo.errors }}` added: its POST never re-renders with field errors
(`test_post_paso_sin_valor_obligatorio_no_bloquea` — validation is deferred to
S-09), so the only live error there is the `aria-invalid` one.

The disabled-primary reason (§4) is markup that is always present and revealed by
`.acciones__primario:disabled ~ .acciones__razon{display:block}` — it follows both
`revision.html`'s server-side `disabled` and `paso.js:65`'s live toggle.

System data uses one utility class, `.mono` (`--fuente-mono`,
`font-variant-numeric: tabular-nums`), applied by hand to the §2 enumeration
(N.º de registro, horas, códigos, tamaños, autoría, fechas), plus blanket rules
for `th` and `.chip`. Rejected: a `{% mono %}` template tag / filter — a new
`templatetags` package to replace one class attribute.

**Two test tripwires constrain the class vocabulary** (see D7): the literal
substrings `disabled` (in `revision.html` + `base.html`) and `generado` (in
`mis_reportes.html` + `base.html`) are asserted absent by existing tests. All
modifiers are therefore Spanish — `--bloqueado`, never `--disabled`, never
`aria-disabled` on those two pages — and chip modifiers encode DESIGN2's three
*weights* (`.chip--solido`, `.chip--borde`, `.chip--borde-gris`, `.chip--ambar`),
not estado slugs. Chip labels keep coming from `get_estado_display`.

### D7 — Zero new JavaScript

The retrofit adds no `.js` file and edits none. Every dynamic state already has
a hook: `button:disabled`, `[aria-disabled]` (`paso.js:70`), `[aria-invalid]`
(`:95`), `[hidden]` on the observation container (`:124`),
`[data-borrador-banner]` / `[data-borrador-prompt]` (`paso-offline.js`),
`:checked`, `ul.errorlist`. Rejected: a small `ui.js` that adds classes — a new
behaviour surface and a new cache entry inside a presentation-only change.
Consequence: DESIGN2's live *chip de conexión* in the screen bar is out (it needs
`navigator.onLine` + listeners); offline state stays visible through the existing
injected banner. See Open Questions.

## Data Flow

    base.html ──{% static %}──▶ /static/css/tokens.css ──@font-face──▶ /static/fonts/*.woff2
        │                              │                                      │
        └──▶ /static/css/components.css│                                      │
                                       ▼                                      ▼
                              sw.js fetch handler: pathname startsWith "/static/"
                                       └──▶ cache-first, CACHE="reportes-offline-vN"

    paso.js  ──sets──▶ [aria-invalid] / button.disabled ──▶ CSS 2px border + mono reason
    paso-offline.js ──injects──▶ [data-borrador-banner] ──▶ CSS .aviso styling (no JS edit)
    Django forms ──render──▶ ul.errorlist ──▶ CSS 2px border + 13/600 message

## File Changes

| File | Action | PR | Description |
|---|---|---|---|
| `config/settings.py` | Modify | 1 | `STATICFILES_DIRS = [BASE_DIR / "static"]` (D2) |
| `static/css/tokens.css` | Create | 1 | `@font-face`, `:root` tokens, element baseline (D1) |
| `static/css/components.css` | Create | 1→3 | 8 blocks, added per consuming PR (D3, D5) |
| `static/fonts/IBMPlexMono-{Regular,Medium}.woff2` | Create | 1 | Binary, provenance in `tokens.css` header (D2) |
| `static/fonts/OFL.txt` | Create | 1 | OFL-1.1 licence text |
| `templates/base.html` | Modify | 1 | `{% load static %}`, viewport meta, 2 `<link>`s, `.pagina` shell, `messages` → `.aviso` |
| `templates/registration/login.html` | Modify | 1 | S-01 |
| `tipos_reporte/templates/tipos_reporte/{lista,detalle,formulario_tipo,formulario_definicion}.html` | Modify | 1 | S-14 desktop |
| `reportes/templates/reportes/mis_reportes.html` | Modify | 2 | S-02 |
| `reportes/templates/reportes/paso.html` | Modify | 2 | S-04…S-08 |
| `reportes/templates/reportes/adjuntos.html` | Modify | 2 | S-08 list |
| `reportes/templates/reportes/revision.html` | Modify | 3 | S-09 sheet / S-10 |
| `reportes/templates/reportes/participantes.html` | Modify | 3 | S-10 |
| `reportes/templates/reportes/sw.js` | Modify | 1,2,3 | `CACHE` bump only (D4) |
| `reportes/tests/test_estatico.py` | Create | 1 | Finder/font/token/base-link tests |
| `reportes/tests/test_views.py` | Modify | 1,2 | Submit-order guard, SW version, per-screen class contract |

## Testing Strategy

`strict_tdd: true` — every row is a failing test before its CSS/markup.

| Layer | What to test | Approach |
|---|---|---|
| Unit | `finders.find()` resolves `css/tokens.css`, `css/components.css`, both `.woff2` | RED until D2's `STATICFILES_DIRS` + files exist |
| Unit | Each `.woff2` starts with the `wOF2` magic bytes and is >10 KB | Catches a committed HTML error page or LFS pointer |
| Unit | `tokens.css` text contains every DESIGN2 §1 hex and no red/danger colour | Only automatable palette check (spec: "no red") |
| Integration | `base.html` response contains both `/static/css/*.css`; contains no `fonts.googleapis`/`gstatic`/CDN stylesheet | Spec scenario "base.html links the new stylesheets" |
| Integration | Rendered `/sw.js` contains the bumped `reportes-offline-v{N}` | Pins D4, one assertion per PR |
| Integration | On a wizard step, the first `form button[type="submit"]` in document order is the step's own submit | `paso.js:63` disables `querySelector('form button[type="submit"]')`; a header/logout form in `base.html` would silently break S-06 blocking |
| Regression | **Whole existing pytest suite green** — the "zero behaviour change" proof | Named tripwires: `test_views.py:504/533` (`"disabled"` present/absent on revisión), `:1248/1263` (`"generado"` absent), `:1497` (no `numero_registro`), `:361-377` (`data-campo`, `data-rango`, `data-requiere-observacion`, `data-siguiente`), `:1074` (`/static/reportes/paso.js`), `:813-815` (form action + csrf), `:988` (usernames), `tipos_reporte/tests/test_vistas.py` |
| Manual QA | Per-PR checklist against DESIGN2 §5's chosen state per screen, at 390×844 and 1120×844; DevTools offline reload of a step (CSS + font from cache); throttled first load to sanity-check the `swap` flash | No visual-regression tooling introduced (proposal, out of scope) |

## Threat Matrix

| Boundary | Applicability | Response |
|---|---|---|
| Third-party binary assets in-repo | **Applicable** — two `.woff2` committed | Fixed upstream (`IBM/plex` release), OFL-1.1 text shipped, release tag + per-file SHA-256 in `tokens.css` header so a reviewer can verify bytes; no installer, no postinstall, no build step |
| Routing | N/A — no new URL, view or route; `STATICFILES_DIRS` only widens the static *search path* to a repo-owned directory |  |
| Executable-file classification | N/A — `.woff2`/`.css` served read-only by WhiteNoise; no upload path touched |  |
| Shell / subprocess / VCS automation / process integration | N/A — none introduced |  |

## Migration / Rollout

No migration; no model or form change. Each PR is independently revertable —
reverting PR1 drops `STATICFILES_DIRS` and both `<link>`s, and every template
falls back to today's unstyled HTML. Stale SW caches from a reverted bump are
deleted by the existing `activate` handler on the next version.

## Open Questions — resolved

- [x] **PR1 budget** — split into PR1a/PR1b per D5. Confirmed with user: not a
      budget-compliance formality, but the right seam — foundation (tokens,
      fonts, base shell, login) and admin desktop (S-14, a fully separate
      desktop-only surface) are different review concerns.
- [x] **Live connection chip** (DESIGN2 §4 screen bar) stays dropped by D7 — it
      needs new JS (`navigator.onLine` + listener), which breaks the "zero
      functional change" guarantee this change relies on for safe, independent
      review/revert. Confirmed out of scope; candidate for a short follow-up
      change if the chip's screen-bar slot needs to be live rather than static.
- [x] **S-02's "cola de subida" banner** — confirmed shipping without it, same
      reasoning as the S-15 exclusion: it isn't markup that exists on
      `mis_reportes.html` today, and adding it there would be new template
      logic, not a visual retrofit.
- [x] **Placeholders** (DESIGN2 §7) — 32px avatar and S-01/S-14 logos ship as
      CSS-drawn boxes/initials, no image assets. Confirmed.

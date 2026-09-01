# Visual Design System Specification

## Purpose

Give the app the concrete visual language DESIGN2.md defines — palette,
typography, spacing/touch-target scale, and 8 reusable component classes —
via a hand-rolled, build-less CSS layer (`static/css/tokens.css`,
`static/css/components.css`) and a self-hosted mono font, applied across the
11 existing templates. Zero behavior change: this capability is presentation
only (backlog #15).

## Requirements

### Requirement: Design Token Stylesheet

`static/css/tokens.css` MUST define CSS custom properties for the complete
DESIGN2 §1 palette (fondo `#f4f3f1`, superficie `#ffffff`, tinta `#14130f`,
tinta secundaria `#4a463f`, tinta mono `#6f6a61`, línea `#d9d5cf`, línea
interna `#eeece8`, deshabilitado fondo/texto, ámbar borde `#b06a00`/`#e0bd7c`,
ámbar fondo `#fdf1dc`, ámbar texto `#7a5a1c`) and the DESIGN2 §2 type scale
(sans sizes 13–26px, mono sizes 10–12px). The palette MUST NOT include any
red/danger color; ámbar is the only warning color.

#### Scenario: Tokens file defines the full palette

- GIVEN `static/css/tokens.css` is loaded
- WHEN any retrofitted template references a token custom property (e.g.
  `var(--color-tinta)`, `var(--color-ambar-borde)`)
- THEN the property resolves to the exact DESIGN2 §1 hex value
- AND no CSS custom property in the file defines a red/danger color

### Requirement: Self-Hosted Mono Font, No CDN Dependency

The system MUST self-host IBM Plex Mono as `.woff2` files under
`static/fonts/`, referenced via `@font-face` in `tokens.css` or
`components.css`. No template or stylesheet SHALL load a font or CSS asset
from a third-party CDN. Prose text MUST use a system sans-serif stack
(Helvetica Neue / Helvetica / Arial fallback) with no self-hosted asset
required.

#### Scenario: Mono font loads without network dependency

- GIVEN the app is served with only `static/` assets available (no external
  network)
- WHEN a page using mono-styled system data (e.g. record numbers, hours,
  timestamps) is rendered
- THEN the mono typeface renders from a self-hosted `static/fonts/*.woff2`
  file, not a CDN URL

### Requirement: Eight DESIGN2 Component Classes

`static/css/components.css` MUST implement CSS classes for all 8 DESIGN2 §4
components: barra de pantalla, indicador de pasos, campo, checklist por rol,
chip de estado, tarjeta de aviso, barra de acciones, hoja modal. Each class's
visible styling (colors, borders, spacing, touch targets) MUST match its
DESIGN2 §4 definition, including the touch-target ranges in DESIGN2 §3
(campos 46–50px, botones 44–52px, casillas Sí/No 48×44, filas ≥48px).

#### Scenario: Component class matches its DESIGN2 spec

- GIVEN a template applies the `campo` component class to a form field
- WHEN the field is rendered
- THEN the field's label, box height, border, and help-text styling match
  the DESIGN2 §4 "Campo" definition (13/600 label, 46px box, 1px border,
  11px mono help text)

#### Scenario: Field error state uses border weight, not color

- GIVEN a field rendered with the `campo` component class has a validation
  error
- WHEN the error state is applied
- THEN the field's border is rendered at 2px in the ink color (`#14130f`)
- AND no red color is introduced to indicate the error

### Requirement: Template Retrofit With No Behavior Change

The 11 in-scope templates (`base.html`, `login.html`, `mis_reportes.html`,
`paso.html`, `participantes.html`, `adjuntos.html`, `revision.html`, and the
4 `tipos_reporte` templates) MUST reference `tokens.css` and `components.css`
and apply the matching DESIGN2 component classes to their existing markup.
These changes MUST NOT alter any view logic, URL, form field name, validation
rule, or server-rendered data; only markup structure/classes and linked
stylesheets MAY change.

#### Scenario: Retrofitted template preserves existing behavior

- GIVEN a retrofitted template (e.g. `paso.html`) had a passing scenario in
  its owning capability's spec before this change
- WHEN the same scenario is exercised after the retrofit
- THEN the scenario still passes with identical server-side behavior
- AND only the rendered markup's classes/structure and linked stylesheets
  differ

#### Scenario: base.html links the new stylesheets and font

- GIVEN `base.html` is rendered
- WHEN the response HTML is inspected
- THEN it includes `<link>` tags for `static/css/tokens.css` and
  `static/css/components.css`
- AND no `<link>`/`<script>` tag references a third-party CDN font or
  stylesheet

### Requirement: No Framework or Build Step

The system MUST NOT introduce a CSS framework (e.g. Tailwind) or a build/
bundling step. All CSS and font assets MUST be servable as-is via WhiteNoise/
Django static files, consistent with the project's existing build-less
convention.

#### Scenario: Static assets are servable without a build step

- GIVEN a fresh checkout with no `npm install`/build command run
- WHEN `static/css/tokens.css`, `static/css/components.css`, and
  `static/fonts/*.woff2` are requested
- THEN they are served directly as committed files with no compilation step

# Exploration: retrofit-visual-design2 (backlog #15)

## Current State

Django server-rendered project. There is **zero CSS** anywhere in the repo (only
Django/GIS vendor CSS inside `.venv`, not project-owned). `templates/base.html` has
no stylesheet link, no `<style>` block, no framework (no Tailwind, no Bootstrap), and
templates use bare semantic HTML with no styling classes. No design tokens exist. No
`static/**/*.css` exists at all — only JS (`paso.js`, `offline-db.js`,
`paso-offline.js`, `adjuntos.js`).

`DESIGN.md` at the repo root **is confirmed to be** the source DESIGN2.md references
as `uploads/DESIGN.md` — matching title convention and identical screen inventory
(S-01…S-15). No separate `uploads/` folder exists.

## Affected Areas (11 project templates)

- `templates/base.html` — global layout, no styling hook currently
- `templates/registration/login.html` — S-01
- `reportes/templates/reportes/mis_reportes.html` — S-02 (+ likely hosts S-15 banner)
- `reportes/templates/reportes/paso.html` — generic S-04→S-08 wizard step
- `reportes/templates/reportes/participantes.html` — likely S-05 (unconfirmed, not read)
- `reportes/templates/reportes/adjuntos.html` — S-08
- `reportes/templates/reportes/revision.html` — S-09/S-10
- `tipos_reporte/templates/tipos_reporte/lista.html`, `detalle.html`,
  `formulario_tipo.html`, `formulario_definicion.html` — S-14 admin (desktop)

Standalone S-15 (sync queue) view not confirmed as separate from the S-02 banner —
needs one more read pass before design.

## Approaches

1. **Hand-rolled CSS design tokens + component classes** (no framework) —
   `static/css/tokens.css` + `components.css`, wired into `base.html`, retrofit 11
   templates incrementally.
   - Pros: matches project's build-less convention, safe for offline-first use,
     DESIGN2's 8 components are small enough not to need a framework.
   - Cons: all from scratch; font-loading strategy for Helvetica Neue/IBM Plex Mono
     must be decided explicitly (offline reliability).
   - Effort: High overall (tokens+base = Medium, 11 template retrofits = Medium-High).

2. **Tailwind (or similar utility framework)** — adds a Node/build step or CDN mode.
   - Pros: faster iteration once configured.
   - Cons: introduces a build step to a currently build-less Django project; CDN mode
     is unreliable for the app's offline-first requirement; disproportionate for a
     small, well-specified component set.
   - Effort: Medium setup + Medium retrofit, with added infra risk.

## Recommendation

Approach 1. Given the scope (global tokens + 11 templates), this should not be one
PR — recommend slicing into ~3 chained PRs: (a) tokens + base layout + login + admin
desktop (S-01, S-14), (b) mobile list + wizard (S-02, S-04–S-08), (c) validation
sheet + sync/offline states (S-09, S-10, S-15).

## Risks

- No visual-regression test coverage; QA against DESIGN2 §5 states will be manual.
- Font-loading strategy unresolved (Helvetica Neue is not universally web-safe; IBM
  Plex Mono is a Google Font) — must decide self-hosted woff2 vs system fallback,
  given offline-first use in the field.
- Standalone S-15 location unconfirmed.
- `participantes.html` content unread — must confirm S-05 mapping before task
  breakdown.
- DESIGN2 explicitly notes S-03, S-07, S-13 are undrawn/derived by analogy — adds
  design-phase ambiguity.
- Scope is broad; must respect the 400-line PR review budget guard via chained
  slices.

## Ready for Proposal

Yes. Recommend `sdd-propose` next, flagging two open questions before design:
(1) font self-hosting vs CDN under offline-first constraints, (2) whether S-02's
banner fully covers S-15 or a dedicated sync-queue view is needed.

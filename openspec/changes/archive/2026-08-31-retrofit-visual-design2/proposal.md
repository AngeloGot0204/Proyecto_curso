# Proposal: Visual Retrofit to DESIGN2.md (backlog #15)

## Intent

The app is fully functional (11 templates, offline-first, sync queue) but has
**zero CSS** — bare unstyled HTML. DESIGN2.md defines a concrete visual
language (palette, typography, 8 reusable components, per-screen states) that
was never applied. This leaves the field-usage product inconsistent with its
own design spec and harder to use/trust in real conditions (bright outdoor
light, quick glance at status/errors, mobile-first wizard). This change
closes that gap with zero behavior change.

## Scope

### In Scope
- `static/css/tokens.css`: CSS custom properties for DESIGN2 palette + type scale.
- `static/css/components.css`: the 8 DESIGN2 components (barra de pantalla,
  indicador de pasos, campo, checklist, chip, tarjeta de aviso, barra de
  acciones, hoja modal).
- Self-hosted IBM Plex Mono `.woff2` in `static/fonts/` (service-worker
  cacheable, no CDN dependency). Helvetica Neue via system-font fallback stack.
- Retrofit of all 11 existing templates to the new tokens/components:
  `base.html`, `login.html`, `mis_reportes.html`, `paso.html`
  (covers S-04 through S-08, wizard steps, including S-05 and S-07),
  `participantes.html` (S-10), `adjuntos.html`, `revision.html`
  (S-09/S-10), and the 4 `tipos_reporte` admin templates (S-14).
- Reasonable visual extrapolation for S-07 (a `paso.html` instance, drawn by
  analogy to S-06's hour-row pattern per DESIGN2 §6.b) by analogy to the
  closest drawn state within the same template.
- Delivered as ~3 chained PRs (tokens+layout+login+admin desktop; mobile
  list+wizard; validation sheet+sync/offline states) per the 400-line review
  budget guard.

### Out of Scope
- Any functional/behavioral change: no new routes, no form-validation logic
  changes, no data-model changes.
- S-03 (nuevo reporte · selección de tipo) and S-13 (admin de usuarios): no
  dedicated template exists for either today (S-03's flow is presumably
  embedded in `mis_reportes.html`'s "nuevo reporte" action; S-13's user
  management runs through Django admin, not a custom screen). Retrofitting
  them would mean building a new screen — that is functional scope, not
  visual retrofit, so both stay out of this change.
- S-15 (dedicated sync-queue screen with retry/last-sync per DESIGN2): no
  standalone template exists either — the offline/sync state today lives as
  a banner/embedded list inside `mis_reportes.html` (S-02). This change
  restyles that embedded banner in place; it does NOT add the dedicated S-15
  screen DESIGN2 describes, since that would be new functionality.
- Pixel-perfect fidelity for S-07 (drawn only by analogy in DESIGN2 §6.b) —
  flagged for later refinement if DESIGN2 is extended with a real S-07 mock.
- Real iconography/logo assets — placeholders only where DESIGN2 references
  icons/branding without shipping final assets.
- Automated visual-regression testing (none exists; QA stays manual against
  DESIGN2 §5).
- Any CSS framework or build step (no Tailwind, no bundler) — stays build-less.

## Capabilities

### New Capabilities
- `visual-design-system`: CSS design tokens + the 8 DESIGN2 component classes,
  applied across all existing templates; self-hosted font strategy.

### Modified Capabilities
- `capa-offline`: extend the service worker's cached static-asset set to
  include the new CSS files and self-hosted `.woff2` fonts, so the retrofitted
  UI renders correctly offline (no behavior change to draft/sync logic).

## Approach

Hand-rolled CSS tokens + component classes (no framework), incrementally
wired into `base.html` and consumed by each template. Matches the project's
existing build-less Django convention and avoids CDN reliance under
offline-first use. See exploration for the rejected Tailwind alternative.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `static/css/tokens.css`, `static/css/components.css` | New | Design tokens + components |
| `static/fonts/*.woff2` | New | Self-hosted IBM Plex Mono |
| `templates/base.html` | Modified | Stylesheet/font links, layout shell |
| 10 other templates (see Scope) | Modified | Apply component classes, no logic change |
| Service worker cache list | Modified | Cache new CSS/font assets |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| No visual-regression tests — manual QA only | Med | Checklist per screen against DESIGN2 §5 states before each PR merge |
| S-07 analogy misreads intent | Low | Flag explicitly in PR description as extrapolated, revisit if DESIGN2 updated |
| S-03/S-13/S-15 have no template today — restyling embedded banner only, not the dedicated screens DESIGN2 describes | Low | Documented as out-of-scope; explicit follow-up candidate if those screens get built |
| Scope creep across 11 templates in one PR | Med | Enforced 3-PR chain per exploration slicing |

## Rollback Plan

Each of the 3 PRs is independently revertable (pure CSS/markup class
additions, no data migration). Reverting a PR removes its `<link>`/class
usage; templates fall back to unstyled HTML (current behavior), no
functional regression.

## Dependencies

- DESIGN2.md and DESIGN.md (already present, no change).
- Requires a resolved `chain_strategy` (stacked-to-main vs
  feature-branch-chain) before `sdd-tasks`, since delivery is confirmed as
  ~3 chained PRs.

## Success Criteria

- [ ] All 11 templates visually match their DESIGN2 screen/state definitions.
- [ ] Zero functional/behavioral regressions (existing specs' scenarios still pass).
- [ ] App renders fully styled with fonts working when offline (SW cache verified).
- [ ] No CDN dependency introduced; no build step introduced.

## Proposal question round — resolved

All three exploration-flagged ambiguities were resolved by reading
`DESIGN.md`'s screen inventory (§5) against the actual template files in
`reportes/templates/reportes/` and `tipos_reporte/templates/`:

1. **S-05 mapping**: `DESIGN.md` describes S-05 as "Paso 2 · Parámetros
   preliminares (7 ítems, Sí/No por rol)" — a wizard step. It is an instance
   of `paso.html` (the generic S-04→S-08 step template), NOT
   `participantes.html`.
2. **`participantes.html` mapping**: it is S-10 ("Estado del reporte ·
   participantes y visto bueno" — invite list, "Compartir con...",
   "Marcar como terminado"), confirmed by matching its described content.
3. **S-15 location**: `DESIGN.md` describes S-15 as a dedicated screen
   ("Lista de reportes pendientes con estado, reintento manual, última
   sincronización"), reached from a banner on S-02 per the flow diagram
   (§5). No such dedicated template exists in the repo today — only a
   banner/embedded list inside `mis_reportes.html` plus client-side JS
   (`paso-offline.js`, `offline-db.js`). Building the dedicated S-15 screen
   is new functionality, out of scope for a visual-only retrofit; this
   change restyles the existing embedded banner in place.
4. **S-03/S-13**: neither has a dedicated template either (S-03's "nuevo
   reporte" flow is presumably an action within `mis_reportes.html`; S-13's
   user admin runs through Django admin). Same reasoning as S-15 — out of
   scope.

Net effect: 8 real templates get full retrofit (`base.html`, `login.html`,
`mis_reportes.html`, `paso.html` for S-04/05/06/07/08, `participantes.html`,
`adjuntos.html`, `revision.html`, and the 4 `tipos_reporte` templates for
S-14 — 11 files total), and S-03/S-13/S-15 are explicitly out of scope as
dedicated screens.

`chain_strategy`: **stacked-to-main** — confirmed with the user. Consistent
with prior backlog items (mis-reportes, adjuntos, admin-tipos-reporte), each
PR merges directly to main in sequence, independently reviewable/mergeable.

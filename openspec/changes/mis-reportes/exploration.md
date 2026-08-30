# Exploration: "Mis reportes" (S-02, backlog #12)

## Current State

**Key finding**: TECH-DESIGN.md explicitly ties S-02's status chip and register-number column to `Reporte.id_local`/`numero_registro` (backlog #10 fields). The intended lifecycle diagram has 5 states (`borrador local → en progreso → completo → terminado → generado`), but only `EN_PROGRESO`/`TERMINADO` exist in code (docstring confirms "#9 offline, #10 sync" states are future work). `Generacion` is an audit table, not a `Reporte.estado` value — "generado" is not tracked as a state anywhere.

No list/index view exists in `reportes/views.py` (confirmed, full file: only `service_worker`, `iniciar_reporte`, `paso`, `revision`, `cerrar_reporte`, `generar`, `invitar`, `participantes`). No pagination precedent, no list templates, no list-view tests anywhere in the app.

**Access model confirmed**: the natural query is `Reporte.objects.filter(Q(creador=usuario) | Q(participaciones__usuario=usuario)).distinct()`, matching the exact pattern already used by `_reporte_accesible`/`tiene_acceso` for `paso`/`revision`/`generar`/`participantes` (backlog #8, merged). `TipoDeReporte.nombre`/`.codigo` are natural search/filter fields.

`usuarios/views.py::inicio` explicitly names #12 as its replacement ("Scope guard: this view must accumulate no report-domain logic. Backlog item #12 replaces it with the real dashboard") — independent of the #10 question.

## Affected Areas
- `reportes/views.py` — new list view needed.
- `reportes/templates/reportes/` — new template, no precedent.
- `usuarios/views.py` — `inicio` is the explicit replacement target.
- `reportes/tests/test_views.py` — extend existing access-control test pattern.

## Approaches

1. **Build a scoped-down "Mis reportes" today** — grouping by the 2 real states, search/filter on `tipo.nombre`/`tipo.codigo`/`creador`/`fecha_creacion`, deferring `numero_registro` and the full 5-state chip.
   - Pros: unblocks #12 without waiting on #9/#10; reuses proven access pattern; no migration.
   - Cons: diverges from the literal wireframe; needs a follow-up once #10 lands.
   - Effort: Low–Medium.

2. **Wait for #10, build exactly as designed.**
   - Cons: blocks a simple listing screen on the highest-risk backlog items; leaves `inicio`'s TODO stuck.
   - Effort: High (externally blocked).

3. **Split into two explicit slices**: ship #1 now, track the deferred `numero_registro`/sync-chip work as a named follow-up once #10 ships.
   - Pros: same benefit as #1, but makes the scope cut explicit/trackable rather than silent.
   - Effort: Low–Medium.

## Recommendation
Approach 3. The `#10` dependency is genuinely load-bearing only for `numero_registro` and the sync-related chip/state — not for the core grouped-list/search/filter mechanism, which is fully buildable on #7/#8. Narrow scope to: list grouped by the 2 existing `EstadoDeReporte` values, search on `tipo__nombre`/`tipo__codigo`/`creador__username`, `?estado=` filter, Django `Paginator`, replacing `usuarios/views.py::inicio`.

## Open Decision (must be settled in proposal)
Proceed with narrowed scope now (defer `numero_registro`/full chip to a follow-up once #10 ships), or keep #12 literally blocked on #10?

## Risks
- Narrowing scope deviates from the written backlog/TECH-DESIGN dependency — must be surfaced explicitly.
- With only 2 states, "agrupado por estado" is thinner than the 5-state design implies — a product call.
- No existing list-view/pagination convention in the codebase — whatever's built here will likely be copied by future list views (#13).
- Exposing "generado" as a derived flag (`Generacion.objects.filter(...).exists()`) rather than a real state is a judgment call needing confirmation.

## Key Learnings
1. TECH-DESIGN.md ties S-02's status chip and register-number column specifically to `Reporte.id_local`/`numero_registro`, both backlog #10 fields not yet in the schema.
2. `Generacion` is an audit-row-per-generation table decoupled from `Reporte.estado` — generating a document never transitions the report's stored state.
3. The creator-or-invited-participant access query is already established across `paso`/`revision`/`generar`/`participantes`.
4. `usuarios/views.py::inicio` carries an explicit scope-guard docstring naming backlog #12 as its intended replacement, independent of the #10 dependency question.
5. No list view, list template, pagination usage, or list-view test exists anywhere in the `reportes` app yet — #12 would be the first.

**Next**: sdd-propose (pending the open decision above)

# Exploration: Cierre manual (visto bueno) y generación del documento (Backlog #7)

## Current State

**Lifecycle today.** `reportes/models.py::EstadoDeReporte` declares only `EN_PROGRESO`. Its docstring explicitly defers every later state ("#7 visto bueno, #9 offline, #10 sync") and notes `TextChoices` + `CharField` makes adding members purely additive. TECH-DESIGN.md's lifecycle: `borrador local → en progreso (sincronizado) → completo → terminado (visto bueno) → generado`. "Completo" is **not** a stored state — it's computed by `reportes.validacion.validar_reporte(reporte).puede_generar`.

**S-09 review screen exists.** `reportes/views.py::revision` + `reportes/templates/reportes/revision.html` render `resultado.puede_generar`. The "Generar" button is a bare `<button type="button" {% if not resultado.puede_generar %}disabled{% endif %}>Generar</button>` — no `action`, no wired URL, gated only on `puede_generar`, not on visto bueno (which doesn't exist yet). This is exactly the gap #7 closes.

**`ParticipacionEnReporte` is not built yet** — only `Reporte`/`ValorDeReporte` exist. ADR-0006's closing rule doesn't need it anyway: closing checks `reporte.creado_por == usuario_actual` directly.

**`tipos_reporte/generador.py::generar_reporte(definicion, valores) -> BytesIO`** (backlog #4, done) is stable:
- Exceptions: `ProblemaDeGeneracion` (base), `PlantillaIlegible` (unreadable/corrupt file, parser failure, or missing declared sheet), `ValoresIncompletos` (accumulated missing obligatorio ids, `.faltantes` tuple).
- `valores` shape: `{"{id}": v}` for scalar `celda` nodes, `{"{id}_inicio": v, "{id}_fin": v}` for ranges — confirmed identical to `reportes/valores.py`'s persistence keys.
- Writes `valores[clave]` **directly** into the cell, no type coercion. `tipos_reporte/tests/conftest.py::valores_completos` confirms expected values are **raw persisted strings** (e.g. `"turno": "Día"`, `"p-01_inicio": "08:00"`) — not `desde_texto`-rehydrated Python objects.
- Does not check `Reporte.estado` or visto bueno — entirely the caller's responsibility.

**No new adapter needed to build `valores`.** The exact one-liner already exists twice: `reportes/validacion.py::validar_reporte` and `reportes/views.py::paso` both do `{v.identificador_de_campo: v.valor for v in reporte.valores.all()}`. The generation endpoint should reuse this — `reportes/valores.py::desde_texto` is unrelated (only for form redisplay).

**No file-download response pattern exists anywhere in the repo** — a repo-wide search for `FileResponse`/`Content-Disposition`/`HttpResponse(content_type=...)` found zero production usages. Plain Django `HttpResponse` with the xlsx MIME type + `Content-Disposition: attachment` header is the standard idiom; no new dependency needed.

## Affected Areas
- `reportes/models.py` — add `VistoBueno` (usuario, fecha; creator-only per ADR-0006); extend `EstadoDeReporte` (at least `TERMINADO`); decide `Generacion` now vs. later.
- `reportes/views.py` — new `cerrar_reporte` (POST, creator-only) and generation view (catches `ProblemaDeGeneracion`, streams file or clean error).
- `reportes/urls.py` — two new routes.
- `reportes/templates/reportes/revision.html` — wire "Generar" to a real endpoint; gate on creator + visto bueno + `puede_generar`.
- `reportes/validacion.py` — no functional change; `puede_generar` stays orthogonal to visto-bueno gating (ADR-0006: both conditions required).
- `tipos_reporte/generador.py` — no change needed, already tested.
- `config/settings.py` — verify Sentry (ADR-0008) is wired before assuming failures reach it.
- `reportes/migrations/` — new migration(s) for `VistoBueno` (+`Generacion`) and `EstadoDeReporte` choices.

## Approaches

1. **`VistoBueno` + `Generacion` audit row per download, no new `GENERADO` estado** — matches TECH-DESIGN's documented two-entity split exactly.
   - Pros: no deviation from TECH-DESIGN; free audit trail (who/when/which template version) without a state machine; small additive migration.
   - Cons: slightly ahead of literal AC text; repeated clicks accumulate rows (acceptable for an audit log).
   - Effort: Low.

2. **`VistoBueno` only, stateless generate-and-serve, no `Generacion`** — smallest slice satisfying every literal AC.
   - Pros: smallest surface, fewer migrations.
   - Cons: contradicts TECH-DESIGN's Modelo de datos table, which lists `Generacion` as a first-class entity; harder to backfill audit history later.
   - Effort: Low (slightly lower than #1).

3. **`Generacion` + explicit terminal `GENERADO` `EstadoDeReporte` member, updated per successful generation** — closest literal match to the documented lifecycle diagram.
   - Pros: `Reporte.estado` becomes queryable for "still needs generation" without joining `Generacion`.
   - Cons: forces resolving an undecided question now — can a report generate more than once, and does `estado` regress if edited post-closure?
   - Effort: Medium.

## Recommendation

**Approach 1.** Follows TECH-DESIGN's data model literally (both `VistoBueno` and `Generacion` are documented entities), avoids forcing the "generated exactly once" question approach 3 raises — no ADR or AC requires `Reporte.estado` to reach a terminal `generado` value; they only require visto-bueno gating and clean generation failure. Add `EstadoDeReporte.TERMINADO` (set when `VistoBueno` is created), load-bearing for the UI distinction ADR-0006 calls out ("la interfaz debe hacer visible ese estado").

Endpoint sketch:
- **Generation** (`POST`): re-check `reporte.visto_bueno` exists and `validar_reporte(reporte).puede_generar` (defense in depth), build `valores` via a shared helper (extract the repeated one-liner into `reportes/valores.py::valores_de_reporte(reporte)` so `paso`, `validar_reporte`, and this view share one source), call `generar_reporte`, catch `ProblemaDeGeneracion` → render a clean error page + forward to Sentry (never a raw 500), on success create one `Generacion` row and stream the `.xlsx` with a `Content-Disposition` header.
- **Visto bueno** (`POST`, creator-only via `get_object_or_404(Reporte, pk=..., creador=request.user)` mirroring `paso`'s pattern): re-check `puede_generar` server-side, create `VistoBueno`, set `estado = TERMINADO`, redirect to `revision`.

## Open Decisions (must be settled in proposal)
1. Who besides the creator may trigger/download generation? (No participation model exists yet — ADR-0006 leans open-collaboration, but nothing built restricts beyond creator for capture. Recommend: any authenticated user, deferred fine-grained access to #8.)
2. Is visto bueno/generation repeatable? Can "Generar" be clicked more than once (re-download)? Does editing a captured value after closure regress `estado`? (Nothing currently locks post-closure edits — is that in scope for #7 or deferred?)

## Risks
- Who besides the creator may download/trigger generation is unstated anywhere — needs explicit decision.
- Sentry integration status (ADR-0008) in `config/settings.py` is unverified.
- Repeatability/revocability of visto bueno and generation is undecided by ADR-0006.
- `EstadoDeReporte` choices addition needs a migration even though schema-additive.
- No existing test pattern for file-download responses — apply phase must establish `Content-Disposition`/`Content-Type`/`load_workbook(BytesIO(response.content))` round-trip assertions from scratch.

## Key Learnings
1. `tipos_reporte.generador.generar_reporte` expects raw persisted strings in `valores`, not typed Python objects rehydrated via `desde_texto`.
2. The `valores` dict `generar_reporte` needs is already built identically in two places, so backlog #7 needs no new adapter, just a shared helper extraction.
3. `EstadoDeReporte` currently declares only `EN_PROGRESO` by design, deferring later states explicitly to backlog #7/#9/#10 in its own docstring.
4. The S-09 "Generar" button already exists but is fully unwired, gated only on `puede_generar`, not on any visto-bueno state.
5. No file-download HTTP response pattern exists anywhere in this codebase yet — backlog #7 establishes it for the first time.

**Next**: sdd-propose (pending resolution of the 2 open decisions above)

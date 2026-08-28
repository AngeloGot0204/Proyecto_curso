# Exploration: Generador de Excel desde plantilla (backlog #4)

## Current State

**`tipos_reporte` app (backlog #3, merged)**:
- `TipoDeReporte` — `plantilla` is a `FileField(upload_to="tipos_reporte/plantillas/")` (original `.xlsx`), plus `logo` (`ImageField`, nullable) and `definicion_activa` (FK to the active `DefinicionDeTipo`).
- `DefinicionDeTipo` — one immutable-once-activated version per `TipoDeReporte`. Key field: `estructura` (`JSONField`), the normalized tree #4/#5 read. Shape (from `tipos_reporte/tests/conftest.py::definicion_valida`, `tipos_reporte/validacion.py`):
  ```json
  {
    "tipo": "instalacion-resinas",
    "plantilla": "JME.PC-0001.F1.xlsx",
    "hoja": "REPORTE",
    "secciones": [
      {
        "id": "datos-generales",
        "titulo": "Datos generales",
        "campos": [
          {"id": "turno", "etiqueta": "Turno", "tipo": "seleccion",
           "opciones": ["Día", "Noche"], "obligatorio": true, "celda": "M12"}
        ]
      },
      {
        "id": "proceso-instalacion",
        "titulo": "...", "roles": [],
        "items": [
          {"id": "p-01", "texto": "...", "tipo": "rango-hora-inicio-fin",
           "celda_inicio": "M25", "celda_fin": "P25"}
        ]
      }
    ]
  }
  ```
  - `campos` nodes use a single `celda`; `items` nodes with `tipo == "rango-hora-inicio-fin"` use `celda_inicio`/`celda_fin` (`tipos_reporte/validacion.py:30-32`). All other closed data types (`texto`, `numero`, `fecha`, `hora`, `seleccion`, `booleano`) use `celda`.
  - `estructura["hoja"]` names the target worksheet; validated to exist at activation time (R5).
  - Every declared destination cell is already validated (R6, `celda-no-es-ancla`) to be the anchor (top-left) cell of its merged range — the write-safety precondition ADR-0002 requires. A generator built on an activated `DefinicionDeTipo` can trust this invariant.

**Template storage**: `TipoDeReporte.plantilla` is a Django `FileField` under `MEDIA_ROOT/tipos_reporte/plantillas/`. Existing code (`tipos_reporte/servicios.py::activar_definicion`) opens it with `plantilla.open("rb")` / `.close()` in `try/finally`, treats `OSError`/`FileNotFoundError` as a domain problem (`plantilla-ilegible`). `tipos_reporte/validacion.py::validar_contra_plantilla` documents it takes an open binary file object, never a `FieldFile` — generator should follow the same convention for testability.

**`ValorDeReporte` — does NOT exist yet.** No such model in the repo. `TECH-DESIGN.md` (line 121) describes it as generic value storage ("una fila por valor capturado") but it belongs to backlog #5 (wizard de captura) or later, not #3. Backlog #4's own dependency edge is only `#3`. Backlog #7 ("Cierre manual...") depends on `#4, #6` and owns "endpoint que dispara el generador (#4)" — #7 is the integration point that reads persisted `ValorDeReporte` rows and calls the #4 service.

**ADR-0002** settles the architecture:
- Load original `.xlsx` with `openpyxl.load_workbook`, write only cell values (never rebuild workbook), export only the target sheet (`estructura["hoja"]`).
- Empirically validated: writing to a merged-range anchor cell works; non-anchor cell raises `AttributeError: 'MergedCell' object attribute 'value' is read-only` (guarded by R6).
- No formulas in reference sheet, so formula-loss-on-write is not a concern.
- Logo is dynamic: generator must replace image by manipulating `ws._images` — remove original, insert tipo's logo at same position/anchor — before writing values.
- Cell-mapping fragile to template revisions; golden-file regression test recommended (ties to ADR-0007).

**Existing openpyxl usage** confined to `tipos_reporte/validacion.py` and `tipos_reporte/tests/conftest.py`. No writer/generator code exists yet. `requirements.txt` pins `openpyxl>=3.1,<4`.

**Test conventions** (pytest-django, `--reuse-db`): `conftest.py` provides `definicion_valida`, `plantilla_xlsx` (builds real on-disk `.xlsx`, configurable sheet/merged ranges), `usuario_factory`, `tipo_de_reporte_factory`. Existing tests are pure-function style asserting on `ProblemaDeDefinicion.regla`. Strict TDD enabled project-wide.

## Affected Areas
- `tipos_reporte/models.py` — read-only for this feature.
- `tipos_reporte/validacion.py` — reuse `_mapa_de_celdas_no_ancla`, `_iterar_nodos`, `_claves_de_celda_requeridas`, `_TIPOS_CON_RANGO` rather than duplicate.
- New module: likely `tipos_reporte/generador.py`.
- `tipos_reporte/tests/conftest.py` — likely needs a new fixture layer for values dicts.
- `adrs/0002-motor-de-generacion-de-excel.md` — authoritative design constraints.

## Recommended Approach
Standalone `generar_reporte` service in `tipos_reporte/generador.py` that accepts an already-**activated** `DefinicionDeTipo` plus a plain values mapping (`dict`, not a `ValorDeReporte` queryset/model) — decoupled from persistence models that don't exist yet. Matches the actual `#4 → #3` dependency edge, buildable/testable today, follows ADR-0002 exactly (open real template, write only anchor cells, swap `ws._images` for logo, export only declared sheet), reuses `validacion.py` helpers.

Open sub-decision: how a `rango-hora-inicio-fin` item's value arrives in the dict — one composite value/tuple per item id, vs. two independently-addressable keys. Needs explicit decision since it shapes the future `ValorDeReporte`→dict adapter (#7).

## Risks
- **Naming mismatch with backlog text**: BACKLOG.md says "escribe `ValorDeReporte`," but that model doesn't exist yet (dependency graph: #4 depends only on #3). Must document explicitly: generator takes a plain values mapping now; `ValorDeReporte` persistence/read-adapter is #7's job.
- **Untested against real reference template**: ADR-0002's validation ran against a manual file not committed to repo. Golden-file regression test needs explicit scoping.
- **Logo-swap via `ws._images`** only described narratively, never implemented/tested — highest-uncertainty piece, needs focused coverage.
- **Range-type value contract undecided** — needs explicit decision before implementation.

## Key Learnings
1. `ValorDeReporte`/`Reporte` models referenced in backlog #4's description don't exist yet; they belong to backlog #5+, and #4's actual dependency edge is only #3.
2. `DefinicionDeTipo.estructura` already guarantees (via R6) every destination cell is a merged-range anchor, satisfying ADR-0002's write-safety precondition.
3. `tipos_reporte/validacion.py` exposes reusable node-iteration/anchor-mapping helpers the new generator should reuse, not duplicate.
4. ADR-0002 requires swapping the logo via `ws._images` manipulation before writing values; undocumented in code and untested anywhere in the repo.
5. `activar_definicion` establishes the convention of `FieldFile.open("rb")`/`.close()` in try/finally, converting template-read failures into domain problems.

**Next**: sdd-propose

# Design: Generador de Excel desde plantilla (backlog #4)

## Technical Approach

New module `tipos_reporte/generador.py` exposing one plain function
`generar_reporte(definicion: DefinicionDeTipo, valores: dict) -> BytesIO`. It mutates a
*loaded copy* of the original template (never the stored file, never a rebuilt workbook) and
reuses `tipos_reporte/validacion.py` helpers (`_iterar_nodos`, `_claves_de_celda_requeridas`,
`_TIPOS_CON_RANGO`) so anchor logic exists in exactly one place.

**Correction to proposal/spec wording**: the FK on `DefinicionDeTipo` is `tipo`, not
`tipo_de_reporte` (`tipos_reporte/models.py:146`). Implementation reads `definicion.tipo.plantilla`
and `definicion.tipo.logo`.

## Sequence

```
caller ─► generar_reporte(definicion, valores)
          │ 1. plantilla.open("rb")            ── OSError/FileNotFoundError ─► PlantillaIlegible
          │ 2. try: load_workbook(fh)          ── any Exception ────────────► PlantillaIlegible
          │    finally: plantilla.close()
          │ 3. hoja = libro[estructura["hoja"]] ── KeyError ────────────────► PlantillaIlegible
          │ 4. VALIDATE valores completeness   ── missing ────────────────► ValoresIncompletos
          │ 5. logo swap on hoja._images (only if definicion.tipo.logo)
          │ 6. write scalar/range values into anchor cells
          │ 7. delete every sheet != hoja; libro.active = 0
          │ 8. libro.save(BytesIO()); seek(0)
          ▼ BytesIO
```

Steps 4–8 run **after** the file handle is closed (openpyxl fully materializes the workbook in
memory), so `try/finally` wraps only open→load, exactly like `activar_definicion`
(`tipos_reporte/servicios.py:44-64`). Validation precedes every mutation: no partial write is
observable even in-memory.

## Architecture Decisions

### D1: Single derivation of (value key → target cell)

**Choice**: one private helper drives both the completeness pass and the write pass:

```python
_SUFIJO_POR_CLAVE = {"celda": "", "celda_inicio": "_inicio", "celda_fin": "_fin"}

def _destinos(nodo):
    """(clave_en_valores, coordenada) pairs for one campo/item."""
    return [
        (f"{nodo['id']}{_SUFIJO_POR_CLAVE[clave]}", nodo[clave])
        for clave in _claves_de_celda_requeridas(nodo.get("tipo"))
    ]
```

**Alternatives**: separate `if tipo in _TIPOS_CON_RANGO` branches in each pass.
**Rationale**: `_claves_de_celda_requeridas` already encodes range-vs-scalar; two branches could
drift and let a validated-as-present key be written to the wrong cell.

### D2: Presence test is key membership, not truthiness

**Choice**: `clave in valores`. **Alternative**: `valores.get(clave)` truthiness.
**Rationale**: `False`, `0` and `""` are legitimate `booleano`/`numero`/`texto` values;
`validacion._requerir` uses truthiness for *schema* keys, which is a different question.

### D3: Requiredness comes from `obligatorio`

**Choice**: a node is required when `nodo.get("obligatorio")` is truthy; non-required nodes whose
keys are absent leave their anchor cell untouched (ADR-0002: "lo que no se escribe, no se altera").
Keys present in `valores` but not declared in `estructura` are ignored — `estructura` is the sole
authority on what gets written.
**Rationale**: `obligatorio` is the only requiredness signal in the validated tree.

### D4: Logo swap by reusing the original anchor object

**Choice** (highest-uncertainty piece — concrete API):

```python
from openpyxl.drawing.image import Image as ImagenOpenpyxl

originales = hoja._images                      # plain list of Image objects
if definicion.tipo.logo and originales:
    original = originales[0]
    nueva = ImagenOpenpyxl(BytesIO(definicion.tipo.logo.read()))
    nueva.anchor = original.anchor             # OneCellAnchor/TwoCellAnchor object, reused as-is
    hoja._images.remove(original)
    hoja.add_image(nueva)                      # add_image(img, anchor=None) keeps nueva.anchor
```

- Reusing the loaded `anchor` **object** preserves both position and extent: for
  `OneCellAnchor`/`TwoCellAnchor`, `SpreadsheetDrawing` serializes the anchor's `_from`/`ext`
  and ignores `Image.width/height`. Copying pixel dimensions instead would resize the box.
- `hoja._images.remove(original)` (not `.clear()`) replaces only the first image and leaves any
  additional template drawings untouched. The reference sheet has exactly one image (ADR-0002).
- **Template has no image + logo set** → no anchor exists to honor, so no image is inserted.
  Rejected alternative: insert at `"A1"`, which would drop the logo over report data.
- Pillow is already pinned (`requirements.txt:8`); without it openpyxl silently drops images on
  load, so the fixture must assert the image survives the round trip.

**Alternatives**: rebuild the drawing XML, or `ws.add_image(img, "B2")` with a hardcoded cell.
**Rationale**: both re-author layout, violating ADR-0002's "el formato nunca se construye".

### D5: Sheet-only export by deleting the other sheets in place

**Choice**: `for nombre in [n for n in libro.sheetnames if n != hoja_objetivo]: del libro[nombre]`,
then `libro.active = 0`, then `libro.save(buffer)`.
**Alternatives**: (a) `Workbook()` + `copy_worksheet` — rejected: `copy_worksheet` does not carry
images/charts and is a rebuild; (b) ZIP/XML surgery — rejected by ADR-0002 as unjustified
complexity; (c) return every sheet — violates the spec.
**Rationale**: styles, number formats and fonts live in workbook-level shared tables, so deleting
sheet objects never touches the target sheet's merges, print area, scaling or drawings. ADR-0002
empirically validated "exportar sólo la hoja del reporte + guardar". `libro.active = 0` avoids an
out-of-range active index after deletion.

## Interfaces / Contracts

```python
class ProblemaDeGeneracion(Exception):
    """Base for every foreseeable generation failure, so backlog #7's endpoint
    catches one type and never surfaces a 500."""
    regla = "problema-de-generacion"

class PlantillaIlegible(ProblemaDeGeneracion):
    regla = "plantilla-ilegible"   # same stable id as validacion.py's problem

class ValoresIncompletos(ProblemaDeGeneracion):
    regla = "valores-incompletos"
    def __init__(self, faltantes):
        self.faltantes = tuple(sorted(faltantes))
        super().__init__(
            "Faltan valores obligatorios para generar el reporte: "
            + ", ".join(self.faltantes)
        )
```

`regla` and `faltantes` are the stable, test-assertable identifiers; the message is free to be
reworded — the exact convention `ProblemaDeDefinicion` documents (`validacion.py:40-50`).
Every missing id is accumulated in one raise (never fail-fast), mirroring "accumulate every
problem".

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tipos_reporte/generador.py` | Create | `generar_reporte` + the three exceptions + `_destinos` |
| `tipos_reporte/tests/test_generador.py` | Create | TDD suite (see Testing Strategy) |
| `tipos_reporte/tests/conftest.py` | Modify | Extend `plantilla_xlsx`; add `imagen_png` fixture |
| `tipos_reporte/validacion.py` | None | Read-only reuse of existing helpers |

## Test Fixture Extension

```python
@pytest.fixture
def imagen_png(tmp_path):
    """Distinct, identifiable PNGs: size is the discriminator after round trip."""
    from PIL import Image
    def _crear(nombre="img.png", tamano=(10, 10), color=(255, 0, 0)):
        ruta = tmp_path / nombre
        Image.new("RGB", tamano, color).save(ruta)
        return ruta
    return _crear
```

`plantilla_xlsx` gains two optional keyword args, keeping today's defaults so existing Slice-3
tests are untouched:

- `hojas_extra=()` → `wb.create_sheet(nombre)` per entry, to prove sheet-only export.
- `imagen=None` → path from `imagen_png`; `wb.active.add_image(Image(str(ruta)), "B2")`.

Tests identify which image survived by reopening the exported bytes and reading
`PIL.Image.open(ws._images[0].ref).size` — original `(10, 10)` vs logo `(20, 20)`.
`tipo_de_reporte_factory` is called with `plantilla=SimpleUploadedFile("plantilla.xlsx",
ruta.read_bytes())` (its default blob is not a real workbook) and `logo=SimpleUploadedFile(...)`,
under `settings.MEDIA_ROOT = tmp_path`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Scalar write to `celda`; range write to `celda_inicio`/`celda_fin`; falsy values written | Reopen returned `BytesIO` with `load_workbook`, assert cell values |
| Unit | `ValoresIncompletos.faltantes` lists all missing ids; nothing returned | `pytest.raises`, assert on `faltantes` tuple |
| Unit | `PlantillaIlegible` for missing file and for non-xlsx bytes | Factory default blob / deleted file |
| Integration | Logo present → swapped at same anchor; logo absent → original untouched | Compare image size and `anchor._from.col/row` before vs after |
| Integration | Only `estructura["hoja"]` in output; merges preserved | `hojas_extra` + `rangos`, assert `sheetnames` and `merged_cells.ranges` |

Strict TDD: every row above is a RED test before any line of `generador.py`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. The one untrusted-input surface (admin-uploaded `.xlsx`/image parsed
by openpyxl/Pillow) is contained by the same rule `validacion.validar_contra_plantilla` already
applies: any parser exception becomes a typed domain problem, never an uncaught exception.

## ADR-0002 Compliance

| Constraint | How honored |
|---|---|
| Never rebuild the workbook | Only cell `.value` writes + one `_images` element swap + sheet deletion; no sheet/style/merge authoring (D5) |
| Write only to merged-range anchor cells | Guaranteed upstream by R6 (`celda-no-es-ancla`) at activation; the generator trusts an *activated* definition and adds no re-check |
| Export only `estructura["hoja"]` | D5 |
| Logo is dynamic, swapped via `ws._images` before writing values | D4, executed at step 5, before step 6 |
| Formulas out of scope | Reference sheet has none |

No deviation from ADR-0002. ADR-0007's golden-file regression test remains an explicit,
proposal-scoped follow-up (no real anonymized template is committed).

## Migration / Rollout

No migration required. Additive module plus test/fixture changes; no model, schema or behavior
change to existing code.

## Open Questions

- [ ] Should checklist `items` default to required when `obligatorio` is absent? D3 currently
      treats them as optional; backlog #5's YAML authoring convention should set
      `obligatorio: true` explicitly if a missing item value must block generation.

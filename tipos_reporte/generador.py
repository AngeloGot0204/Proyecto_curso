"""Report generation service for `tipos_reporte` (backlog #4).

`generar_reporte(definicion, valores)` fills an already-**activated**
`DefinicionDeTipo`'s template with captured values and returns the
generated `.xlsx` bytes for the single declared sheet. It mutates a
*loaded copy* of the original template — never the stored file, never a
rebuilt workbook (ADR-0002) — and reuses `tipos_reporte/validacion.py`'s
`_iterar_nodos`/`_claves_de_celda_requeridas` so anchor logic exists in
exactly one place (design D1).

This module currently implements Phase 1 (exceptions), Phase 2 (template
loading + completeness validation) and Phase 3 (cell writing + sheet-only
export) of the change's `tasks.md`. Logo swap lands in a later PR.
"""

from io import BytesIO

from openpyxl import load_workbook

from tipos_reporte.validacion import _claves_de_celda_requeridas, _iterar_nodos


class ProblemaDeGeneracion(Exception):
    """Base for every foreseeable generation failure (design's
    Interfaces/Contracts), so backlog #7's future endpoint catches one type
    and never surfaces a raw 500 for a foreseeable problem."""

    regla = "problema-de-generacion"


class PlantillaIlegible(ProblemaDeGeneracion):
    """The template file could not be opened or parsed as a workbook.
    Same stable `regla` id `validacion.validar_contra_plantilla` uses for
    the equivalent problem, per design's Interfaces/Contracts."""

    regla = "plantilla-ilegible"


class ValoresIncompletos(ProblemaDeGeneracion):
    """One or more required ids are missing from `valores` (design D2/D3).
    `faltantes` is the stable, test-assertable identifier — the message is
    free to be reworded, mirroring `ProblemaDeDefinicion`'s convention
    (`validacion.py:40-50`). Every missing id is accumulated into one raise
    (never fail-fast)."""

    regla = "valores-incompletos"

    def __init__(self, faltantes):
        self.faltantes = tuple(sorted(faltantes))
        super().__init__(
            "Faltan valores obligatorios para generar el reporte: "
            + ", ".join(self.faltantes)
        )


# Design D1: the suffix a `valores` key gets, keyed by which cell key the
# node declares — "" for a scalar `celda`, "_inicio"/"_fin" for a range's
# two independent keys.
_SUFIJO_POR_CLAVE = {"celda": "", "celda_inicio": "_inicio", "celda_fin": "_fin"}


def _destinos(nodo):
    """`(clave_en_valores, coordenada)` pairs for one campo/item (design
    D1). Single derivation shared by the completeness pass and the write
    pass, so a validated-as-present key can never be written to the wrong
    cell — `_claves_de_celda_requeridas` already encodes range-vs-scalar."""
    return [
        (f"{nodo['id']}{_SUFIJO_POR_CLAVE[clave]}", nodo[clave])
        for clave in _claves_de_celda_requeridas(nodo.get("tipo"))
    ]


def _validar_completitud(estructura, valores):
    """Accumulate every required id absent from `valores` and raise ONE
    `ValoresIncompletos` listing all of them (design's Sequence, step 4;
    "accumulate every problem"; D2: membership test, never truthiness, so
    `False`/`0`/`""` count as present; D3: only `nodo.get("obligatorio")`
    truthy nodes are required)."""
    faltantes = [
        clave
        for _ubicacion, nodo, _clave_de_etiqueta in _iterar_nodos(estructura)
        if nodo.get("obligatorio")
        for clave, _coordenada in _destinos(nodo)
        if clave not in valores
    ]
    if faltantes:
        raise ValoresIncompletos(faltantes)


def _escribir_valores(hoja, estructura, valores):
    """Write every present `valores` key into its anchor cell (design's
    Sequence, step 6). Walks the same nodes `_validar_completitud` walks,
    but writes ANY key present in `valores` — not only required ones,
    per D3: present-but-not-required keys are written; absent optional
    keys leave their anchor cell untouched ("lo que no se escribe, no se
    altera"). D2: membership test, so `False`/`0`/`""` are written as-is,
    never skipped as if absent."""
    for _ubicacion, nodo, _clave_de_etiqueta in _iterar_nodos(estructura):
        for clave, coordenada in _destinos(nodo):
            if clave in valores:
                hoja[coordenada] = valores[clave]


def _exportar_solo_hoja_declarada(libro, nombre_hoja):
    """Delete every sheet other than the declared one and reset the active
    index (design D5). Deleting sheet OBJECTS never touches the target
    sheet's own merges/styles/drawings, since those live per-sheet or in
    workbook-level shared tables — no rebuild."""
    for nombre in [nombre for nombre in libro.sheetnames if nombre != nombre_hoja]:
        del libro[nombre]
    libro.active = 0


def generar_reporte(definicion, valores: dict):
    """Fill `definicion`'s template with `valores` and return the generated
    `.xlsx` bytes (design's Sequence, steps 1-4, 6-8 in this PR slice; step
    5 — logo swap — lands in the next PR).

    `definicion` must already be an ACTIVATED `DefinicionDeTipo` — this
    function trusts `definicion.estructura` and adds no re-validation of
    anchor cells (ADR-0002 Compliance table, "Write only to merged-range
    anchor cells").
    """
    tipo = definicion.tipo
    estructura = definicion.estructura
    plantilla = tipo.plantilla

    try:
        plantilla.open("rb")
    except (OSError, FileNotFoundError) as error:
        # Mirrors `servicios.activar_definicion`'s own guard: a missing
        # file in storage (deleted, ephemeral filesystem) must become a
        # `PlantillaIlegible`, never an uncaught exception (design's
        # Sequence, step 1).
        raise PlantillaIlegible(
            "No se pudo leer el archivo de plantilla (.xlsx)."
        ) from error

    try:
        try:
            libro = load_workbook(plantilla)
        except Exception as error:
            # Any parser failure (not just IO) becomes the same typed
            # problem (design's Sequence, step 2), mirroring
            # `validacion.validar_contra_plantilla`'s convention.
            raise PlantillaIlegible(
                "No se pudo leer el archivo de plantilla (.xlsx)."
            ) from error
    finally:
        plantilla.close()

    nombre_hoja = estructura["hoja"]
    try:
        hoja = libro[nombre_hoja]
    except KeyError as error:
        # Declared sheet missing from the actual workbook (design's
        # Sequence, step 3) — same typed problem, never a raw KeyError.
        raise PlantillaIlegible(
            f"La hoja '{nombre_hoja}' declarada no existe en la plantilla."
        ) from error

    # Design's Sequence, step 4: validation precedes every mutation, so no
    # partial write is ever observable, even in-memory (step 5, logo swap,
    # lands in a later PR).
    _validar_completitud(estructura, valores)

    # Design's Sequence, step 6: write every present value into its anchor
    # cell (step 5, logo swap, is not yet implemented in this PR slice).
    _escribir_valores(hoja, estructura, valores)

    # Design's Sequence, step 7: export only the declared sheet.
    _exportar_solo_hoja_declarada(libro, nombre_hoja)

    # Design's Sequence, step 8: materialize the final bytes.
    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer

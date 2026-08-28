"""Structural validation rules for a `DefinicionDeTipo.estructura` tree
(spec: "Exhaustive activation validation", "Closed data-type catalog";
design D5, D6).

This module holds ONLY R1-R4 (Slice 2): required keys, known data type,
valid Excel-style cell notation, and no cell collisions within one
definition. All functions here are pure — no database access, no
filesystem access, no `TipoDeReporte`/`DefinicionDeTipo` instance. They
operate directly on plain dicts (the JSON-serializable shape stored in
`DefinicionDeTipo.estructura`), so a definition can be validated before it
is ever saved.

R5 (template/sheet readable) and R6 (merged-range anchor) require an open
`.xlsx` workbook via `openpyxl` and belong to Slice 3 — not implemented
here. `validar_definicion`, the composer that runs both groups and returns
a `ResultadoDeValidacion`, is introduced alongside R5-R6 in that slice.
"""

from dataclasses import dataclass

from openpyxl.utils.cell import coordinate_from_string
from openpyxl.utils.exceptions import CellCoordinatesException

from tipos_reporte.models import TipoDeDato

# Data types whose destination is a cell RANGE (celda_inicio + celda_fin)
# rather than a single celda (design's Interfaces/Contracts catalog table).
_TIPOS_CON_RANGO = {TipoDeDato.RANGO_HORA_INICIO_FIN}

# Characters that make coordinate_from_string tolerate a shape the
# generator does not support: absolute references, ranges, and
# sheet-qualified references (design's Interfaces/Contracts note).
_CARACTERES_NO_PERMITIDOS_EN_CELDA = ("$", ":", "!")


@dataclass(frozen=True)
class ProblemaDeDefinicion:
    """One accumulated validation failure.

    `regla` is a stable identifier assertable in tests (design D5) — it
    must never change when only the human-readable `mensaje` is reworded.
    """

    regla: str
    ubicacion: str
    mensaje: str


def _es_celda_valida(valor) -> bool:
    if not isinstance(valor, str) or not valor:
        return False
    if any(caracter in valor for caracter in _CARACTERES_NO_PERMITIDOS_EN_CELDA):
        return False
    try:
        coordinate_from_string(valor)
    except (CellCoordinatesException, ValueError):
        return False
    return True


def _claves_de_celda_requeridas(tipo) -> list[str]:
    if tipo in _TIPOS_CON_RANGO:
        return ["celda_inicio", "celda_fin"]
    return ["celda"]


def _iterar_nodos(estructura: dict):
    """Yield `(ubicacion, nodo, clave_de_etiqueta)` for every campo/item in
    the tree. `clave_de_etiqueta` differs by node type: campos use
    `etiqueta`, items use `texto` (design's Interfaces/Contracts example)."""
    secciones = estructura.get("secciones") or []
    for i, seccion in enumerate(secciones):
        base = f"secciones[{i}]"
        for j, campo in enumerate(seccion.get("campos") or []):
            yield f"{base}.campos[{j}]", campo, "etiqueta"
        for j, item in enumerate(seccion.get("items") or []):
            yield f"{base}.items[{j}]", item, "texto"


def _validar_campos_obligatorios(ubicacion, nodo, clave_de_etiqueta):
    problemas = []

    def _requerir(clave):
        if not nodo.get(clave):
            problemas.append(
                ProblemaDeDefinicion(
                    regla="campo-obligatorio-ausente",
                    ubicacion=ubicacion,
                    mensaje=f"Falta la clave obligatoria '{clave}'.",
                )
            )

    _requerir("id")
    _requerir(clave_de_etiqueta)
    _requerir("tipo")

    tipo = nodo.get("tipo")
    if tipo in TipoDeDato.values:
        for clave in _claves_de_celda_requeridas(tipo):
            _requerir(clave)
        if tipo == TipoDeDato.SELECCION:
            _requerir("opciones")

    return problemas


def _validar_tipo_conocido(ubicacion, nodo):
    tipo = nodo.get("tipo")
    if tipo is not None and tipo not in TipoDeDato.values:
        return [
            ProblemaDeDefinicion(
                regla="tipo-de-dato-desconocido",
                ubicacion=ubicacion,
                mensaje=f"El tipo '{tipo}' no pertenece al catálogo cerrado.",
            )
        ]
    return []


def _validar_notacion_de_celda(ubicacion, nodo):
    problemas = []
    for clave in ("celda", "celda_inicio", "celda_fin"):
        valor = nodo.get(clave)
        if valor is None:
            continue
        if not _es_celda_valida(valor):
            problemas.append(
                ProblemaDeDefinicion(
                    regla="celda-mal-formada",
                    ubicacion=ubicacion,
                    mensaje=f"'{clave}': '{valor}' no es una notación de celda válida.",
                )
            )
    return problemas


def _validar_colisiones_de_celda(nodos):
    """Collision detection only considers already-valid cells (mirrors R6's
    documented precedent of only checking what already passed notation
    validation) — a shared typo is reported as `celda-mal-formada` for each
    occurrence, not additionally as a collision."""
    ocupantes: dict[str, list[str]] = {}
    for ubicacion, nodo, _clave_de_etiqueta in nodos:
        for clave in ("celda", "celda_inicio", "celda_fin"):
            valor = nodo.get(clave)
            if valor and _es_celda_valida(valor):
                ocupantes.setdefault(valor, []).append(ubicacion)

    problemas = []
    for celda, ubicaciones in ocupantes.items():
        if len(ubicaciones) > 1:
            for ubicacion in ubicaciones:
                problemas.append(
                    ProblemaDeDefinicion(
                        regla="celda-duplicada",
                        ubicacion=ubicacion,
                        mensaje=(
                            f"La celda '{celda}' está usada por más de un "
                            f"campo/ítem: {', '.join(ubicaciones)}."
                        ),
                    )
                )
    return problemas


def validar_estructura(estructura: dict) -> list[ProblemaDeDefinicion]:
    """Runs R1-R4 over the full definition and accumulates every problem
    found (spec: "Exhaustive activation validation") — never returns early."""
    problemas: list[ProblemaDeDefinicion] = []
    nodos = list(_iterar_nodos(estructura))

    for ubicacion, nodo, clave_de_etiqueta in nodos:
        problemas.extend(_validar_campos_obligatorios(ubicacion, nodo, clave_de_etiqueta))
        problemas.extend(_validar_tipo_conocido(ubicacion, nodo))
        problemas.extend(_validar_notacion_de_celda(ubicacion, nodo))

    problemas.extend(_validar_colisiones_de_celda(nodos))

    return problemas

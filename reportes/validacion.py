"""Aggregate validation of a `Reporte`'s persisted values (backlog
`validacion-datos-formulario`; spec `validacion-reporte`; design's
Interfaces/Contracts and Data Flow).

`validar_reporte(reporte)` re-reads every persisted `ValorDeReporte` row and
returns a `ResultadoDeRevision` with two buckets: `errores` (blocking) and
`advertencias` (non-blocking). The obligatorio-missing-value check reuses
`tipos_reporte.generador._validar_completitud` — via `try/except
ValoresIncompletos`, translating `.faltantes` into errores — so the
required/not-required decision lives in exactly one place and can never
drift from the generator (design's "Obligatorio reuse via
`_validar_completitud` exception translation" decision). This module's own
traversal (`_indice_de_campos`) supplies only *presentation* metadata
(`seccion_id`, `etiqueta`) — never the obligatorio decision itself.
"""

from dataclasses import dataclass

from django import forms

from reportes.valores import desde_texto
from tipos_reporte.generador import ValoresIncompletos, _validar_completitud
from tipos_reporte.models import TipoDeDato
from tipos_reporte.validacion import _iterar_nodos

# The exact persisted string that marks a `seleccion` field as "not
# compliant" (design's "'No cumple' = seleccion nodes only, exact string"
# decision) — case-sensitive, matched only against `seleccion` nodes.
_VALOR_NO_CUMPLE = "No cumple"

# Suffix a range node's two independent `valores` keys get, keyed by which
# half of the range the key represents (design's Interfaces/Contracts).
_SUFIJO_DE_ETIQUETA = {"_inicio": " — Inicio", "_fin": " — Fin"}


@dataclass(frozen=True)
class ProblemaDeReporte:
    """One accumulated validation finding — either an errore or an
    advertencia (design's Interfaces/Contracts). `regla` is a stable,
    test-assertable identifier; `mensaje` is reworkable prose never
    asserted in tests."""

    regla: str
    identificador_de_campo: str
    seccion_id: str
    etiqueta: str
    mensaje: str


@dataclass(frozen=True)
class ResultadoDeRevision:
    """The outcome of `validar_reporte` (design's Interfaces/Contracts):
    every accumulated finding, split into `errores` (blocking) and
    `advertencias` (non-blocking), plus a convenience `puede_generar`
    property. Named to avoid shadowing
    `tipos_reporte.validacion.ResultadoDeValidacion`."""

    errores: tuple[ProblemaDeReporte, ...]
    advertencias: tuple[ProblemaDeReporte, ...]

    @property
    def puede_generar(self) -> bool:
        return not self.errores


def _indice_de_campos(estructura: dict) -> dict:
    """Map every `valores`-dict key a node declares to
    `(seccion_id, etiqueta, nodo)` — *presentation* metadata only (design's
    Data Flow). Built once per `validar_reporte` call by walking each
    section in isolation with `_iterar_nodos` (mirrors
    `reportes.formularios.construir_formulario_seccion`'s per-section
    traversal), so `seccion_id` is always the enclosing section's own id."""
    from tipos_reporte.generador import claves_de_valor

    indice = {}
    for seccion in estructura.get("secciones") or []:
        seccion_id = seccion.get("id")
        for _ubicacion, nodo, clave_de_etiqueta in _iterar_nodos(
            {"secciones": [seccion]}
        ):
            etiqueta_base = nodo.get(clave_de_etiqueta, "")
            for clave in claves_de_valor(nodo):
                sufijo = clave[len(nodo["id"]) :]
                etiqueta = etiqueta_base + _SUFIJO_DE_ETIQUETA.get(sufijo, "")
                indice[clave] = (seccion_id, etiqueta, nodo)
    return indice


def _errores_por_obligatorios_faltantes(estructura, valores, indice):
    """Obligatorio-missing-value pass (design's Decision: exception
    translation). Calls the SAME function `generador.generar_reporte` calls
    — never a reimplemented traversal — so the required/not-required
    decision can never drift (spec scenario 3, locked by
    `test_validar_reporte_coincide_con_validar_completitud`)."""
    try:
        _validar_completitud(estructura, valores)
    except ValoresIncompletos as error:
        return [
            ProblemaDeReporte(
                regla="valor-obligatorio-faltante",
                identificador_de_campo=clave,
                seccion_id=indice[clave][0],
                etiqueta=indice[clave][1],
                mensaje=f"Falta completar '{indice[clave][1]}'.",
            )
            for clave in error.faltantes
        ]
    return []


def _advertencias_por_rango_invalido(estructura, valores, indice):
    """Stray `fin<=inicio` pass (design's Data Flow, step 4): re-parses
    both halves of every `rango-hora-inicio-fin` node through the SAME
    `TimeField` the wizard form uses (`desde_texto`, design D2's
    same-field-parses-back rule), and skips the pair entirely if either
    half is absent or fails to parse — never a blocking errore (spec
    scenario 4)."""
    campo_hora = forms.TimeField()
    advertencias = []
    for _ubicacion, nodo, _clave_de_etiqueta in _iterar_nodos(estructura):
        if nodo.get("tipo") != TipoDeDato.RANGO_HORA_INICIO_FIN:
            continue
        clave_inicio = f"{nodo['id']}_inicio"
        clave_fin = f"{nodo['id']}_fin"
        if clave_inicio not in valores or clave_fin not in valores:
            continue
        inicio = desde_texto(campo_hora, valores[clave_inicio])
        fin = desde_texto(campo_hora, valores[clave_fin])
        if inicio is None or fin is None:
            continue
        if fin <= inicio:
            seccion_id, etiqueta, _nodo = indice[clave_fin]
            advertencias.append(
                ProblemaDeReporte(
                    regla="rango-hora-invalido",
                    identificador_de_campo=clave_fin,
                    seccion_id=seccion_id,
                    etiqueta=etiqueta,
                    mensaje=f"'{etiqueta}': la hora de fin debe ser posterior a la de inicio.",
                )
            )
    return advertencias


def _advertencias_por_no_cumple_sin_observacion(estructura, valores, indice):
    """"No cumple" without observación pass (design's "'No cumple' =
    seleccion nodes only, exact string" decision; spec scenarios 5-6):
    matches only `seleccion` nodes whose persisted value is EXACTLY
    `"No cumple"`, and only when the companion `{id}_observacion` key is
    absent or blank."""
    advertencias = []
    for _ubicacion, nodo, _clave_de_etiqueta in _iterar_nodos(estructura):
        if nodo.get("tipo") != TipoDeDato.SELECCION:
            continue
        clave = nodo["id"]
        if valores.get(clave) != _VALOR_NO_CUMPLE:
            continue
        observacion = valores.get(f"{clave}_observacion", "")
        if observacion.strip():
            continue
        seccion_id, etiqueta, _nodo = indice[clave]
        advertencias.append(
            ProblemaDeReporte(
                regla="no-cumple-sin-observacion",
                identificador_de_campo=clave,
                seccion_id=seccion_id,
                etiqueta=etiqueta,
                mensaje=f"'{etiqueta}': agregá una observación para justificar 'No cumple'.",
            )
        )
    return advertencias


def validar_reporte(reporte) -> ResultadoDeRevision:
    """Walk `reporte.definicion.estructura` against its persisted
    `ValorDeReporte` rows and return a `ResultadoDeRevision` (design's Data
    Flow). One query builds `valores`; membership means "provided" (same
    rule `_validar_completitud` and `guardar_valor` already use, since
    `guardar_valor` deletes empties rather than persisting them)."""
    estructura = reporte.definicion.estructura
    valores = {
        valor.identificador_de_campo: valor.valor
        for valor in reporte.valores.all()
    }
    indice = _indice_de_campos(estructura)

    errores = _errores_por_obligatorios_faltantes(estructura, valores, indice)
    advertencias = _advertencias_por_rango_invalido(estructura, valores, indice)
    advertencias += _advertencias_por_no_cumple_sin_observacion(
        estructura, valores, indice
    )

    return ResultadoDeRevision(
        errores=tuple(errores), advertencias=tuple(advertencias)
    )

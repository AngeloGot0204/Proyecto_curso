"""Tests for `reportes.validacion.validar_reporte` (backlog
`validacion-datos-formulario`; spec `validacion-reporte`).

Strict TDD: every scenario below is written RED (failing, referencing
production code that does not exist yet) before `reportes/validacion.py`
lands. Covers the six spec scenarios plus the anti-drift lock against
`tipos_reporte.generador._validar_completitud`.
"""

import pytest

from reportes.models import ValorDeReporte
from tipos_reporte.generador import ValoresIncompletos, _validar_completitud


def _crear_valor(reporte, identificador_de_campo, valor, autor):
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo=identificador_de_campo,
        valor=valor,
        autor=autor,
    )


# ---------------------------------------------------------------------------
# Scenario: All obligatorio fields filled produces no errores
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_todos_los_obligatorios_completos_produce_errores_vacio(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    _crear_valor(reporte, "observaciones-generales", "Todo en orden.", autor)
    _crear_valor(reporte, "estado-general", "Cumple", autor)
    _crear_valor(reporte, "p-01_inicio", "08:00", autor)
    _crear_valor(reporte, "p-01_fin", "09:00", autor)

    resultado = validar_reporte(reporte)

    assert resultado.errores == ()


# ---------------------------------------------------------------------------
# Scenario: Missing obligatorio field produces an errore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_falta_un_obligatorio_produce_un_errore(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    # "estado-general" is left unset — every other obligatorio is filled.
    _crear_valor(reporte, "observaciones-generales", "Todo en orden.", autor)
    _crear_valor(reporte, "p-01_inicio", "08:00", autor)
    _crear_valor(reporte, "p-01_fin", "09:00", autor)

    resultado = validar_reporte(reporte)

    assert len(resultado.errores) == 1
    errore = resultado.errores[0]
    assert errore.identificador_de_campo == "estado-general"
    assert errore.seccion_id == "datos-generales"


# ---------------------------------------------------------------------------
# Scenario: Obligatorio detection matches the generator exactly (anti-drift)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validar_reporte_coincide_con_validar_completitud(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    # Only "estado-general" is filled — every other obligatorio is missing,
    # so both the range's inicio/fin keys AND the texto campo are absent.
    _crear_valor(reporte, "estado-general", "Cumple", autor)
    valores = {"estado-general": "Cumple"}

    resultado = validar_reporte(reporte)

    with pytest.raises(ValoresIncompletos) as excinfo:
        _validar_completitud(definicion.estructura, valores)

    faltantes_directos = set(excinfo.value.faltantes)
    faltantes_via_validar_reporte = {
        e.identificador_de_campo
        for e in resultado.errores
        if e.regla == "valor-obligatorio-faltante"
    }
    assert faltantes_via_validar_reporte == faltantes_directos
    assert faltantes_directos == {
        "observaciones-generales",
        "p-01_inicio",
        "p-01_fin",
    }


# ---------------------------------------------------------------------------
# Scenario: Stray hora_fin<=hora_inicio produces an advertencia, not an errore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rango_hora_invalido_produce_advertencia_no_errore(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    _crear_valor(reporte, "observaciones-generales", "Todo en orden.", autor)
    _crear_valor(reporte, "estado-general", "Cumple", autor)
    # `fin` (08:00) is not after `inicio` (09:00) — simulates a direct POST
    # that bypassed the client-side JS guard.
    _crear_valor(reporte, "p-01_inicio", "09:00", autor)
    _crear_valor(reporte, "p-01_fin", "08:00", autor)

    resultado = validar_reporte(reporte)

    assert resultado.errores == ()
    assert len(resultado.advertencias) == 1
    advertencia = resultado.advertencias[0]
    assert advertencia.regla == "rango-hora-invalido"
    assert advertencia.identificador_de_campo == "p-01_fin"


# ---------------------------------------------------------------------------
# Scenario: "No cumple" without observación produces an advertencia
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_cumple_sin_observacion_produce_advertencia(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    _crear_valor(reporte, "observaciones-generales", "Todo en orden.", autor)
    _crear_valor(reporte, "estado-general", "No cumple", autor)
    _crear_valor(reporte, "p-01_inicio", "08:00", autor)
    _crear_valor(reporte, "p-01_fin", "09:00", autor)
    # No "estado-general_observacion" row persisted.

    resultado = validar_reporte(reporte)

    assert resultado.errores == ()
    assert len(resultado.advertencias) == 1
    advertencia = resultado.advertencias[0]
    assert advertencia.regla == "no-cumple-sin-observacion"
    assert advertencia.identificador_de_campo == "estado-general"


# ---------------------------------------------------------------------------
# Scenario: "No cumple" with observación produces no advertencia for that item
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_cumple_con_observacion_no_produce_advertencia(
    estructura_con_validaciones,
    tipo_con_definicion_activa_factory,
    reporte_factory,
    usuario_factory,
):
    from reportes.validacion import validar_reporte

    tipo, definicion = tipo_con_definicion_activa_factory(
        estructura=estructura_con_validaciones()
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)
    autor = usuario_factory(username="autor-de-valores")

    _crear_valor(reporte, "observaciones-generales", "Todo en orden.", autor)
    _crear_valor(reporte, "estado-general", "No cumple", autor)
    _crear_valor(
        reporte, "estado-general_observacion", "Falta calibrar el equipo.", autor
    )
    _crear_valor(reporte, "p-01_inicio", "08:00", autor)
    _crear_valor(reporte, "p-01_fin", "09:00", autor)

    resultado = validar_reporte(reporte)

    assert resultado.errores == ()
    assert not any(
        a.identificador_de_campo == "estado-general" for a in resultado.advertencias
    )

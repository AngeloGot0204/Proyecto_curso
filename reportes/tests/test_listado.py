"""Tests for the pure helpers in `reportes.listado` (backlog #12, PR 1 of a
stacked-to-main chain; spec `listado-reportes`, design D2/D3/D4). No HTTP
involved — mirrors `reportes/tests/test_permisos.py`.
"""

import pytest

from reportes.listado import (
    aplicar_busqueda,
    normalizar_estado,
    reportes_accesibles,
)
from reportes.models import EstadoDeReporte, Reporte


@pytest.mark.django_db
def test_reportes_accesibles_incluye_creados_y_participados(
    reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
):
    """Spec 'Access-Scoped Report List': user A's accessible set contains
    R1 (created) and R2 (invited), not R3 (unrelated, created by B)."""
    a = usuario_factory(username="usuario_a")
    b = usuario_factory(username="usuario_b")
    tipo1, definicion1 = tipo_con_definicion_activa_factory(
        nombre="Tipo 1", codigo="tipo-1"
    )
    tipo2, definicion2 = tipo_con_definicion_activa_factory(
        nombre="Tipo 2", codigo="tipo-2"
    )
    tipo3, definicion3 = tipo_con_definicion_activa_factory(
        nombre="Tipo 3", codigo="tipo-3"
    )
    r1 = reporte_factory(tipo=tipo1, definicion=definicion1, creador=a)
    r2 = reporte_factory(tipo=tipo2, definicion=definicion2, creador=b)
    from reportes.models import ParticipacionEnReporte

    ParticipacionEnReporte.objects.create(reporte=r2, usuario=a)
    r3 = reporte_factory(tipo=tipo3, definicion=definicion3, creador=b)

    resultado = reportes_accesibles(a)

    assert set(resultado) == {r1, r2}
    assert r3 not in resultado


@pytest.mark.django_db
def test_reportes_accesibles_no_duplica_filas(
    reporte_factory, usuario_factory, participacion_factory
):
    """Proves `.distinct()` on the join: A is invited via one
    `ParticipacionEnReporte` row, and a second, unrelated participation on
    the same report (another invited user) must not multiply A's row."""
    a = usuario_factory(username="usuario_a")
    reporte = reporte_factory()
    from reportes.models import ParticipacionEnReporte

    ParticipacionEnReporte.objects.create(reporte=reporte, usuario=a)
    participacion_factory(reporte, username="otro_invitado")

    resultado = list(reportes_accesibles(a))

    assert resultado.count(reporte) == 1


@pytest.mark.django_db
def test_aplicar_busqueda_por_tipo_nombre(
    reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
):
    tipo_auditoria, definicion_auditoria = tipo_con_definicion_activa_factory(
        nombre="Auditoría de sitio", codigo="auditoria-sitio"
    )
    tipo_inspeccion, definicion_inspeccion = tipo_con_definicion_activa_factory(
        nombre="Inspección de equipos", codigo="inspeccion-equipos"
    )
    r_auditoria = reporte_factory(
        tipo=tipo_auditoria,
        definicion=definicion_auditoria,
        creador=usuario_factory(username="creador_auditoria"),
    )
    reporte_factory(
        tipo=tipo_inspeccion,
        definicion=definicion_inspeccion,
        creador=usuario_factory(username="creador_inspeccion"),
    )

    resultado = aplicar_busqueda(Reporte.objects.all(), "Auditoría de sitio")

    assert list(resultado) == [r_auditoria]


@pytest.mark.django_db
def test_aplicar_busqueda_por_tipo_codigo(
    reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
):
    tipo_a, definicion_a = tipo_con_definicion_activa_factory(
        nombre="Tipo A", codigo="codigo-a"
    )
    tipo_b, definicion_b = tipo_con_definicion_activa_factory(
        nombre="Tipo B", codigo="codigo-b"
    )
    r_a = reporte_factory(
        tipo=tipo_a,
        definicion=definicion_a,
        creador=usuario_factory(username="creador_tipo_a"),
    )
    reporte_factory(
        tipo=tipo_b,
        definicion=definicion_b,
        creador=usuario_factory(username="creador_tipo_b"),
    )

    resultado = aplicar_busqueda(Reporte.objects.all(), "codigo-a")

    assert list(resultado) == [r_a]


@pytest.mark.django_db
def test_aplicar_busqueda_por_creador_username(
    reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
):
    creador_buscado = usuario_factory(username="ana_creadora")
    otro_creador = usuario_factory(username="beto_creador")
    tipo1, definicion1 = tipo_con_definicion_activa_factory(
        nombre="Tipo X", codigo="tipo-creador-1"
    )
    tipo2, definicion2 = tipo_con_definicion_activa_factory(
        nombre="Tipo Y", codigo="tipo-creador-2"
    )
    r_buscado = reporte_factory(
        tipo=tipo1, definicion=definicion1, creador=creador_buscado
    )
    reporte_factory(tipo=tipo2, definicion=definicion2, creador=otro_creador)

    resultado = aplicar_busqueda(Reporte.objects.all(), "ana_creadora")

    assert list(resultado) == [r_buscado]


@pytest.mark.django_db
def test_aplicar_busqueda_ignora_acentos(
    reporte_factory, tipo_con_definicion_activa_factory
):
    """Design D4: `q="auditoria"` (no accent) matches a `tipo.nombre` of
    `"Auditoría"` (accented)."""
    tipo, definicion = tipo_con_definicion_activa_factory(
        nombre="Auditoría", codigo="auditoria"
    )
    reporte = reporte_factory(tipo=tipo, definicion=definicion)

    resultado = aplicar_busqueda(Reporte.objects.all(), "auditoria")

    assert list(resultado) == [reporte]


@pytest.mark.django_db
def test_aplicar_busqueda_q_vacio_es_no_op(
    reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
):
    tipo1, definicion1 = tipo_con_definicion_activa_factory(
        nombre="Tipo 1", codigo="tipo-vacio-1"
    )
    tipo2, definicion2 = tipo_con_definicion_activa_factory(
        nombre="Tipo 2", codigo="tipo-vacio-2"
    )
    r1 = reporte_factory(
        tipo=tipo1,
        definicion=definicion1,
        creador=usuario_factory(username="creador_vacio_1"),
    )
    r2 = reporte_factory(
        tipo=tipo2,
        definicion=definicion2,
        creador=usuario_factory(username="creador_vacio_2"),
    )

    resultado = aplicar_busqueda(Reporte.objects.all(), "")
    resultado_espacios = aplicar_busqueda(Reporte.objects.all(), "   ")

    assert set(resultado) == {r1, r2}
    assert set(resultado_espacios) == {r1, r2}


def test_normalizar_estado_valores_validos():
    assert normalizar_estado("terminado") == EstadoDeReporte.TERMINADO
    assert normalizar_estado("en_progreso") == EstadoDeReporte.EN_PROGRESO


@pytest.mark.parametrize("valor", ["", None, "basura", "TERMINADO"])
def test_normalizar_estado_valores_invalidos_devuelven_vacio(valor):
    assert normalizar_estado(valor) == ""

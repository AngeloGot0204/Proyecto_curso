"""Tests for the pure helpers in `tipos_reporte.listado` (backlog #13, S-14,
PR 1 of a stacked-to-main chain; spec `administracion-tipos-reporte`, design
D3). No HTTP involved — mirrors `reportes/tests/test_listado.py`.
"""

import pytest

from tipos_reporte.listado import aplicar_busqueda, tipos_administrables
from tipos_reporte.models import TipoDeReporte


@pytest.mark.django_db
def test_tipos_administrables_ordena_por_nombre_y_id(tipo_de_reporte_factory):
    """Design D3: ordered `("nombre", "id")` — alphabetical, with the
    mandatory `id` tiebreaker for two rows sharing the same `nombre`."""
    tipo_z = tipo_de_reporte_factory(nombre="Zeta", codigo="orden-zeta")
    tipo_a = tipo_de_reporte_factory(nombre="Alfa", codigo="orden-alfa")
    tipo_a_empate_1 = tipo_de_reporte_factory(nombre="Alfa", codigo="orden-alfa-empate-1")
    tipo_a_empate_2 = tipo_de_reporte_factory(nombre="Alfa", codigo="orden-alfa-empate-2")

    resultado = list(tipos_administrables())

    ids_alfa_esperados = sorted([tipo_a.id, tipo_a_empate_1.id, tipo_a_empate_2.id])
    assert [t.id for t in resultado[:3]] == ids_alfa_esperados
    assert resultado[3] == tipo_z


@pytest.mark.django_db
def test_tipos_administrables_select_related_definicion_activa(
    tipo_de_reporte_factory, django_assert_num_queries
):
    """Design D3, mirrors #12: no extra query when accessing
    `definicion_activa` on each row of the returned queryset."""
    tipo_de_reporte_factory(nombre="Con select related", codigo="select-related-1")
    tipo_de_reporte_factory(nombre="Con select related 2", codigo="select-related-2")

    with django_assert_num_queries(1):
        for tipo in tipos_administrables():
            _ = tipo.definicion_activa


@pytest.mark.django_db
def test_aplicar_busqueda_por_nombre(tipo_de_reporte_factory):
    coincide = tipo_de_reporte_factory(nombre="Auditoría de sitio", codigo="busqueda-nombre-1")
    tipo_de_reporte_factory(nombre="Inspección de equipos", codigo="busqueda-nombre-2")

    resultado = aplicar_busqueda(TipoDeReporte.objects.all(), "Auditoría de sitio")

    assert list(resultado) == [coincide]


@pytest.mark.django_db
def test_aplicar_busqueda_por_codigo(tipo_de_reporte_factory):
    coincide = tipo_de_reporte_factory(nombre="Tipo A", codigo="busqueda-codigo-a")
    tipo_de_reporte_factory(nombre="Tipo B", codigo="busqueda-codigo-b")

    resultado = aplicar_busqueda(TipoDeReporte.objects.all(), "busqueda-codigo-a")

    assert list(resultado) == [coincide]


@pytest.mark.django_db
def test_aplicar_busqueda_ignora_acentos(tipo_de_reporte_factory):
    """Design D3: `q="auditoria"` (no accent) matches a `nombre` of
    `"Auditoría"` (accented)."""
    coincide = tipo_de_reporte_factory(nombre="Auditoría", codigo="busqueda-acentos")

    resultado = aplicar_busqueda(TipoDeReporte.objects.all(), "auditoria")

    assert list(resultado) == [coincide]


@pytest.mark.django_db
def test_aplicar_busqueda_q_vacio_es_no_op(tipo_de_reporte_factory):
    t1 = tipo_de_reporte_factory(nombre="Tipo 1", codigo="busqueda-vacio-1")
    t2 = tipo_de_reporte_factory(nombre="Tipo 2", codigo="busqueda-vacio-2")

    resultado = aplicar_busqueda(TipoDeReporte.objects.all(), "")
    resultado_espacios = aplicar_busqueda(TipoDeReporte.objects.all(), "   ")

    assert set(resultado) == {t1, t2}
    assert set(resultado_espacios) == {t1, t2}

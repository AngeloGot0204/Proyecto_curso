"""Tests for the pure helpers in `reportes.listado` (backlog #12, PR 1 of a
stacked-to-main chain; spec `listado-reportes`, design D2/D3/D4). No HTTP
involved — mirrors `reportes/tests/test_permisos.py`.
"""

import pytest
from django.db.models import Exists, OuterRef

from reportes.listado import (
    aplicar_busqueda,
    normalizar_estado,
    reportes_accesibles,
)
from reportes.models import EstadoDeReporte, Reporte

# ---------------------------------------------------------------------------
# Phase 2 (backlog #12, PR 1 of a stacked-to-main chain; spec
# `listado-reportes`; design D1-D5) additions: bucket/avance/relacion pure
# helpers. Focused command: `pytest reportes/tests/test_listado.py -q`.
# ---------------------------------------------------------------------------


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
    """Design's 'Interfaces / Contracts': `?estado=` values are now the
    BUCKETS ids — `terminado`/`en_progreso` stay byte-identical to the old
    `EstadoDeReporte` values (the `cierre-reporte` redirect keeps working
    unchanged), and `listo_para_generar` is the new, third valid id."""
    assert normalizar_estado("terminado") == "terminado"
    assert normalizar_estado("en_progreso") == "en_progreso"
    assert normalizar_estado("listo_para_generar") == "listo_para_generar"


@pytest.mark.parametrize("valor", ["", None, "basura", "TERMINADO"])
def test_normalizar_estado_valores_invalidos_devuelven_vacio(valor):
    assert normalizar_estado(valor) == ""


def _estructura_con_n_obligatorios(n):
    """Synthetic `estructura` with `n` obligatorio `texto` campos in one
    section, ids `campo-0`..`campo-{n-1}` (test-local helper for
    `porcentaje_de_avance`'s ratio scenarios — no template/generation
    concerns involved, so `tipo`/`celda` are minimal placeholders)."""
    return {
        "secciones": [
            {
                "id": "seccion-unica",
                "titulo": "Sección única",
                "campos": [
                    {
                        "id": f"campo-{i}",
                        "etiqueta": f"Campo {i}",
                        "tipo": "texto",
                        "obligatorio": True,
                        "celda": "M1",
                    }
                    for i in range(n)
                ],
            }
        ]
    }


class TestPorcentajeDeAvance:
    """Task 2.1 RED / 2.2 GREEN: `porcentaje_de_avance(estructura,
    faltantes)`, design D5 — floor, not round; `total == 0` ⇒ 100."""

    def test_siete_de_diez_es_setenta_por_ciento(self):
        from reportes.listado import porcentaje_de_avance

        estructura = _estructura_con_n_obligatorios(10)
        faltantes = tuple(f"campo-{i}" for i in range(7, 10))

        assert porcentaje_de_avance(estructura, faltantes) == 70

    def test_doscientos_cuarenta_y_nueve_de_doscientos_cincuenta_es_noventa_y_nueve_por_ciento(self):
        """Design D5's exact rationale: `round` would show 100% here —
        floor keeps '100% ⟺ nothing obligatory missing' exact."""
        from reportes.listado import porcentaje_de_avance

        estructura = _estructura_con_n_obligatorios(250)
        faltantes = ("campo-249",)

        assert porcentaje_de_avance(estructura, faltantes) == 99

    def test_sin_obligatorios_es_cien_por_ciento(self):
        from reportes.listado import porcentaje_de_avance

        estructura = _estructura_con_n_obligatorios(0)

        assert porcentaje_de_avance(estructura, ()) == 100


class TestBucketDeReporte:
    """Task 2.3 RED / 2.4 GREEN: `bucket_de_reporte(tiene_visto_bueno,
    puede_generar)`, priority terminado > listo_para_generar >
    en_progreso (spec 'Status Bucket Grouping')."""

    def test_con_visto_bueno_es_terminado_sin_importar_puede_generar(self):
        from reportes.listado import bucket_de_reporte

        assert bucket_de_reporte(tiene_visto_bueno=True, puede_generar=True) == "terminado"
        assert bucket_de_reporte(tiene_visto_bueno=True, puede_generar=False) == "terminado"

    def test_sin_visto_bueno_y_puede_generar_es_listo_para_generar(self):
        from reportes.listado import bucket_de_reporte

        assert (
            bucket_de_reporte(tiene_visto_bueno=False, puede_generar=True)
            == "listo_para_generar"
        )

    def test_sin_visto_bueno_y_no_puede_generar_es_en_progreso(self):
        from reportes.listado import bucket_de_reporte

        assert (
            bucket_de_reporte(tiene_visto_bueno=False, puede_generar=False)
            == "en_progreso"
        )


class TestNormalizarRelacion:
    """Task 2.5 RED / 2.6 GREEN: `normalizar_relacion` — creados/
    compartidos/todos pass through, unrecognized/None → todos (design's
    ADDED 'Creador/Compartido/Todos Filter')."""

    @pytest.mark.parametrize("valor", ["creados", "compartidos", "todos"])
    def test_valores_validos_pasan_igual(self, valor):
        from reportes.listado import normalizar_relacion

        assert normalizar_relacion(valor) == valor

    @pytest.mark.parametrize("valor", [None, "", "basura", "CREADOS"])
    def test_valores_invalidos_devuelven_todos(self, valor):
        from reportes.listado import normalizar_relacion

        assert normalizar_relacion(valor) == "todos"


@pytest.mark.django_db
class TestAplicarRelacion:
    """Task 2.6 GREEN: `aplicar_relacion(qs, usuario, relacion)` narrows the
    already access-scoped queryset."""

    def test_creados_solo_devuelve_los_propios(
        self, reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
    ):
        from reportes.listado import aplicar_relacion
        from reportes.models import ParticipacionEnReporte

        a = usuario_factory(username="relacion-creados-a")
        tipo1, definicion1 = tipo_con_definicion_activa_factory(
            nombre="Relacion creados 1", codigo="relacion-creados-1"
        )
        tipo2, definicion2 = tipo_con_definicion_activa_factory(
            nombre="Relacion creados 2", codigo="relacion-creados-2"
        )
        propio = reporte_factory(creador=a, tipo=tipo1, definicion=definicion1)
        ajeno = reporte_factory(tipo=tipo2, definicion=definicion2)
        ParticipacionEnReporte.objects.create(reporte=ajeno, usuario=a)

        resultado = aplicar_relacion(
            Reporte.objects.filter(pk__in=[propio.pk, ajeno.pk]), a, "creados"
        )

        assert list(resultado) == [propio]

    def test_compartidos_excluye_los_propios(
        self, reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
    ):
        from reportes.listado import aplicar_relacion
        from reportes.models import ParticipacionEnReporte

        a = usuario_factory(username="relacion-compartidos-a")
        tipo1, definicion1 = tipo_con_definicion_activa_factory(
            nombre="Relacion compartidos 1", codigo="relacion-compartidos-1"
        )
        tipo2, definicion2 = tipo_con_definicion_activa_factory(
            nombre="Relacion compartidos 2", codigo="relacion-compartidos-2"
        )
        propio = reporte_factory(creador=a, tipo=tipo1, definicion=definicion1)
        compartido = reporte_factory(tipo=tipo2, definicion=definicion2)
        ParticipacionEnReporte.objects.create(reporte=compartido, usuario=a)

        resultado = aplicar_relacion(
            Reporte.objects.filter(pk__in=[propio.pk, compartido.pk]), a, "compartidos"
        )

        assert list(resultado) == [compartido]

    def test_todos_no_filtra(
        self, reporte_factory, usuario_factory, tipo_con_definicion_activa_factory
    ):
        from reportes.listado import aplicar_relacion
        from reportes.models import ParticipacionEnReporte

        a = usuario_factory(username="relacion-todos-a")
        tipo1, definicion1 = tipo_con_definicion_activa_factory(
            nombre="Relacion todos 1", codigo="relacion-todos-1"
        )
        tipo2, definicion2 = tipo_con_definicion_activa_factory(
            nombre="Relacion todos 2", codigo="relacion-todos-2"
        )
        propio = reporte_factory(creador=a, tipo=tipo1, definicion=definicion1)
        compartido = reporte_factory(tipo=tipo2, definicion=definicion2)
        ParticipacionEnReporte.objects.create(reporte=compartido, usuario=a)
        qs = Reporte.objects.filter(pk__in=[propio.pk, compartido.pk])

        resultado = aplicar_relacion(qs, a, "todos")

        assert set(resultado) == {propio, compartido}


@pytest.mark.django_db
class TestConstruirTarjetasYAgruparPorBucket:
    """Task 2.8 RED / 2.9 GREEN: `TarjetaDeReporte` fields, BUCKETS-ordered
    `[{id, titulo, tarjetas}]` (design's Interfaces/Contracts)."""

    def test_construir_tarjetas_calcula_bucket_y_avance(
        self,
        reporte_factory,
        usuario_factory,
        estructura_con_validaciones,
        tipo_con_definicion_activa_factory,
    ):
        from reportes.listado import construir_tarjetas
        from reportes.models import ValorDeReporte, VistoBueno

        a = usuario_factory(username="construir-tarjetas-a")
        tipo, definicion = tipo_con_definicion_activa_factory(
            estructura=estructura_con_validaciones(),
            nombre="Construir tarjetas",
            codigo="construir-tarjetas",
        )
        reporte = reporte_factory(creador=a, tipo=tipo, definicion=definicion)
        # `estructura_con_validaciones` declares 4 obligatorio keys
        # (observaciones-generales, estado-general, p-01_inicio, p-01_fin);
        # only one is filled here.
        ValorDeReporte.objects.create(
            reporte=reporte,
            identificador_de_campo="estado-general",
            valor="Cumple",
            autor=a,
        )

        qs = Reporte.objects.filter(pk=reporte.pk).annotate(
            tiene_visto_bueno=Exists(
                VistoBueno.objects.filter(reporte=OuterRef("pk"))
            )
        )
        tarjetas = construir_tarjetas(qs)

        assert len(tarjetas) == 1
        tarjeta = tarjetas[0]
        assert tarjeta.reporte == reporte
        assert tarjeta.bucket == "en_progreso"
        assert tarjeta.avance == 25
        assert tarjeta.numero_registro == reporte.numero_registro

    def test_construir_tarjetas_terminado_con_visto_bueno(
        self, reporte_factory, usuario_factory
    ):
        from reportes.listado import construir_tarjetas
        from reportes.models import VistoBueno

        a = usuario_factory(username="construir-tarjetas-terminado")
        reporte = reporte_factory(creador=a)
        VistoBueno.objects.create(reporte=reporte, usuario=a)

        qs = Reporte.objects.filter(pk=reporte.pk).annotate(
            tiene_visto_bueno=Exists(
                VistoBueno.objects.filter(reporte=OuterRef("pk"))
            )
        )
        tarjetas = construir_tarjetas(qs)

        assert tarjetas[0].bucket == "terminado"

    def test_agrupar_por_bucket_ordena_segun_buckets_y_omite_vacios(self):
        from reportes.listado import BUCKETS, TarjetaDeReporte, agrupar_por_bucket

        tarjeta_terminada = TarjetaDeReporte(
            reporte=None, bucket="terminado", avance=100, numero_registro=1
        )
        tarjeta_en_progreso = TarjetaDeReporte(
            reporte=None, bucket="en_progreso", avance=0, numero_registro=2
        )

        grupos = agrupar_por_bucket([tarjeta_terminada, tarjeta_en_progreso])

        assert [g["id"] for g in grupos] == [id_ for id_, _titulo in BUCKETS]
        en_progreso = next(g for g in grupos if g["id"] == "en_progreso")
        terminado = next(g for g in grupos if g["id"] == "terminado")
        listo = next(g for g in grupos if g["id"] == "listo_para_generar")
        assert en_progreso["tarjetas"] == [tarjeta_en_progreso]
        assert terminado["tarjetas"] == [tarjeta_terminada]
        assert listo["tarjetas"] == []

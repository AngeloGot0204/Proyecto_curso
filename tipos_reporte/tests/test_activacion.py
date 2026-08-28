"""Activation service tests (Slice 4: `servicios.activar_definicion`,
`servicios.desactivar_tipo`).

Covers spec requirement "Fully valid definition activates cleanly" and
design D8 (validate-then-mutate ordering, `transaction.atomic()`), D2
(version assigned once, at first successful activation, never reassigned
by a later re-activation of the same row).

`activar_definicion` never raises for a validation failure — it returns the
`ResultadoDeValidacion` either way (design D8's own docstring). Callers
(the admin action) decide how to surface `es_valida is False`.
"""

import threading

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tipos_reporte.models import DefinicionDeTipo, Estado
from tipos_reporte.servicios import activar_definicion, desactivar_tipo


def _crear_borrador(tipo, estructura, **kwargs):
    defaults = {
        "tipo": tipo,
        "archivo_yaml": SimpleUploadedFile("definicion.yaml", b"secciones: []"),
        "yaml_fuente": "secciones: []",
        "estructura": estructura,
        "estado": Estado.BORRADOR,
    }
    defaults.update(kwargs)
    return DefinicionDeTipo.objects.create(**defaults)


def _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx, **kwargs):
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))
    with open(destino, "rb") as archivo:
        contenido = archivo.read()
    defaults = {"plantilla": SimpleUploadedFile("plantilla.xlsx", contenido)}
    defaults.update(kwargs)
    return tipo_de_reporte_factory(**defaults)


@pytest.mark.django_db
def test_activar_definicion_valida_asigna_version_y_actualiza_fk(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Spec scenario: Fully valid definition activates cleanly — the row
    transitions borrador -> activa, gets its first version, and the tipo's
    FK now points at it (design D1, D2, D8)."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    definicion = _crear_borrador(tipo, definicion_valida())

    resultado = activar_definicion(definicion)

    definicion.refresh_from_db()
    tipo.refresh_from_db()
    assert resultado.es_valida is True
    assert definicion.estado == Estado.ACTIVA
    assert definicion.version == 1
    assert definicion.activada_en is not None
    assert tipo.definicion_activa_id == definicion.pk


@pytest.mark.django_db
def test_activar_definicion_invalida_no_muta_nada(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Design D8: nothing is mutated until `resultado.es_valida` is true —
    an invalid definition must leave the row and the tipo untouched."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    estructura = definicion_valida()
    del estructura["secciones"][0]["campos"][0]["tipo"]
    definicion = _crear_borrador(tipo, estructura)

    resultado = activar_definicion(definicion)

    definicion.refresh_from_db()
    tipo.refresh_from_db()
    assert resultado.es_valida is False
    assert definicion.estado == Estado.BORRADOR
    assert definicion.version is None
    assert tipo.definicion_activa_id is None


@pytest.mark.django_db
def test_activar_nueva_definicion_mueve_la_anterior_a_historica(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Activating a second draft for the same tipo must move the previously
    active row to `historica` and assign the new row the next version
    number (design D2's incremental, per-tipo versioning)."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    primera = _crear_borrador(tipo, definicion_valida())
    activar_definicion(primera)

    segunda = _crear_borrador(tipo, definicion_valida())
    resultado = activar_definicion(segunda)

    primera.refresh_from_db()
    segunda.refresh_from_db()
    tipo.refresh_from_db()
    assert resultado.es_valida is True
    assert primera.estado == Estado.HISTORICA
    assert segunda.estado == Estado.ACTIVA
    assert segunda.version == 2
    assert tipo.definicion_activa_id == segunda.pk


@pytest.mark.django_db
def test_reactivar_definicion_historica_reusa_su_version_original(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Design D2: re-activating a row that already has a version must NOT
    reassign it — a version identifies a content snapshot, not an
    activation event."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    primera = _crear_borrador(tipo, definicion_valida())
    activar_definicion(primera)
    segunda = _crear_borrador(tipo, definicion_valida())
    activar_definicion(segunda)

    resultado = activar_definicion(primera)

    primera.refresh_from_db()
    segunda.refresh_from_db()
    tipo.refresh_from_db()
    assert resultado.es_valida is True
    assert primera.estado == Estado.ACTIVA
    assert primera.version == 1
    assert segunda.estado == Estado.HISTORICA
    assert tipo.definicion_activa_id == primera.pk


@pytest.mark.django_db
def test_desactivar_tipo_limpia_fk_y_marca_historica(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """S-14 offers a plain deactivation toggle — the FK is cleared and the
    formerly active row becomes `historica`, keeping its version."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    definicion = _crear_borrador(tipo, definicion_valida())
    activar_definicion(definicion)

    desactivar_tipo(tipo)

    definicion.refresh_from_db()
    tipo.refresh_from_db()
    assert tipo.definicion_activa_id is None
    assert definicion.estado == Estado.HISTORICA
    assert definicion.version == 1


@pytest.mark.django_db
def test_desactivar_tipo_sin_definicion_activa_es_no_op(tipo_de_reporte_factory):
    """Deactivating a tipo with no active definition must not raise."""
    tipo = tipo_de_reporte_factory()

    desactivar_tipo(tipo)

    tipo.refresh_from_db()
    assert tipo.definicion_activa_id is None


@pytest.mark.django_db
def test_activar_definicion_lockea_el_tipo_con_select_for_update(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Code-review fix: concurrent activations of the SAME tipo must be
    serialized — two overlapping calls could otherwise both compute the
    same "next version" (`_siguiente_version()`) before either commits, and
    the second crashes with an uncaught `IntegrityError` against
    `definicion_version_unica_por_tipo`. Proven here by asserting the SQL
    Django actually executes inside `activar_definicion`'s atomic block
    includes a row lock (`FOR UPDATE`) on the tipo."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    definicion = _crear_borrador(tipo, definicion_valida())

    with CaptureQueriesContext(connection) as contexto:
        resultado = activar_definicion(definicion)

    assert resultado.es_valida is True
    consultas_con_lock = [
        q["sql"] for q in contexto.captured_queries if "FOR UPDATE" in q["sql"].upper()
    ]
    assert consultas_con_lock, (
        "activar_definicion debe lockear el tipo (select_for_update) para "
        "serializar activaciones concurrentes del mismo tipo"
    )


@pytest.mark.django_db(transaction=True)
def test_activar_definicion_serializa_con_una_activacion_concurrente_del_mismo_tipo(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Functional proof of the same fix: while another transaction holds the
    tipo's row lock open (an in-flight, uncommitted activation), a second
    `activar_definicion` call for that SAME tipo must block instead of
    racing ahead — and must complete successfully once the first releases
    the lock (commits)."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    definicion = _crear_borrador(tipo, definicion_valida())

    lock_adquirido = threading.Event()
    liberar_lock = threading.Event()
    orden = []

    def _mantener_lock_externo():
        from django.db import transaction as tx

        from tipos_reporte.models import TipoDeReporte

        try:
            with tx.atomic():
                TipoDeReporte.objects.select_for_update().get(pk=tipo.pk)
                orden.append("lock-externo-adquirido")
                lock_adquirido.set()
                liberar_lock.wait(timeout=5)
            orden.append("lock-externo-liberado")
        finally:
            connection.close()

    resultado_contenedor = {}

    def _activar_en_hilo():
        try:
            resultado_contenedor["resultado"] = activar_definicion(definicion)
            orden.append("activacion-completada")
        finally:
            connection.close()

    hilo_lock = threading.Thread(target=_mantener_lock_externo)
    hilo_lock.start()
    assert lock_adquirido.wait(timeout=5)

    hilo_activacion = threading.Thread(target=_activar_en_hilo)
    hilo_activacion.start()
    hilo_activacion.join(timeout=1)
    assert hilo_activacion.is_alive(), (
        "activar_definicion no debería completar mientras otra transacción "
        "mantiene el lock del mismo tipo"
    )

    liberar_lock.set()
    hilo_lock.join(timeout=5)
    hilo_activacion.join(timeout=5)

    assert not hilo_activacion.is_alive()
    assert orden.index("lock-externo-liberado") < orden.index("activacion-completada")
    assert resultado_contenedor["resultado"].es_valida is True
    definicion.refresh_from_db()
    assert definicion.estado == Estado.ACTIVA
    assert definicion.version == 1


@pytest.mark.django_db
def test_activar_definicion_con_plantilla_ilegible_en_storage_reporta_problema(
    tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    """Code-review fix: `validacion.validar_contra_plantilla` documents that a
    template problem must NEVER be an uncaught exception — it always becomes
    a `plantilla-ilegible` problem. If the template file is missing from
    storage (deleted, or an ephemeral filesystem), `plantilla.open("rb")`
    itself raises `FileNotFoundError` before `validar_contra_plantilla` ever
    gets a chance to catch anything, so the service must guard that open()
    too instead of letting it propagate as an uncaught 500."""
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    import os

    os.remove(tipo.plantilla.path)
    definicion = _crear_borrador(tipo, definicion_valida())

    resultado = activar_definicion(definicion)

    definicion.refresh_from_db()
    tipo.refresh_from_db()
    assert resultado.es_valida is False
    assert any(p.regla == "plantilla-ilegible" for p in resultado.problemas)
    assert definicion.estado == Estado.BORRADOR
    assert tipo.definicion_activa_id is None


@pytest.mark.django_db
def test_segundo_tipo_estructuralmente_distinto_se_activa_sin_cambios(
    tipo_de_reporte_factory, plantilla_xlsx
):
    """Design's extensibility proof: a structurally different definition
    (a plain `texto` field, no `rango-hora-inicio-fin`) against its own
    template activates with zero production-code changes."""
    tipo = _tipo_con_plantilla(
        tipo_de_reporte_factory,
        plantilla_xlsx,
        codigo="otro-tipo",
        nombre="Otro tipo",
    )
    estructura = {
        "tipo": "otro-tipo",
        "plantilla": "otra.xlsx",
        "hoja": "REPORTE",
        "secciones": [
            {
                "id": "s1",
                "titulo": "Sección 1",
                "campos": [
                    {"id": "c1", "etiqueta": "Campo 1", "tipo": "texto", "celda": "M12"}
                ],
            }
        ],
    }
    definicion = _crear_borrador(tipo, estructura)

    resultado = activar_definicion(definicion)

    definicion.refresh_from_db()
    assert resultado.es_valida is True
    assert definicion.estado == Estado.ACTIVA
    assert definicion.version == 1

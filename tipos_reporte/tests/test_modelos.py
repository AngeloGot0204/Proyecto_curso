"""Model-layer tests for `TipoDeReporte`/`DefinicionDeTipo` (Slice 1).

Covers spec requirements "TipoDeReporte model" (codigo uniqueness) and
"Deletion blocked after any successful activation", plus design decisions
D1-D3 (versioning, immutability), D7 (version_formato), and D9 (delete
guards). Validation rules (R1-R6) and the activation service belong to
later slices and are not exercised here.
"""

from datetime import timedelta

import threading

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from tipos_reporte.models import DefinicionDeTipo, Estado, TipoDeReporte


def _crear_definicion(tipo, **kwargs):
    """Direct row creation bypassing the (not-yet-existing) activation
    service — Slice 1 tests the model/state invariants in isolation."""
    defaults = {
        "tipo": tipo,
        "archivo_yaml": SimpleUploadedFile("definicion.yaml", b"secciones: []"),
        "yaml_fuente": "secciones: []",
        "estructura": {"secciones": []},
        "estado": Estado.BORRADOR,
        "version": None,
        "activada_en": None,
    }
    defaults.update(kwargs)
    return DefinicionDeTipo.objects.create(**defaults)


# --- Requirement: TipoDeReporte model — codigo uniqueness -----------------


@pytest.mark.django_db
def test_codigo_uniqueness_is_enforced(tipo_de_reporte_factory):
    """Spec scenario: codigo uniqueness is enforced."""
    tipo_de_reporte_factory(codigo="instalacion-resinas")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            tipo_de_reporte_factory(
                codigo="instalacion-resinas",
                nombre="Otro nombre",
                plantilla=SimpleUploadedFile("otra.xlsx", b"otro-contenido"),
            )


@pytest.mark.django_db
def test_tipo_de_reporte_is_created_inactive_by_default(tipo_de_reporte_factory):
    """Spec scenario: TipoDeReporte is created inactive by default."""
    tipo = tipo_de_reporte_factory()

    assert tipo.activo is False
    assert tipo.definicion_activa_id is None


# --- Design D1/D2/D7: the four named database constraints -----------------


@pytest.mark.django_db
def test_definicion_una_activa_por_tipo_constraint(tipo_de_reporte_factory):
    """Only one `activa` DefinicionDeTipo per tipo (design D1)."""
    tipo = tipo_de_reporte_factory()
    _crear_definicion(tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now())

    with pytest.raises(IntegrityError, match="definicion_una_activa_por_tipo"):
        with transaction.atomic():
            _crear_definicion(
                tipo, estado=Estado.ACTIVA, version=2, activada_en=timezone.now()
            )


@pytest.mark.django_db
def test_definicion_un_borrador_por_tipo_constraint(tipo_de_reporte_factory):
    """Only one `borrador` DefinicionDeTipo per tipo (design D1)."""
    tipo = tipo_de_reporte_factory()
    _crear_definicion(tipo, estado=Estado.BORRADOR)

    with pytest.raises(IntegrityError, match="definicion_un_borrador_por_tipo"):
        with transaction.atomic():
            _crear_definicion(tipo, estado=Estado.BORRADOR)


@pytest.mark.django_db
def test_definicion_version_unica_por_tipo_constraint(tipo_de_reporte_factory):
    """Version numbers cannot repeat within the same tipo (design D2)."""
    tipo = tipo_de_reporte_factory()
    ahora = timezone.now()
    _crear_definicion(tipo, estado=Estado.HISTORICA, version=1, activada_en=ahora)

    with pytest.raises(IntegrityError, match="definicion_version_unica_por_tipo"):
        with transaction.atomic():
            _crear_definicion(
                tipo, estado=Estado.HISTORICA, version=1, activada_en=ahora
            )


@pytest.mark.django_db
def test_definicion_estado_implica_version_constraint(tipo_de_reporte_factory):
    """A `borrador` row must have version=NULL and activada_en=NULL, and a
    non-borrador row must have both set (design D1's nullable-version
    rationale, enforced as a CheckConstraint)."""
    tipo = tipo_de_reporte_factory()

    with pytest.raises(IntegrityError, match="definicion_estado_implica_version"):
        with transaction.atomic():
            _crear_definicion(tipo, estado=Estado.BORRADOR, version=1)


# --- Design D3: immutability of a non-draft DefinicionDeTipo --------------


@pytest.mark.django_db
def test_editing_frozen_fields_on_activa_definicion_raises_via_save(
    tipo_de_reporte_factory,
):
    """Changing a CONGELADOS field (e.g. `estructura`) on an `activa` row via
    the normal save() path must be rejected (design D3)."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(
        tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )

    definicion.estructura = {"secciones": [{"id": "nueva"}]}
    with pytest.raises(ValidationError):
        definicion.save()


@pytest.mark.django_db
def test_editing_non_frozen_field_on_activa_definicion_is_allowed(
    tipo_de_reporte_factory,
):
    """`version` is not the only field on the row — a non-CONGELADOS field
    (design D3 only freezes tipo_id/estructura/yaml_fuente/version) must
    remain editable, proving save() targets specific fields, not the whole
    row."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(
        tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )

    nueva_fecha = timezone.now() - timedelta(days=1)
    definicion.activada_en = nueva_fecha
    definicion.save()
    definicion.refresh_from_db()

    assert definicion.activada_en == nueva_fecha


@pytest.mark.django_db
def test_queryset_update_bypassing_immutability_on_activa_row_raises(
    tipo_de_reporte_factory,
):
    """`QuerySet.update()` bypasses `save()`, so a dedicated guard must catch
    an attempt to change a CONGELADOS field on a non-draft row through it
    (design D3's stated residual gap otherwise)."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(
        tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )

    with pytest.raises(ValidationError):
        DefinicionDeTipo.objects.filter(pk=definicion.pk).update(
            estructura={"secciones": [{"id": "otra"}]}
        )


@pytest.mark.django_db
def test_primera_activacion_asigna_version_sin_disparar_inmutabilidad(
    tipo_de_reporte_factory,
):
    """Regression (found while building Slice 4's activation service): the
    borrador -> activa transition itself assigns `version` for the first
    time, which must NOT trip the immutability guard — only a row that was
    ALREADY non-borrador before this save is frozen (design D3)."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(tipo, estado=Estado.BORRADOR)

    definicion.version = 1
    definicion.activada_en = timezone.now()
    definicion.estado = Estado.ACTIVA
    definicion.save()
    definicion.refresh_from_db()

    assert definicion.estado == Estado.ACTIVA
    assert definicion.version == 1


@pytest.mark.django_db
def test_queryset_update_on_borrador_row_is_allowed(tipo_de_reporte_factory):
    """The `update()` guard must only block non-draft rows — a borrador stays
    editable through `update()` too."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(tipo, estado=Estado.BORRADOR)

    DefinicionDeTipo.objects.filter(pk=definicion.pk).update(
        estructura={"secciones": [{"id": "editado"}]}
    )
    definicion.refresh_from_db()

    assert definicion.estructura == {"secciones": [{"id": "editado"}]}


# --- Code-review fix: the immutability guard's read is lockeada -----------


@pytest.mark.django_db
def test_save_lockea_la_fila_anterior_con_select_for_update(tipo_de_reporte_factory):
    """Code-review fix: the immutability guard's `anterior = ...get(pk=...)`
    read must use `select_for_update()` — otherwise two concurrent processes
    could both pass the guard (both read the row as `activa`, both see no
    frozen-field changes from each other) before either writes, letting the
    second overwrite fields that should be immutable (design D3). Proven by
    asserting the SQL Django emits during `save()` on an existing row
    includes a row lock (`FOR UPDATE`)."""
    tipo = tipo_de_reporte_factory()
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura={"secciones": []},
        estado=Estado.ACTIVA,
        version=1,
        activada_en=timezone.now(),
    )

    with CaptureQueriesContext(connection) as contexto:
        definicion.activada_en = timezone.now()
        definicion.save()

    consultas_con_lock = [
        q["sql"] for q in contexto.captured_queries if "FOR UPDATE" in q["sql"].upper()
    ]
    assert consultas_con_lock, (
        "save() debe lockear la fila anterior (select_for_update) al leerla "
        "para el guard de inmutabilidad"
    )


@pytest.mark.django_db(transaction=True)
def test_save_espera_el_lock_mantenido_por_otra_transaccion(tipo_de_reporte_factory):
    """Functional proof of the same fix: while another transaction holds the
    row's lock open (an in-flight, uncommitted save), a concurrent `save()`
    on that SAME row must block instead of racing ahead to read a
    pre-write snapshot of `anterior`."""
    tipo = tipo_de_reporte_factory()
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura={"secciones": []},
        estado=Estado.ACTIVA,
        version=1,
        activada_en=timezone.now(),
    )

    lock_adquirido = threading.Event()
    liberar_lock = threading.Event()
    orden = []

    def _mantener_lock_externo():
        from django.db import transaction as tx

        try:
            with tx.atomic():
                DefinicionDeTipo.objects.select_for_update().get(pk=definicion.pk)
                orden.append("lock-externo-adquirido")
                lock_adquirido.set()
                liberar_lock.wait(timeout=5)
            orden.append("lock-externo-liberado")
        finally:
            connection.close()

    def _guardar_en_hilo():
        try:
            fila = DefinicionDeTipo.objects.get(pk=definicion.pk)
            fila.activada_en = timezone.now()
            fila.save()
            orden.append("guardado-completado")
        finally:
            connection.close()

    hilo_lock = threading.Thread(target=_mantener_lock_externo)
    hilo_lock.start()
    assert lock_adquirido.wait(timeout=5)

    hilo_guardado = threading.Thread(target=_guardar_en_hilo)
    hilo_guardado.start()
    hilo_guardado.join(timeout=1)
    assert hilo_guardado.is_alive(), (
        "save() no debería completar mientras otra transacción mantiene "
        "el lock de la misma fila"
    )

    liberar_lock.set()
    hilo_lock.join(timeout=5)
    hilo_guardado.join(timeout=5)

    assert not hilo_guardado.is_alive()
    assert orden.index("lock-externo-liberado") < orden.index("guardado-completado")


# --- Design D9: deletion blocked once ever activated -----------------------


@pytest.mark.django_db
def test_definicion_delete_blocked_for_ever_activated_row(tipo_de_reporte_factory):
    """`DefinicionDeTipo.delete()` on an ever-activated (historica) row must
    be blocked (spec: Deletion blocked after any successful activation)."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(
        tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )

    with pytest.raises(ValidationError):
        definicion.delete()


@pytest.mark.django_db
def test_definicion_queryset_delete_blocked_for_ever_activated_row(
    tipo_de_reporte_factory,
):
    """The bulk `QuerySet.delete()` path must be independently blocked — this
    is the path a plain object-level admin guard would miss (design D9)."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(
        tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )

    with pytest.raises(ValidationError):
        DefinicionDeTipo.objects.filter(pk=definicion.pk).delete()


@pytest.mark.django_db
def test_definicion_delete_allowed_for_never_activated_row(tipo_de_reporte_factory):
    """Spec scenario: Deletion is allowed for a TipoDeReporte that was never
    activated — mirrored here at the DefinicionDeTipo level for a borrador
    row that has never been activated."""
    tipo = tipo_de_reporte_factory()
    definicion = _crear_definicion(tipo, estado=Estado.BORRADOR)

    definicion.delete()

    assert not DefinicionDeTipo.objects.filter(pk=definicion.pk).exists()


@pytest.mark.django_db
def test_tipo_delete_blocked_for_ever_activated_type(tipo_de_reporte_factory):
    """Spec scenario: Deletion is blocked for a TipoDeReporte that was ever
    activated, even if currently deactivated (definicion_activa cleared but
    a historica row with activada_en still exists)."""
    tipo = tipo_de_reporte_factory()
    _crear_definicion(
        tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )

    with pytest.raises(ValidationError):
        tipo.delete()


@pytest.mark.django_db
def test_tipo_queryset_delete_blocked_for_ever_activated_type(tipo_de_reporte_factory):
    """The bulk `QuerySet.delete()` path for TipoDeReporte must be
    independently blocked too (mirrors the DefinicionDeTipo case, design D9)."""
    tipo = tipo_de_reporte_factory()
    _crear_definicion(
        tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )

    with pytest.raises(ValidationError):
        TipoDeReporte.objects.filter(pk=tipo.pk).delete()


@pytest.mark.django_db
def test_tipo_delete_allowed_for_never_activated_type(tipo_de_reporte_factory):
    """Spec scenario: Deletion is allowed for a TipoDeReporte that was never
    successfully activated."""
    tipo = tipo_de_reporte_factory()

    tipo.delete()

    assert not TipoDeReporte.objects.filter(pk=tipo.pk).exists()

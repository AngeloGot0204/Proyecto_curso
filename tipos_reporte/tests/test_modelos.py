"""Model-layer tests for `TipoDeReporte`/`DefinicionDeTipo` (Slice 1).

Covers spec requirements "TipoDeReporte model" (codigo uniqueness) and
"Deletion blocked after any successful activation", plus design decisions
D1-D3 (versioning, immutability), D7 (version_formato), and D9 (delete
guards). Validation rules (R1-R6) and the activation service belong to
later slices and are not exercised here.
"""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
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

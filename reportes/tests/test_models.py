"""Model-layer tests for `Reporte`/`ValorDeReporte` (backlog #5, Phase 2).

Covers spec `reportes-modelo`:
- Requirement: Reporte creation (both scenarios)
- Requirement: ValorDeReporte per captured value (unique constraint per
  `reporte` + `identificador_de_campo`, backing `update_or_create`, design
  Interfaces/Contracts)
"""

import pytest
from django.db import IntegrityError, transaction

from reportes.models import (
    EstadoDeReporte,
    Generacion,
    Reporte,
    ValorDeReporte,
    VistoBueno,
)


# --- Requirement: Reporte creation -----------------------------------------


@pytest.mark.django_db
def test_reporte_is_created_with_tipo_definicion_creador_and_estado_inicial(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Spec scenario: First wizard step creates the Reporte."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()

    reporte = Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=usuario
    )

    assert reporte.tipo_id == tipo.id
    assert reporte.definicion_id == definicion.id
    assert reporte.creador_id == usuario.id
    assert reporte.fecha_creacion is not None
    assert reporte.estado == EstadoDeReporte.EN_PROGRESO


@pytest.mark.django_db
def test_subsequent_step_reuses_the_existing_reporte(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Spec scenario: Subsequent steps reference the existing Reporte — the
    model layer must allow looking a `Reporte` back up by primary key
    instead of creating a second row."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()
    reporte = Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=usuario
    )

    reencontrado = Reporte.objects.get(pk=reporte.pk)

    assert reencontrado.pk == reporte.pk
    assert Reporte.objects.count() == 1


# --- Requirement: ValorDeReporte per captured value ------------------------


@pytest.mark.django_db
def test_valor_de_reporte_is_created_with_identificador_valor_autor_fecha(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Spec scenario: Simple field value is stored as one row."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()
    reporte = Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=usuario
    )

    valor = ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="turno",
        valor="Día",
        autor=usuario,
    )

    assert valor.reporte_id == reporte.id
    assert valor.identificador_de_campo == "turno"
    assert valor.valor == "Día"
    assert valor.autor_id == usuario.id
    assert valor.fecha is not None


# --- Requirement: EstadoDeReporte.TERMINADO Member ------------------------


def test_estado_de_reporte_admite_terminado():
    """Spec `cierre-reporte`: `TERMINADO` is additive to `EN_PROGRESO`, with
    the exact stable value `"terminado"` used by `cerrar_reporte`."""
    assert EstadoDeReporte.TERMINADO == "terminado"
    assert EstadoDeReporte.TERMINADO in EstadoDeReporte.values


@pytest.mark.django_db
def test_valor_de_reporte_unique_constraint_per_reporte_y_campo(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Design Interfaces/Contracts: `valor_unico_por_reporte_y_campo` backs
    `update_or_create` (D3) — a second row for the same `reporte` +
    `identificador_de_campo` pair must be rejected at the database level."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()
    reporte = Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=usuario
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="turno", valor="Día", autor=usuario
    )

    with pytest.raises(IntegrityError, match="valor_unico_por_reporte_y_campo"):
        with transaction.atomic():
            ValorDeReporte.objects.create(
                reporte=reporte,
                identificador_de_campo="turno",
                valor="Noche",
                autor=usuario,
            )


# --- Requirement: VistoBueno Model -----------------------------------------


@pytest.mark.django_db
def test_visto_bueno_defaults_y_auto_now_add(reporte_factory, usuario_factory):
    """Spec `cierre-reporte` scenario: VistoBueno created on closure — the
    model itself stores `reporte`, `usuario`, and an auto-populated
    `fecha`."""
    reporte = reporte_factory()
    usuario = usuario_factory(username="aprobador")

    visto_bueno = VistoBueno.objects.create(reporte=reporte, usuario=usuario)

    assert visto_bueno.reporte_id == reporte.id
    assert visto_bueno.usuario_id == usuario.id
    assert visto_bueno.fecha is not None


@pytest.mark.django_db
def test_segundo_visto_bueno_lanza_integrity_error(reporte_factory, usuario_factory):
    """Design D1: `VistoBueno` is a `OneToOneField(Reporte)` — DB-enforced
    single closure per `Reporte`."""
    reporte = reporte_factory()
    usuario = usuario_factory(username="aprobador")
    VistoBueno.objects.create(reporte=reporte, usuario=usuario)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VistoBueno.objects.create(reporte=reporte, usuario=usuario)


# --- Requirement: Generacion Model ------------------------------------------


@pytest.mark.django_db
def test_generacion_permite_multiples_filas(reporte_factory, usuario_factory):
    """Spec `generacion-documento` scenario: Repeated generation creates
    multiple rows — `Generacion` is an unbounded audit log, no uniqueness
    constraint (design D3)."""
    reporte = reporte_factory()
    usuario = usuario_factory(username="generador")

    primera = Generacion.objects.create(
        reporte=reporte, definicion=reporte.definicion, usuario=usuario
    )
    segunda = Generacion.objects.create(
        reporte=reporte, definicion=reporte.definicion, usuario=usuario
    )

    assert Generacion.objects.filter(reporte=reporte).count() == 2
    assert primera.id != segunda.id
    assert segunda.definicion_id == reporte.definicion_id
    assert segunda.fecha is not None

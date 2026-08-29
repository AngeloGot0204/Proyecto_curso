"""Model-layer tests for `Reporte`/`ValorDeReporte` (backlog #5, Phase 2).

Covers spec `reportes-modelo`:
- Requirement: Reporte creation (both scenarios)
- Requirement: ValorDeReporte per captured value (unique constraint per
  `reporte` + `identificador_de_campo`, backing `update_or_create`, design
  Interfaces/Contracts)
"""

import pytest
from django.db import IntegrityError, transaction

from reportes.models import EstadoDeReporte, Reporte, ValorDeReporte


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

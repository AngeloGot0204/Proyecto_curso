"""Tests for `reportes.permisos.tiene_acceso` (backlog #8, Phase 1; spec
`colaboracion-reporte`, design D1). Pure predicate — no HTTP involved.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from reportes.permisos import tiene_acceso


@pytest.mark.django_db
def test_tiene_acceso_creador_sin_fila_de_participacion(
    reporte_factory, usuario_factory
):
    """Design D1 / spec 'Creator has no participation row': the creator has
    access via the creator check, with zero `ParticipacionEnReporte` rows."""
    creador = usuario_factory(username="creador")
    reporte = reporte_factory(creador=creador)

    assert tiene_acceso(reporte, creador) is True


@pytest.mark.django_db
def test_tiene_acceso_participante_invitado(
    reporte_factory, usuario_factory, participacion_factory
):
    """Spec 'Participation row created on invite': an invited participant
    has access via their `ParticipacionEnReporte` row."""
    reporte = reporte_factory()
    invitado = participacion_factory(reporte, username="invitado")

    assert tiene_acceso(reporte, invitado) is True


@pytest.mark.django_db
def test_tiene_acceso_desconocido_devuelve_false(
    reporte_factory, usuario_factory
):
    """A stranger — neither creator nor invited — has no access."""
    reporte = reporte_factory()
    desconocido = usuario_factory(username="desconocido")

    assert tiene_acceso(reporte, desconocido) is False


@pytest.mark.django_db
def test_tiene_acceso_usuario_no_autenticado_devuelve_false(reporte_factory):
    """Defensive branch: an unauthenticated user never has access, even if
    all callers are expected to be `@login_required`."""
    reporte = reporte_factory()

    assert tiene_acceso(reporte, AnonymousUser()) is False

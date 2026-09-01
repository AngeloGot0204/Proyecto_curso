"""Tests for `usuarios.decorators.solo_administradores` (backlog #13, S-14;
spec `administracion-tipos-reporte` — "Admin-Role-Gated Access"; design D1).

The anonymous case (`test_solo_administradores_anonimo_redirige_antes_de_leer_rol`)
deliberately uses `RequestFactory` + `AnonymousUser`, no DB: it proves
`login_required` (applied outermost, design D1) redirects BEFORE
`request.user.es_administrador` is ever read — `AnonymousUser` has no such
attribute, so reading it would raise `AttributeError`, not merely fail an
assertion.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from usuarios.decorators import solo_administradores


def _vista_dummy(request):
    from django.http import HttpResponse

    return HttpResponse("ok-vista-ejecutada")


@pytest.mark.django_db
def test_solo_administradores_permite_administrador(usuario_factory):
    """Spec 'Administrator reaches the list view': admin user -> 200, the
    view body actually runs (real content in the response, not a smoke
    check)."""
    from usuarios.models import Rol

    admin = usuario_factory(username="decorador-admin", rol=Rol.ADMINISTRADOR)
    request = RequestFactory().get("/cualquier-ruta/")
    request.user = admin

    respuesta = solo_administradores(_vista_dummy)(request)

    assert respuesta.status_code == 200
    assert respuesta.content == b"ok-vista-ejecutada"


@pytest.mark.django_db
def test_solo_administradores_bloquea_no_administrador_403(usuario_factory):
    """Spec 'Non-administrator is blocked with 403': authenticated
    non-admin -> PermissionDenied is raised, the view body never runs."""
    from usuarios.models import Rol

    no_admin = usuario_factory(username="decorador-no-admin", rol=Rol.USUARIO)
    request = RequestFactory().get("/cualquier-ruta/")
    request.user = no_admin

    with pytest.raises(PermissionDenied):
        solo_administradores(_vista_dummy)(request)


def test_solo_administradores_anonimo_redirige_antes_de_leer_rol():
    """Spec 'Anonymous user is redirected', design D1: `login_required` is
    applied OUTERMOST, so an anonymous request 302s to LOGIN_URL before
    `request.user.es_administrador` is ever accessed. No DB needed — proves
    the property is never read for `AnonymousUser` (which has no
    `es_administrador` attribute at all)."""
    request = RequestFactory().get("/cualquier-ruta/")
    request.user = AnonymousUser()

    respuesta = solo_administradores(_vista_dummy)(request)

    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("login"))

"""Sidebar de navegación principal (Inicio / Mis reportes / Nuevo reporte,
y para administradores: Usuarios / Tipos de reporte).

Visible para usuarios autenticados en cualquier pantalla (base.html), oculta
en el login. Reusa el patrón `.escritorio__sidebar` que ya existía sólo en
tipos_reporte, ahora unificado via `templates/partials/sidebar.html`.

Assertions check `href="<url>"` presence, not exact `>texto<` matches — each
nav item wraps its label with an inline SVG icon, so the rendered markup has
whitespace/tags between the `<a>` and its text, not a bare `>texto<` pair.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_sidebar_visible_para_usuario_autenticado(client, usuario_factory):
    usuario = usuario_factory(username="nav-autenticado")
    client.force_login(usuario)

    response = client.get(reverse("reportes_mis"))
    contenido = response.content.decode()

    assert 'class="escritorio"' in contenido
    assert "escritorio__sidebar" in contenido
    assert f'href="{reverse("reportes_mis")}"' in contenido
    assert f'href="{reverse("reportes_seleccion_tipo")}"' in contenido


@pytest.mark.django_db
def test_sidebar_no_admin_no_ve_enlaces_de_administracion(client, usuario_factory):
    """`Usuario.Rol.USUARIO` (default de `usuario_factory`) no debe ver
    "Usuarios"/"Tipos de reporte" — ambas vistas están gateadas por
    `@solo_administradores` y devuelven 403; mostrarlas a cualquiera
    invitaba a tocar un link que rompe."""
    usuario = usuario_factory(username="nav-no-admin")
    client.force_login(usuario)

    response = client.get(reverse("reportes_mis"))
    contenido = response.content.decode()

    assert f'href="{reverse("usuarios_lista")}"' not in contenido
    assert f'href="{reverse("tipos_lista")}"' not in contenido


@pytest.mark.django_db
def test_sidebar_admin_ve_enlaces_de_administracion(client, usuario_factory):
    admin = usuario_factory(username="nav-admin", rol="administrador")
    client.force_login(admin)

    response = client.get(reverse("reportes_mis"))
    contenido = response.content.decode()

    assert f'href="{reverse("usuarios_lista")}"' in contenido
    assert f'href="{reverse("tipos_lista")}"' in contenido


@pytest.mark.django_db
def test_sidebar_enlaces_apuntan_a_rutas_reales(client, usuario_factory):
    usuario = usuario_factory(username="nav-enlaces")
    client.force_login(usuario)

    response = client.get(reverse("reportes_mis"))
    contenido = response.content.decode()

    assert reverse("inicio") in contenido
    assert reverse("reportes_seleccion_tipo") in contenido
    assert reverse("reportes_mis") in contenido


def test_sidebar_no_aparece_en_login():
    from django.test import Client

    response = Client().get(reverse("login"))
    contenido = response.content.decode()

    assert "escritorio__sidebar" not in contenido

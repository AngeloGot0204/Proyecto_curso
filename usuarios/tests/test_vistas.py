"""View tests for the users administration screen (BACKLOG.md #1, S-13:
"admin de usuarios: buscador, crear, editar rol/organización, resetear
contraseña, suspender"). Mirrors `tipos_reporte/tests/test_vistas.py`'s
conventions. Focused command: `pytest usuarios/tests/test_vistas.py -q`.
"""

import pytest
from django.urls import reverse

from usuarios.models import Rol, Usuario

# ---------------------------------------------------------------------------
# usuarios_lista
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lista_anonimo_redirige_login(client, usuario_factory):
    usuario_factory()

    response = client.get(reverse("usuarios_lista"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_lista_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="lista-no-admin", rol=Rol.USUARIO)
    client.force_login(no_admin)

    response = client.get(reverse("usuarios_lista"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_lista_administrador_ve_usuarios(
    client, administrador_factory, usuario_factory
):
    admin = administrador_factory(username="lista-admin")
    usuario_factory(username="alguien-mas")
    client.force_login(admin)

    response = client.get(reverse("usuarios_lista"))

    assert response.status_code == 200
    usernames = {u.username for u in response.context["page_obj"]}
    assert "lista-admin" in usernames
    assert "alguien-mas" in usernames


@pytest.mark.django_db
def test_lista_busca_por_username(client, administrador_factory, usuario_factory):
    admin = administrador_factory(username="buscador-admin")
    usuario_factory(username="carlos-mendoza")
    usuario_factory(username="ana-torres")
    client.force_login(admin)

    response = client.get(reverse("usuarios_lista"), {"q": "carlos"})

    usernames = {u.username for u in response.context["page_obj"]}
    assert usernames == {"carlos-mendoza"}


# ---------------------------------------------------------------------------
# usuarios_crear
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_crear_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="crear-no-admin", rol=Rol.USUARIO)
    client.force_login(no_admin)

    response = client.get(reverse("usuarios_crear"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_crear_administrador_crea_usuario_con_password_hasheada(
    client, administrador_factory
):
    admin = administrador_factory(username="crear-admin")
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_crear"),
        {
            "username": "nuevo-usuario",
            "rol": Rol.USUARIO,
            "password": "Contrasena-Segura-123",
        },
    )

    assert response.status_code == 302
    creado = Usuario.objects.get(username="nuevo-usuario")
    assert creado.rol == Rol.USUARIO
    assert creado.check_password("Contrasena-Segura-123")
    assert creado.password != "Contrasena-Segura-123"


@pytest.mark.django_db
def test_crear_password_debil_no_crea_usuario(client, administrador_factory):
    admin = administrador_factory(username="crear-admin-debil")
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_crear"),
        {"username": "otro-usuario", "rol": Rol.USUARIO, "password": "123"},
    )

    assert response.status_code == 200
    assert not Usuario.objects.filter(username="otro-usuario").exists()


# ---------------------------------------------------------------------------
# usuarios_editar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_editar_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="editar-no-admin", rol=Rol.USUARIO)
    objetivo = usuario_factory(username="editar-objetivo")
    client.force_login(no_admin)

    response = client.get(reverse("usuarios_editar", args=[objetivo.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_editar_administrador_cambia_rol(client, administrador_factory, usuario_factory):
    admin = administrador_factory(username="editar-admin")
    objetivo = usuario_factory(username="editar-objetivo-2", rol=Rol.USUARIO)
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_editar", args=[objetivo.id]), {"rol": Rol.ADMINISTRADOR}
    )

    assert response.status_code == 302
    objetivo.refresh_from_db()
    assert objetivo.rol == Rol.ADMINISTRADOR
    assert objetivo.is_staff is True


# ---------------------------------------------------------------------------
# usuarios_resetear_password
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resetear_password_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="resetear-no-admin", rol=Rol.USUARIO)
    objetivo = usuario_factory(username="resetear-objetivo")
    client.force_login(no_admin)

    response = client.get(reverse("usuarios_resetear_password", args=[objetivo.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_resetear_password_administrador_cambia_password(
    client, administrador_factory, usuario_factory
):
    admin = administrador_factory(username="resetear-admin")
    objetivo = usuario_factory(username="resetear-objetivo-2")
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_resetear_password", args=[objetivo.id]),
        {"nueva_password": "Otra-Contrasena-456"},
    )

    assert response.status_code == 302
    objetivo.refresh_from_db()
    assert objetivo.check_password("Otra-Contrasena-456")


# ---------------------------------------------------------------------------
# usuarios_suspender
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_suspender_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="suspender-no-admin", rol=Rol.USUARIO)
    objetivo = usuario_factory(username="suspender-objetivo")
    client.force_login(no_admin)

    response = client.post(reverse("usuarios_suspender", args=[objetivo.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_suspender_administrador_desactiva_usuario_activo(
    client, administrador_factory, usuario_factory
):
    admin = administrador_factory(username="suspender-admin")
    objetivo = usuario_factory(username="suspender-objetivo-2", is_active=True)
    client.force_login(admin)

    response = client.post(reverse("usuarios_suspender", args=[objetivo.id]))

    assert response.status_code == 302
    objetivo.refresh_from_db()
    assert objetivo.is_active is False


@pytest.mark.django_db
def test_suspender_administrador_reactiva_usuario_suspendido(
    client, administrador_factory, usuario_factory
):
    admin = administrador_factory(username="reactivar-admin")
    objetivo = usuario_factory(username="reactivar-objetivo", is_active=False)
    client.force_login(admin)

    response = client.post(reverse("usuarios_suspender", args=[objetivo.id]))

    assert response.status_code == 302
    objetivo.refresh_from_db()
    assert objetivo.is_active is True


@pytest.mark.django_db
def test_suspender_get_no_permitido(client, administrador_factory, usuario_factory):
    admin = administrador_factory(username="suspender-get-admin")
    objetivo = usuario_factory(username="suspender-get-objetivo")
    client.force_login(admin)

    response = client.get(reverse("usuarios_suspender", args=[objetivo.id]))

    assert response.status_code == 405


@pytest.mark.django_db
def test_suspender_no_puede_autosuspenderse(client, administrador_factory):
    admin = administrador_factory(username="autosuspender-admin", is_active=True)
    client.force_login(admin)

    response = client.post(reverse("usuarios_suspender", args=[admin.id]))

    assert response.status_code == 302
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_suspender_administrador_puede_suspender_a_otro_administrador(
    client, administrador_factory
):
    """A suspend that doesn't target the actor is unrestricted — the actor
    stays active regardless, so this can never leave zero active admins."""
    admin_actor = administrador_factory(username="suspender-actor-admin")
    otro_admin = administrador_factory(
        username="suspender-otro-admin", is_active=True
    )
    client.force_login(admin_actor)

    response = client.post(reverse("usuarios_suspender", args=[otro_admin.id]))

    assert response.status_code == 302
    otro_admin.refresh_from_db()
    assert otro_admin.is_active is False


# --- Self-demotion guard (SECURITY-REPORT.md F-11) ------------------------


@pytest.mark.django_db
def test_editar_no_puede_quitarse_el_rol_de_administrador_a_si_mismo(
    client, administrador_factory
):
    """F-11 RED: `usuarios_suspender` already refuses to suspend the acting
    admin, because that would lock them out of every gated screen with no
    self-service way back in. Demoting yourself has the same effect and was
    never guarded. Recovering requires database or `manage.py` access
    against production."""
    admin = administrador_factory(username="autodegradador-admin")
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_editar", args=[admin.id]), {"rol": "usuario"}
    )

    assert response.status_code == 302
    admin.refresh_from_db()
    assert admin.rol == "administrador"
    assert admin.is_staff is True


@pytest.mark.django_db
def test_editar_puede_degradar_a_otro_administrador(client, administrador_factory):
    """F-11 companion: the guard is about the ACTOR only. Demoting a
    different admin stays allowed — the actor is mid-request as an active
    admin, so no single request can leave zero administrators. Mirrors
    `test_suspender_administrador_puede_suspender_a_otro_administrador`."""
    actor = administrador_factory(username="degradador-actor")
    otro = administrador_factory(username="degradador-objetivo")
    client.force_login(actor)

    response = client.post(
        reverse("usuarios_editar", args=[otro.id]), {"rol": "usuario"}
    )

    assert response.status_code == 302
    otro.refresh_from_db()
    assert otro.rol == "usuario"
    assert otro.is_staff is False


@pytest.mark.django_db
def test_editar_puede_dejar_su_propio_rol_sin_cambios(client, administrador_factory):
    """F-11 companion: the guard must reject only an actual self-demotion.
    Re-submitting the form unchanged is a legitimate no-op and must not
    start erroring."""
    admin = administrador_factory(username="autoeditor-admin")
    client.force_login(admin)

    response = client.post(
        reverse("usuarios_editar", args=[admin.id]), {"rol": "administrador"}
    )

    assert response.status_code == 302
    admin.refresh_from_db()
    assert admin.rol == "administrador"

import pytest
from django.conf import settings
from django.urls import reverse

from usuarios.models import Usuario


@pytest.fixture
def usuario_activo(db):
    return Usuario.objects.create_user(
        username="usuario_activo", password="clave-valida-123", is_active=True
    )


@pytest.mark.django_db
def test_successful_login_redirects_past_login_screen(client, usuario_activo):
    response = client.post(
        reverse("login"),
        {"username": "usuario_activo", "password": "clave-valida-123"},
    )
    assert response.status_code == 302
    assert response.url == reverse("inicio")


@pytest.mark.django_db
def test_failed_login_wrong_password_rerenders_form_no_session(client, usuario_activo):
    response = client.post(
        reverse("login"),
        {"username": "usuario_activo", "password": "clave-incorrecta"},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_rejected_for_inactive_account(client, db):
    Usuario.objects.create_user(
        username="usuario_inactivo", password="clave-valida-123", is_active=False
    )
    response = client.post(
        reverse("login"),
        {"username": "usuario_inactivo", "password": "clave-valida-123"},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_authenticated_user_hitting_login_is_redirected_not_shown_form(
    client, usuario_activo
):
    client.login(username="usuario_activo", password="clave-valida-123")

    response = client.get(reverse("login"))

    assert response.status_code == 302
    assert response.url == reverse(settings.LOGIN_REDIRECT_URL)


@pytest.mark.django_db
def test_logout_ends_session_and_redirects_protected_view_to_login(client, usuario_activo):
    client.login(username="usuario_activo", password="clave-valida-123")
    client.post(reverse("logout"))

    response = client.get(reverse("inicio"))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_inicio_renderiza_pantalla_de_bienvenida(client, usuario_activo):
    client.login(username="usuario_activo", password="clave-valida-123")

    response = client.get(reverse("inicio"))

    assert response.status_code == 200
    assert "usuarios/inicio.html" in [t.name for t in response.templates]
    assert usuario_activo.username in response.content.decode()


@pytest.mark.django_db
def test_inicio_sin_reportes_muestra_los_3_conteos_en_cero(client, usuario_activo):
    client.login(username="usuario_activo", password="clave-valida-123")

    response = client.get(reverse("inicio"))

    conteos = {c["id"]: c["cantidad"] for c in response.context["conteos"]}
    assert conteos == {"en_progreso": 0, "listo_para_generar": 0, "terminado": 0}


@pytest.mark.django_db
def test_administrador_can_access_django_admin(client, db):
    Usuario.objects.create_user(
        username="admin_rol", password="clave-valida-123", rol="administrador"
    )
    client.login(username="admin_rol", password="clave-valida-123")

    response = client.get("/admin/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_usuario_role_is_denied_django_admin(client, db):
    Usuario.objects.create_user(
        username="usuario_rol", password="clave-valida-123", rol="usuario"
    )
    client.login(username="usuario_rol", password="clave-valida-123")

    response = client.get("/admin/")
    assert response.status_code in (302, 403)
    if response.status_code == 302:
        assert reverse("login") in response.url or "/admin/login/" in response.url


def test_session_cookie_age_is_seven_days():
    assert settings.SESSION_COOKIE_AGE == 604800

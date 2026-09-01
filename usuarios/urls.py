from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from usuarios import views

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.inicio, name="inicio"),
    # Admin users screen (BACKLOG.md #1, S-13). "nuevo/" declared before
    # "<int:usuario_id>/" mirrors tipos_reporte/urls.py's ordering note.
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", views.usuarios_crear, name="usuarios_crear"),
    path(
        "usuarios/<int:usuario_id>/editar/",
        views.usuarios_editar,
        name="usuarios_editar",
    ),
    path(
        "usuarios/<int:usuario_id>/resetear-password/",
        views.usuarios_resetear_password,
        name="usuarios_resetear_password",
    ),
    path(
        "usuarios/<int:usuario_id>/suspender/",
        views.usuarios_suspender,
        name="usuarios_suspender",
    ),
]

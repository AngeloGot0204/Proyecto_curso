from django.urls import path

from tipos_reporte import views

urlpatterns = [
    path("", views.lista, name="tipos_lista"),
    path("<int:tipo_id>/", views.detalle, name="tipos_detalle"),
    path(
        "<int:tipo_id>/desactivar/",
        views.desactivar_tipo_vista,
        name="tipos_desactivar",
    ),
    path(
        "definiciones/<int:definicion_id>/activar/",
        views.activar_definicion_vista,
        name="tipos_definicion_activar",
    ),
]

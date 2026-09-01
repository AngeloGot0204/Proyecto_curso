from django.urls import path

from tipos_reporte import views

urlpatterns = [
    path("", views.lista, name="tipos_lista"),
    # "nuevo/" must be declared BEFORE "<int:tipo_id>/" — the int converter
    # rejects it, so ordering alone is not what avoids the collision, but
    # this keeps the intent explicit and matches design's Interfaces note.
    path("nuevo/", views.crear_tipo, name="tipos_crear"),
    path("<int:tipo_id>/", views.detalle, name="tipos_detalle"),
    path("<int:tipo_id>/editar/", views.editar_tipo, name="tipos_editar"),
    path(
        "<int:tipo_id>/desactivar/",
        views.desactivar_tipo_vista,
        name="tipos_desactivar",
    ),
    path(
        "<int:tipo_id>/definiciones/nueva/",
        views.crear_definicion,
        name="tipos_definicion_crear",
    ),
    path(
        "<int:tipo_id>/definiciones/<int:definicion_id>/editar/",
        views.editar_definicion,
        name="tipos_definicion_editar",
    ),
    path(
        "definiciones/<int:definicion_id>/activar/",
        views.activar_definicion_vista,
        name="tipos_definicion_activar",
    ),
]

from django.urls import path

from reportes import views

urlpatterns = [
    path("<str:codigo_tipo>/nuevo/", views.iniciar_reporte, name="reportes_nuevo"),
    path(
        "<int:reporte_id>/paso/<str:seccion_id>/",
        views.paso,
        name="reportes_paso",
    ),
    path(
        "<int:reporte_id>/revision/",
        views.revision,
        name="reportes_revision",
    ),
    path(
        "<int:reporte_id>/cerrar/",
        views.cerrar_reporte,
        name="reportes_cerrar",
    ),
    path(
        "<int:reporte_id>/generar/",
        views.generar,
        name="reportes_generar",
    ),
    path(
        "<int:reporte_id>/invitar/",
        views.invitar,
        name="reportes_invitar",
    ),
    path(
        "<int:reporte_id>/participantes/",
        views.participantes,
        name="reportes_participantes",
    ),
]

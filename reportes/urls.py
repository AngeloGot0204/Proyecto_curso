from django.urls import path

from reportes import views

urlpatterns = [
    path("mis/", views.mis_reportes, name="reportes_mis"),
    path(
        "sincronizacion/",
        views.sincronizacion,
        name="reportes_sincronizacion",
    ),
    path(
        "nuevo/",
        views.seleccion_de_tipo,
        name="reportes_seleccion_tipo",
    ),
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
    path(
        "<int:reporte_id>/eliminar/",
        views.eliminar_reporte,
        name="reportes_eliminar",
    ),
    path(
        "<int:reporte_id>/adjuntos/subir/",
        views.subir_adjunto,
        name="reportes_adjuntos_subir",
    ),
    path(
        "<int:reporte_id>/adjuntos/<int:adjunto_id>/eliminar/",
        views.eliminar_adjunto,
        name="reportes_adjuntos_eliminar",
    ),
    path(
        "<int:reporte_id>/adjuntos/",
        views.adjuntos_de_reporte,
        name="reportes_adjuntos",
    ),
]

from django.urls import path

from reportes import views

urlpatterns = [
    path("<str:codigo_tipo>/nuevo/", views.iniciar_reporte, name="reportes_nuevo"),
    path(
        "<int:reporte_id>/paso/<str:seccion_id>/",
        views.paso,
        name="reportes_paso",
    ),
]

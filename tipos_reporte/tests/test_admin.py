"""Django admin tests (Slice 4).

Covers design D8 (activation is an explicit admin action calling the
service, never a `save()` hook) and D9 (the delete guard is layered: the
model already blocks deletion of an ever-activated row, but Django calls
`has_delete_permission(request, obj=None)` — WITHOUT an object — when
deciding whether to offer the changelist's bulk `delete_selected` action,
so an object-sensitive override alone would let that bulk action slip
past a protected row; `delete_selected` must be removed from `actions`
entirely).
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from tipos_reporte.admin import DefinicionDeTipoAdmin, TipoDeReporteAdmin
from tipos_reporte.models import DefinicionDeTipo, Estado, TipoDeReporte


@pytest.fixture
def site():
    return AdminSite()


@pytest.fixture
def rf_admin_request(rf, usuario_factory):
    """A request carrying a `rol=administrador` user (project convention:
    admin access is gated by `Usuario.rol`, see `usuarios/models.py`), plus
    a message storage so the action's `messages.error`/`messages.success`
    calls (design D8) can be inspected without a full HTTP round trip."""
    request = rf.get("/admin/")
    request.user = usuario_factory(
        username="admin_test", rol="administrador", is_staff=True, is_superuser=True
    )
    request._messages = CookieStorage(request)
    return request


# --- Design D9: bulk delete_selected is removed, not just guarded ----------


@pytest.mark.django_db
def test_delete_selected_is_not_offered_by_definicion_admin(site, rf_admin_request):
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)

    acciones = admin.get_actions(rf_admin_request)

    assert "delete_selected" not in acciones


@pytest.mark.django_db
def test_delete_selected_is_not_offered_by_tipo_admin(site, rf_admin_request):
    admin = TipoDeReporteAdmin(TipoDeReporte, site)

    acciones = admin.get_actions(rf_admin_request)

    assert "delete_selected" not in acciones


@pytest.mark.django_db
def test_has_delete_permission_false_for_ever_activated_definicion(
    site, rf_admin_request, tipo_de_reporte_factory
):
    """The object-level guard is still worth keeping for the detail page's
    delete button/link (design D9's admin layer), even though it alone
    cannot protect the changelist bulk action."""
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)
    tipo = tipo_de_reporte_factory()
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura={"secciones": []},
        estado=Estado.HISTORICA,
        version=1,
        activada_en=timezone.now(),
    )

    assert admin.has_delete_permission(rf_admin_request, definicion) is False


@pytest.mark.django_db
def test_has_delete_permission_true_for_never_activated_definicion(
    site, rf_admin_request, tipo_de_reporte_factory
):
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)
    tipo = tipo_de_reporte_factory()
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura={"secciones": []},
        estado=Estado.BORRADOR,
    )

    assert admin.has_delete_permission(rf_admin_request, definicion) is True


# --- Readonly / derived fields -----------------------------------------------


@pytest.mark.django_db
def test_estado_version_activada_en_are_readonly_on_definicion_admin(site):
    """`estado`, `version` and `activada_en` change only through
    `servicios.activar_definicion`/`desactivar_tipo`, never through direct
    admin editing (design D8)."""
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)

    campos_de_solo_lectura = admin.get_readonly_fields(None)

    assert "estado" in campos_de_solo_lectura
    assert "version" in campos_de_solo_lectura
    assert "activada_en" in campos_de_solo_lectura


@pytest.mark.django_db
def test_definicion_activa_is_readonly_on_tipo_admin(site):
    """`definicion_activa` changes only through the activation service, not
    by hand-picking a row in the admin (design D1, D8)."""
    admin = TipoDeReporteAdmin(TipoDeReporte, site)

    campos_de_solo_lectura = admin.get_readonly_fields(None)

    assert "definicion_activa" in campos_de_solo_lectura


# --- The "Activar definición" action wires the service ----------------------


@pytest.mark.django_db
def test_activar_action_is_registered(site):
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)

    assert "activar" in admin.actions


@pytest.mark.django_db
def test_activar_action_reports_one_error_message_per_problem(
    site, rf_admin_request, tipo_de_reporte_factory, definicion_valida
):
    """Design D8: the action reports ONE `messages.ERROR` per problem, each
    rendered as `{ubicacion}: {mensaje}` — a definition with several
    defects produces several separately readable lines."""
    tipo = tipo_de_reporte_factory()
    estructura = definicion_valida()
    del estructura["secciones"][0]["campos"][0]["tipo"]
    del estructura["secciones"][0]["campos"][0]["celda"]
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura=estructura,
        estado=Estado.BORRADOR,
    )
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)

    admin.activar(rf_admin_request, DefinicionDeTipo.objects.filter(pk=definicion.pk))

    mensajes = list(rf_admin_request._messages)
    assert len(mensajes) >= 2
    definicion.refresh_from_db()
    assert definicion.estado == Estado.BORRADOR


@pytest.mark.django_db
def test_activar_action_success_reports_one_success_message(
    site, rf_admin_request, tipo_de_reporte_factory, plantilla_xlsx, definicion_valida
):
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))
    with open(destino, "rb") as archivo:
        contenido = archivo.read()
    tipo = tipo_de_reporte_factory(plantilla=SimpleUploadedFile("p.xlsx", contenido))
    definicion = DefinicionDeTipo.objects.create(
        tipo=tipo,
        archivo_yaml=SimpleUploadedFile("d.yaml", b"secciones: []"),
        yaml_fuente="secciones: []",
        estructura=definicion_valida(),
        estado=Estado.BORRADOR,
    )
    admin = DefinicionDeTipoAdmin(DefinicionDeTipo, site)

    admin.activar(rf_admin_request, DefinicionDeTipo.objects.filter(pk=definicion.pk))

    definicion.refresh_from_db()
    assert definicion.estado == Estado.ACTIVA
    assert definicion.version == 1

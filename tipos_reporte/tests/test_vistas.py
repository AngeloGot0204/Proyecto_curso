"""View integration tests for the tipos-de-reporte administration screen
(backlog #13, S-14, PR 1 of a stacked-to-main chain; spec
`administracion-tipos-reporte`; design D1, D3, D6). Focused command:
`pytest tipos_reporte/tests/test_vistas.py -q`.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
import pytest

from tipos_reporte.models import DefinicionDeTipo, Estado, TipoDeReporte
from usuarios.models import Rol


def _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx, **kwargs):
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))
    with open(destino, "rb") as archivo:
        contenido = archivo.read()
    defaults = {"plantilla": SimpleUploadedFile("plantilla.xlsx", contenido)}
    defaults.update(kwargs)
    return tipo_de_reporte_factory(**defaults)


# ---------------------------------------------------------------------------
# tipos_lista
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lista_anonimo_redirige_login(client, tipo_de_reporte_factory):
    """Spec 'Anonymous user is redirected to login'."""
    tipo_de_reporte_factory()

    response = client.get(reverse("tipos_lista"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_lista_no_administrador_403_sin_datos(
    client, usuario_factory, tipo_de_reporte_factory
):
    """Spec 'Non-administrator is blocked with 403': 403, no tipo `codigo`
    leaked in the body."""
    no_admin = usuario_factory(username="lista-no-admin", rol=Rol.USUARIO)
    tipo = tipo_de_reporte_factory(nombre="Secreto", codigo="lista-403-secreto")
    client.force_login(no_admin)

    response = client.get(reverse("tipos_lista"))

    assert response.status_code == 403
    assert tipo.codigo not in response.content.decode()


@pytest.mark.django_db
def test_lista_pagina_1_tiene_20_y_pagina_2_tiene_1(
    client, administrador_factory, tipo_de_reporte_factory
):
    admin = administrador_factory(username="lista-paginacion-admin")
    for i in range(21):
        tipo_de_reporte_factory(
            nombre=f"Paginación {i:02d}", codigo=f"paginacion-lista-{i:02d}"
        )
    client.force_login(admin)

    respuesta_pagina_1 = client.get(reverse("tipos_lista"))
    respuesta_pagina_2 = client.get(reverse("tipos_lista"), {"page": 2})

    assert respuesta_pagina_1.status_code == 200
    assert len(respuesta_pagina_1.context["page_obj"]) == 20
    assert respuesta_pagina_2.status_code == 200
    assert len(respuesta_pagina_2.context["page_obj"]) == 1


@pytest.mark.django_db
def test_lista_page_param_invalido_no_falla(
    client, administrador_factory, tipo_de_reporte_factory
):
    admin = administrador_factory(username="lista-page-invalido-admin")
    tipo_de_reporte_factory(nombre="Único", codigo="page-invalido-unico")
    client.force_login(admin)

    respuesta_abc = client.get(reverse("tipos_lista"), {"page": "abc"})
    respuesta_999 = client.get(reverse("tipos_lista"), {"page": "999"})

    assert respuesta_abc.status_code == 200
    assert respuesta_999.status_code == 200


@pytest.mark.django_db
def test_lista_busqueda_por_q(client, administrador_factory, tipo_de_reporte_factory):
    admin = administrador_factory(username="lista-busqueda-admin")
    coincide = tipo_de_reporte_factory(nombre="Auditoría", codigo="lista-busqueda-auditoria")
    tipo_de_reporte_factory(nombre="Inspección", codigo="lista-busqueda-inspeccion")
    client.force_login(admin)

    response = client.get(reverse("tipos_lista"), {"q": "auditoria"})
    tipos_en_pagina = list(response.context["page_obj"])

    assert response.status_code == 200
    assert tipos_en_pagina == [coincide]


# ---------------------------------------------------------------------------
# tipos_detalle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_detalle_muestra_definicion_activa_e_historicas(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    """Spec 'Detail View': shows tipo fields plus both active and
    historical definiciones."""
    admin = administrador_factory(username="detalle-admin")
    tipo = tipo_de_reporte_factory(nombre="Con historial", codigo="detalle-con-historial")
    historica = definicion_factory(
        tipo=tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )
    activa = definicion_factory(
        tipo=tipo, estado=Estado.ACTIVA, version=2, activada_en=timezone.now()
    )
    TipoDeReporte.objects.filter(pk=tipo.pk).update(definicion_activa=activa)
    client.force_login(admin)

    response = client.get(reverse("tipos_detalle", args=[tipo.id]))
    contenido = response.content.decode()

    assert response.status_code == 200
    assert tipo.nombre in contenido
    definiciones_en_contexto = list(response.context["tipo"].definiciones.all())
    assert historica in definiciones_en_contexto
    assert activa in definiciones_en_contexto


@pytest.mark.django_db
def test_detalle_no_administrador_403(
    client, usuario_factory, tipo_de_reporte_factory
):
    no_admin = usuario_factory(username="detalle-no-admin", rol=Rol.USUARIO)
    tipo = tipo_de_reporte_factory(nombre="Detalle 403", codigo="detalle-403")
    client.force_login(no_admin)

    response = client.get(reverse("tipos_detalle", args=[tipo.id]))

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# tipos_definicion_activar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_activar_definicion_exito_mensaje_success_y_estado_activa(
    client,
    administrador_factory,
    tipo_de_reporte_factory,
    plantilla_xlsx,
    definicion_valida,
    definicion_factory,
):
    """Spec 'Activation succeeds through the new screen'."""
    admin = administrador_factory(username="activar-exito-admin")
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    definicion = definicion_factory(tipo=tipo, estructura=definicion_valida())
    client.force_login(admin)

    response = client.post(
        reverse("tipos_definicion_activar", args=[definicion.id]), follow=True
    )

    definicion.refresh_from_db()
    assert response.status_code == 200
    assert definicion.estado == Estado.ACTIVA
    mensajes = list(response.context["messages"])
    assert len(mensajes) == 1
    assert mensajes[0].tags == "success"


@pytest.mark.django_db
def test_activar_definicion_falla_muestra_todos_los_problemas_y_permanece_borrador(
    client,
    administrador_factory,
    tipo_de_reporte_factory,
    plantilla_xlsx,
    definicion_valida,
    definicion_factory,
):
    """Spec 'Activation failure surfaces every problem': no partial state
    change, and every accumulated problem is surfaced as a message."""
    admin = administrador_factory(username="activar-falla-admin")
    tipo = _tipo_con_plantilla(tipo_de_reporte_factory, plantilla_xlsx)
    estructura = definicion_valida()
    del estructura["secciones"][0]["campos"][0]["tipo"]
    del estructura["hoja"]
    definicion = definicion_factory(tipo=tipo, estructura=estructura)
    client.force_login(admin)

    response = client.post(
        reverse("tipos_definicion_activar", args=[definicion.id]), follow=True
    )

    definicion.refresh_from_db()
    mensajes = [str(m) for m in response.context["messages"]]
    assert response.status_code == 200
    assert definicion.estado == Estado.BORRADOR
    assert len(mensajes) >= 2


@pytest.mark.django_db
def test_activar_definicion_get_405(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    """Design D6: `@require_POST`."""
    admin = administrador_factory(username="activar-get-405-admin")
    tipo = tipo_de_reporte_factory(nombre="Activar GET", codigo="activar-get-405")
    definicion = definicion_factory(tipo=tipo)
    client.force_login(admin)

    response = client.get(reverse("tipos_definicion_activar", args=[definicion.id]))

    assert response.status_code == 405


# ---------------------------------------------------------------------------
# tipos_desactivar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_desactivar_tipo_exito_limpia_definicion_activa_y_version_sin_cambios(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    """Spec 'Desactivation succeeds through the new screen'."""
    admin = administrador_factory(username="desactivar-exito-admin")
    tipo = tipo_de_reporte_factory(nombre="Desactivar", codigo="desactivar-exito")
    activa = definicion_factory(
        tipo=tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )
    TipoDeReporte.objects.filter(pk=tipo.pk).update(definicion_activa=activa)
    tipo.refresh_from_db()
    client.force_login(admin)

    response = client.post(
        reverse("tipos_desactivar", args=[tipo.id]), follow=True
    )

    tipo.refresh_from_db()
    activa.refresh_from_db()
    assert response.status_code == 200
    assert tipo.definicion_activa_id is None
    assert activa.estado == Estado.HISTORICA
    assert activa.version == 1


@pytest.mark.django_db
def test_desactivar_get_405(client, administrador_factory, tipo_de_reporte_factory):
    admin = administrador_factory(username="desactivar-get-405-admin")
    tipo = tipo_de_reporte_factory(nombre="Desactivar GET", codigo="desactivar-get-405")
    client.force_login(admin)

    response = client.get(reverse("tipos_desactivar", args=[tipo.id]))

    assert response.status_code == 405

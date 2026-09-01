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


@pytest.mark.django_db
def test_lista_aplica_grid_de_escritorio_sidebar_316px(
    client, administrador_factory, tipo_de_reporte_factory
):
    """Change `retrofit-visual-design2` PR1b (design D5, DESIGN2 §3
    'Escritorio S-14'): the desktop admin shell wraps the screen in the
    `.escritorio` grid (sidebar 232px, token `--sidebar`) with its inner
    `.escritorio__contenido` grid (`316px minmax(0,1fr)`, 28px gap)."""
    admin = administrador_factory(username="lista-grid-escritorio-admin")
    tipo_de_reporte_factory(nombre="Grid", codigo="lista-grid-escritorio")
    client.force_login(admin)

    response = client.get(reverse("tipos_lista"))
    contenido = response.content.decode()

    assert 'class="escritorio"' in contenido
    assert "escritorio__sidebar" in contenido
    assert "escritorio__contenido" in contenido


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


@pytest.mark.django_db
def test_detalle_aplica_tabla_component_class(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    """Change `retrofit-visual-design2` PR1b (design D3/D5): the read-only
    definiciones listing on the S-14 detail screen uses the new `.tabla`
    component class."""
    admin = administrador_factory(username="detalle-tabla-admin")
    tipo = tipo_de_reporte_factory(nombre="Con tabla", codigo="detalle-tabla-class")
    definicion_factory(tipo=tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now())
    client.force_login(admin)

    response = client.get(reverse("tipos_detalle", args=[tipo.id]))
    contenido = response.content.decode()

    assert 'class="tabla"' in contenido


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


# ---------------------------------------------------------------------------
# tipos_crear (PR2, design D4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_crear_tipo_administrador_exito_sin_definicion_activa(
    client, administrador_factory
):
    """Spec 'Administrator creates a new TipoDeReporte'."""
    admin = administrador_factory(username="crear-tipo-exito-admin")
    client.force_login(admin)

    response = client.post(
        reverse("tipos_crear"),
        data={
            "nombre": "Nuevo tipo",
            "codigo": "crear-tipo-exito-codigo",
            "version_formato": "",
            "plantilla": SimpleUploadedFile("p.xlsx", b"contenido-irrelevante"),
        },
        follow=True,
    )

    assert response.status_code == 200
    tipo = TipoDeReporte.objects.get(codigo="crear-tipo-exito-codigo")
    assert tipo.definicion_activa_id is None


@pytest.mark.django_db
def test_crear_tipo_no_administrador_403(client, usuario_factory):
    no_admin = usuario_factory(username="crear-tipo-no-admin", rol=Rol.USUARIO)
    client.force_login(no_admin)

    response = client.get(reverse("tipos_crear"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_formulario_tipo_aplica_campo_component_class(
    client, administrador_factory
):
    """Change `retrofit-visual-design2` PR1b (design D3/D5): `formulario_tipo.html`
    wraps `{{ form.as_p }}` in `.form-basica` (same pattern `login.html`
    shipped in PR1a) so the `.campo`/`.form-basica` descendant selectors
    already in `components.css` style every native widget without touching
    `tipos_reporte/forms.py`."""
    admin = administrador_factory(username="formulario-tipo-campo-admin")
    client.force_login(admin)

    response = client.get(reverse("tipos_crear"))
    contenido = response.content.decode()

    assert 'class="form-basica"' in contenido


# ---------------------------------------------------------------------------
# tipos_editar (PR2, design D4, D8)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_editar_tipo_sin_reupload_logo_mantiene_logo_existente(
    client, administrador_factory, tipo_de_reporte_factory
):
    """Spec headline scenario 'Editing without re-uploading keeps the
    existing logo'."""
    from PIL import Image
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    admin = administrador_factory(username="editar-logo-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Con logo",
        codigo="editar-logo-mantiene",
        logo=SimpleUploadedFile("logo.png", buffer.read(), content_type="image/png"),
    )
    logo_original = tipo.logo.name
    client.force_login(admin)

    response = client.post(
        reverse("tipos_editar", args=[tipo.id]),
        data={
            "nombre": tipo.nombre,
            "codigo": tipo.codigo,
            "version_formato": tipo.version_formato,
            "plantilla": SimpleUploadedFile("p2.xlsx", b"contenido-irrelevante"),
        },
        follow=True,
    )

    tipo.refresh_from_db()
    assert response.status_code == 200
    assert tipo.logo.name == logo_original


@pytest.mark.django_db
def test_editar_tipo_plantilla_solo_lectura_cuando_definicion_activa_no_persiste_cambio(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    admin = administrador_factory(username="editar-plantilla-readonly-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Con activa", codigo="editar-plantilla-readonly"
    )
    activa = definicion_factory(
        tipo=tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )
    TipoDeReporte.objects.filter(pk=tipo.pk).update(definicion_activa=activa)
    tipo.refresh_from_db()
    plantilla_original = tipo.plantilla.name
    client.force_login(admin)

    response = client.post(
        reverse("tipos_editar", args=[tipo.id]),
        data={
            "nombre": tipo.nombre,
            "codigo": tipo.codigo,
            "version_formato": tipo.version_formato,
            "plantilla": SimpleUploadedFile("nueva.xlsx", b"contenido-nuevo"),
        },
        follow=True,
    )

    tipo.refresh_from_db()
    assert response.status_code == 200
    assert tipo.plantilla.name == plantilla_original


# ---------------------------------------------------------------------------
# tipos_definicion_crear / tipos_definicion_editar (PR2, design D5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_crear_definicion_yaml_valido_crea_borrador_bajo_tipo_de_url(
    client, administrador_factory, tipo_de_reporte_factory
):
    admin = administrador_factory(username="crear-definicion-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Para definiciones", codigo="crear-definicion-tipo"
    )
    client.force_login(admin)

    response = client.post(
        reverse("tipos_definicion_crear", args=[tipo.id]),
        data={
            "archivo_yaml": SimpleUploadedFile(
                "d.yaml", b"secciones: []", content_type="application/x-yaml"
            )
        },
        follow=True,
    )

    assert response.status_code == 200
    definicion = DefinicionDeTipo.objects.get(tipo=tipo)
    assert definicion.estado == Estado.BORRADOR
    assert definicion.estructura == {"secciones": []}


@pytest.mark.django_db
def test_editar_definicion_borrador_permite_edicion(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    admin = administrador_factory(username="editar-definicion-borrador-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Editar borrador", codigo="editar-definicion-borrador"
    )
    definicion = definicion_factory(tipo=tipo)
    client.force_login(admin)

    response = client.get(
        reverse("tipos_definicion_editar", args=[tipo.id, definicion.id])
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_editar_definicion_no_borrador_404(
    client, administrador_factory, tipo_de_reporte_factory, definicion_factory
):
    """Design D5: edit is restricted to `borrador` rows — `models.py`'s
    `CONGELADOS` guard makes non-borrador rows immutable."""
    admin = administrador_factory(username="editar-definicion-404-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Editar no borrador", codigo="editar-definicion-no-borrador"
    )
    definicion = definicion_factory(
        tipo=tipo, estado=Estado.HISTORICA, version=1, activada_en=timezone.now()
    )
    client.force_login(admin)

    response = client.get(
        reverse("tipos_definicion_editar", args=[tipo.id, definicion.id])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_formulario_definicion_aplica_campo_component_class(
    client, administrador_factory, tipo_de_reporte_factory
):
    """Change `retrofit-visual-design2` PR1b (design D3/D5): `formulario_definicion.html`
    wraps `{{ form.as_p }}` in `.form-basica`, same pattern as
    `formulario_tipo.html`."""
    admin = administrador_factory(username="formulario-definicion-campo-admin")
    tipo = tipo_de_reporte_factory(
        nombre="Formulario definicion", codigo="formulario-definicion-campo"
    )
    client.force_login(admin)

    response = client.get(reverse("tipos_definicion_crear", args=[tipo.id]))
    contenido = response.content.decode()

    assert 'class="form-basica"' in contenido


@pytest.mark.django_db
def test_crear_o_editar_plantilla_oversize_es_aceptada(
    client, administrador_factory
):
    """Design D8, spec 'Oversized plantilla is accepted': a `plantilla`
    file larger than `Adjunto`'s size ceiling must not be rejected for
    size."""
    from reportes.adjuntos import TAMANO_MAXIMO_BYTES

    admin = administrador_factory(username="crear-tipo-oversize-admin")
    client.force_login(admin)
    contenido_grande = b"0" * (TAMANO_MAXIMO_BYTES + 1)

    response = client.post(
        reverse("tipos_crear"),
        data={
            "nombre": "Oversize",
            "codigo": "crear-tipo-oversize-codigo",
            "version_formato": "",
            "plantilla": SimpleUploadedFile("grande.xlsx", contenido_grande),
        },
        follow=True,
    )

    assert response.status_code == 200
    assert TipoDeReporte.objects.filter(codigo="crear-tipo-oversize-codigo").exists()


# ---------------------------------------------------------------------------
# Admin deregistration (PR2, design D7)
# ---------------------------------------------------------------------------


def test_admin_registry_no_contiene_tipo_de_reporte_ni_definicion_de_tipo():
    """8.2 RED: `TipoDeReporte`/`DefinicionDeTipo` absent from
    `admin.site._registry` (spec "Admin registration removed once new
    create/edit screen exists")."""
    from django.contrib import admin as django_admin

    assert TipoDeReporte not in django_admin.site._registry
    assert DefinicionDeTipo not in django_admin.site._registry

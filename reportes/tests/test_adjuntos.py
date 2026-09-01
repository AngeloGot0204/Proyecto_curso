"""Tests for the `adjuntos-reporte` capability (backlog #11).

PR 1 scope (tasks.md Phase 1, D1): standalone `Adjunto` model + migration.
PR 2 scope (tasks.md Phase 2 + Phase 3, D7 + D2): the pure
`reportes.adjuntos.validar_adjunto` module and the upload/list endpoints.
Client-pipeline/Excel-embedding tests are out of scope here and land in
later PRs (Phase 4+).
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from reportes.adjuntos import (
    SECCION_DE_ADJUNTOS,
    TAMANO_MAXIMO_BYTES,
    validar_adjunto,
)
from reportes.models import Adjunto, CategoriaDeAdjunto, ValorDeReporte


# --- Requirement: Standalone Adjunto Model ----------------------------------


@pytest.mark.django_db
@pytest.mark.modelo
def test_adjunto_se_guarda_independiente_de_valorreporte(
    reporte_factory, usuario_factory, seccion_s08_id
):
    """Spec scenario "Attachment is stored independent of ValorDeReporte":
    saving an S-08 attachment persists an `Adjunto` row, not a
    `ValorDeReporte` row."""
    usuario = usuario_factory()
    reporte = reporte_factory(creador=usuario)
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="turno",
        valor="Día",
        autor=usuario,
    )

    adjunto = Adjunto.objects.create(
        reporte=reporte,
        seccion_id=seccion_s08_id,
        categoria=CategoriaDeAdjunto.EVIDENCIA,
        archivo=SimpleUploadedFile(
            "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
        ),
        nombre_original="foto.jpg",
        formato_original="image/jpeg",
        tamano_bytes=21,
        autor=usuario,
    )

    assert Adjunto.objects.count() == 1
    assert ValorDeReporte.objects.filter(reporte=reporte).count() == 1
    assert adjunto.reporte_id == reporte.id
    assert adjunto.seccion_id == seccion_s08_id
    assert adjunto.categoria == CategoriaDeAdjunto.EVIDENCIA
    assert adjunto.nombre_original == "foto.jpg"
    assert adjunto.formato_original == "image/jpeg"
    assert adjunto.tamano_bytes == 21
    assert adjunto.autor_id == usuario.id
    assert adjunto.fecha_subida is not None


# --- Requirement: Format Allowlist / Server-Side Size Ceiling (D7) ---------


@pytest.fixture
def sesion_de_creador(client, usuario_factory, reporte_factory):
    """A `(client, reporte)` pair where the logged-in user IS the `Reporte`'s
    `creador` (app-local duplicate of `test_views.py`'s fixture of the same
    name — established project convention, design's Testing Strategy)."""
    creador = usuario_factory(username="creador_del_reporte_adjuntos")
    reporte = reporte_factory(creador=creador)
    client.force_login(creador)
    return client, reporte


@pytest.mark.parametrize(
    "content_type",
    ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"],
)
def test_valida_formato_permitido(content_type):
    """Spec "Format Allowlist" — every allowed content-type passes
    `validar_adjunto` with no DB access involved."""
    archivo = SimpleUploadedFile(
        "foto", b"contenido-irrelevante", content_type=content_type
    )
    assert validar_adjunto(archivo) is None


@pytest.mark.parametrize("content_type", ["image/gif", "application/pdf"])
def test_rechaza_formato_no_permitido(content_type):
    """Spec "Format Allowlist" — a disallowed content-type is rejected with
    the stable `formato-no-permitido` error id."""
    archivo = SimpleUploadedFile(
        "archivo", b"contenido-irrelevante", content_type=content_type
    )
    assert validar_adjunto(archivo) == "formato-no-permitido"


def test_acepta_tamano_limite_8mb():
    """Spec "Server-Side Size Ceiling" boundary — exactly 8MB is accepted
    (design D7's `TAMANO_MAXIMO_BYTES` boundary)."""
    archivo = SimpleUploadedFile(
        "foto.jpg", b"a" * TAMANO_MAXIMO_BYTES, content_type="image/jpeg"
    )
    assert validar_adjunto(archivo) is None


def test_rechaza_tamano_excedido_8mb_mas_1():
    """Spec "Server-Side Size Ceiling" boundary — 8MB + 1 byte is rejected
    with the stable `tamano-excedido` error id."""
    archivo = SimpleUploadedFile(
        "foto.jpg", b"a" * (TAMANO_MAXIMO_BYTES + 1), content_type="image/jpeg"
    )
    assert validar_adjunto(archivo) == "tamano-excedido"


# --- Requirement: Upload endpoint (D2) --------------------------------------


@pytest.mark.django_db
def test_subir_adjunto_happy_path_crea_adjunto(sesion_de_creador, seccion_s08_id):
    """Design's Interfaces/Contracts: happy path returns 201 with
    `id`/`nombre`/`url`/`tamano_bytes`, creates exactly one `Adjunto` row and
    zero `ValorDeReporte` rows."""
    client, reporte = sesion_de_creador
    archivo = SimpleUploadedFile(
        "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
    )

    response = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": seccion_s08_id,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo,
        },
    )

    assert response.status_code == 201
    cuerpo = response.json()
    assert set(cuerpo) == {"id", "nombre", "url", "tamano_bytes"}
    assert cuerpo["nombre"] == "foto.jpg"
    assert cuerpo["tamano_bytes"] == len(b"contenido-irrelevante")
    assert Adjunto.objects.count() == 1
    assert ValorDeReporte.objects.filter(reporte=reporte).count() == 0


@pytest.mark.django_db
def test_subir_adjunto_formato_no_permitido_devuelve_400_sin_crear_fila(
    sesion_de_creador, seccion_s08_id
):
    """Spec "Format Allowlist" — a disallowed content-type is rejected
    BEFORE any `Adjunto.objects.create` (design D7's "creates no row, writes
    no blob")."""
    client, reporte = sesion_de_creador
    archivo = SimpleUploadedFile(
        "archivo.gif", b"contenido-irrelevante", content_type="image/gif"
    )

    response = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": seccion_s08_id,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "formato-no-permitido"}
    assert Adjunto.objects.count() == 0


@pytest.mark.django_db
def test_subir_adjunto_tamano_excedido_devuelve_400_sin_crear_fila(
    sesion_de_creador, seccion_s08_id
):
    """Spec "Server-Side Size Ceiling" — an oversized file is rejected
    server-side, independent of any client-side compression outcome, and no
    `Adjunto` row is created."""
    client, reporte = sesion_de_creador
    archivo = SimpleUploadedFile(
        "foto.jpg",
        b"a" * (TAMANO_MAXIMO_BYTES + 1),
        content_type="image/jpeg",
    )

    response = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": seccion_s08_id,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "tamano-excedido"}
    assert Adjunto.objects.count() == 0


@pytest.mark.django_db
def test_subir_adjunto_seccion_no_admite_adjuntos_400(sesion_de_creador):
    """`seccion_id` is never trusted from the client (threat matrix
    "Routing") — a `seccion_id` other than `SECCION_DE_ADJUNTOS` is rejected
    with a 400, even with an otherwise-valid file."""
    client, reporte = sesion_de_creador
    archivo = SimpleUploadedFile(
        "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
    )

    response = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": "otra-seccion-cualquiera",
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "seccion-no-admite-adjuntos"}
    assert Adjunto.objects.count() == 0


@pytest.mark.django_db
def test_subir_adjunto_no_participante_devuelve_404(
    client, usuario_factory, reporte_factory, seccion_s08_id
):
    """Threat matrix "Routing" — a non-creator/non-invited user gets a 404,
    same as `paso`/`revision`/`generar` (`_reporte_accesible`, no existence
    leak)."""
    creador = usuario_factory(username="creador_ajeno_adjuntos")
    reporte = reporte_factory(creador=creador)
    ajeno = usuario_factory(username="usuario_sin_acceso_adjuntos")
    client.force_login(ajeno)
    archivo = SimpleUploadedFile(
        "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
    )

    response = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": seccion_s08_id,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo,
        },
    )

    assert response.status_code == 404
    assert Adjunto.objects.count() == 0


@pytest.mark.django_db
def test_multiples_adjuntos_sin_limite_de_cantidad(sesion_de_creador, seccion_s08_id):
    """Spec "No Hard Cap on Attachment Count" — N valid attachments are all
    accepted, with no count-based rejection."""
    client, reporte = sesion_de_creador

    for i in range(5):
        archivo = SimpleUploadedFile(
            f"foto-{i}.jpg", b"contenido-irrelevante", content_type="image/jpeg"
        )
        response = client.post(
            reverse("reportes_adjuntos_subir", args=[reporte.id]),
            data={
                "seccion_id": seccion_s08_id,
                "categoria": CategoriaDeAdjunto.EVIDENCIA,
                "archivo": archivo,
            },
        )
        assert response.status_code == 201

    assert Adjunto.objects.filter(reporte=reporte).count() == 5


@pytest.mark.django_db
def test_aislamiento_un_adjunto_invalido_no_bloquea_paso(
    sesion_de_creador, seccion_s08_id
):
    """Spec "Per-Attachment Failure Isolation" — the step's field values are
    persisted and the step succeeds (302) independent of a separately-posted
    oversized attachment being rejected (design D2's whole rationale: a
    dedicated endpoint means the step's Post/Redirect/Get outcome is never
    touched by an attachment's own outcome)."""
    client, reporte = sesion_de_creador
    estructura = reporte.definicion.estructura
    primera_seccion_id = estructura["secciones"][0]["id"]

    respuesta_paso = client.post(
        reverse("reportes_paso", args=[reporte.id, primera_seccion_id]),
        data={"turno": "Día"},
    )
    assert respuesta_paso.status_code == 302
    assert ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="turno", valor="Día"
    ).exists()

    archivo_sobredimensionado = SimpleUploadedFile(
        "foto.jpg",
        b"a" * (TAMANO_MAXIMO_BYTES + 1),
        content_type="image/jpeg",
    )
    respuesta_adjunto = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        data={
            "seccion_id": seccion_s08_id,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
            "archivo": archivo_sobredimensionado,
        },
    )

    assert respuesta_adjunto.status_code == 400
    assert respuesta_adjunto.json() == {"error": "tamano-excedido"}
    assert Adjunto.objects.count() == 0
    # The step's field values remain untouched by the attachment rejection.
    assert ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="turno", valor="Día"
    ).exists()


# --- Requirement: Server-Side Listing and Download --------------------------


@pytest.mark.django_db
def test_lista_adjuntos_autorizado_incluye_metadata_y_enlace(
    sesion_de_creador, seccion_s08_id
):
    """Spec "Server-Side Listing and Download" — the response includes each
    attachment's `nombre_original`, `categoria`, `fecha_subida`, `autor`,
    `tamano_bytes`, and a download link."""
    client, reporte = sesion_de_creador
    creador = reporte.creador
    adjunto = Adjunto.objects.create(
        reporte=reporte,
        seccion_id=seccion_s08_id,
        categoria=CategoriaDeAdjunto.CROQUIS,
        archivo=SimpleUploadedFile(
            "croquis.png", b"contenido-irrelevante", content_type="image/png"
        ),
        nombre_original="croquis.png",
        formato_original="image/png",
        tamano_bytes=21,
        autor=creador,
    )

    response = client.get(reverse("reportes_adjuntos", args=[reporte.id]))

    assert response.status_code == 200
    contenido = response.content.decode()
    assert adjunto.nombre_original in contenido
    assert adjunto.get_categoria_display() in contenido
    assert creador.username in contenido
    assert str(adjunto.tamano_bytes) in contenido
    assert adjunto.archivo.url in contenido


@pytest.mark.django_db
def test_adjuntos_aplica_grid_de_adjuntos_component_class(
    sesion_de_creador, seccion_s08_id
):
    """Change `retrofit-visual-design2` PR2 (design D3/§6.b, task 3.11): the
    read-only attachment listing uses the `.adjuntos` grid component
    (DESIGN2 §6.b "Adjuntos (S-08)" — 2-column grid of thumbnail + name/
    peso/local, applied here to already-uploaded rows; spec `visual-design-
    system`, requirement 'Eight DESIGN2 Component Classes')."""
    client, reporte = sesion_de_creador
    Adjunto.objects.create(
        reporte=reporte,
        seccion_id=seccion_s08_id,
        categoria=CategoriaDeAdjunto.EVIDENCIA,
        archivo=SimpleUploadedFile(
            "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
        ),
        nombre_original="foto.jpg",
        formato_original="image/jpeg",
        tamano_bytes=21,
        autor=reporte.creador,
    )

    response = client.get(reverse("reportes_adjuntos", args=[reporte.id]))
    contenido = response.content.decode()

    assert response.status_code == 200
    assert 'class="adjuntos' in contenido
    assert 'class="adjuntos__item' in contenido


# --- eliminar_adjunto --------------------------------------------------------


def _crear_adjunto(reporte, seccion_id, autor):
    return Adjunto.objects.create(
        reporte=reporte,
        seccion_id=seccion_id,
        categoria=CategoriaDeAdjunto.EVIDENCIA,
        archivo=SimpleUploadedFile(
            "foto.jpg", b"contenido-irrelevante", content_type="image/jpeg"
        ),
        nombre_original="foto.jpg",
        formato_original="image/jpeg",
        tamano_bytes=21,
        autor=autor,
    )


@pytest.mark.django_db
def test_eliminar_adjunto_creador_borra_adjunto_de_otro_autor(
    sesion_de_creador, seccion_s08_id, participacion_factory
):
    """The creator can delete an attachment ANY participant uploaded, not
    only their own."""
    client, reporte = sesion_de_creador
    invitado = participacion_factory(reporte, username="invitado-sube-foto")
    adjunto = _crear_adjunto(reporte, seccion_s08_id, invitado)

    response = client.post(
        reverse("reportes_adjuntos_eliminar", args=[reporte.id, adjunto.id])
    )

    assert response.status_code == 302
    assert not Adjunto.objects.filter(pk=adjunto.id).exists()


@pytest.mark.django_db
def test_eliminar_adjunto_autor_borra_su_propio_adjunto(
    sesion_de_creador, seccion_s08_id, participacion_factory
):
    """A non-creator participant CAN delete their OWN upload."""
    client, reporte = sesion_de_creador
    invitado = participacion_factory(reporte, username="invitado-borra-lo-suyo")
    adjunto = _crear_adjunto(reporte, seccion_s08_id, invitado)
    client.logout()
    client.force_login(invitado)

    response = client.post(
        reverse("reportes_adjuntos_eliminar", args=[reporte.id, adjunto.id])
    )

    assert response.status_code == 302
    assert not Adjunto.objects.filter(pk=adjunto.id).exists()


@pytest.mark.django_db
def test_eliminar_adjunto_participante_no_puede_borrar_de_otro(
    sesion_de_creador, seccion_s08_id, participacion_factory
):
    """A non-creator participant CANNOT delete an attachment a DIFFERENT
    participant uploaded — mutation stays narrower than view access."""
    client, reporte = sesion_de_creador
    autor_original = participacion_factory(reporte, username="invitado-autor")
    adjunto = _crear_adjunto(reporte, seccion_s08_id, autor_original)
    otro_invitado = participacion_factory(reporte, username="invitado-sin-permiso")
    client.logout()
    client.force_login(otro_invitado)

    response = client.post(
        reverse("reportes_adjuntos_eliminar", args=[reporte.id, adjunto.id])
    )

    assert response.status_code == 404
    assert Adjunto.objects.filter(pk=adjunto.id).exists()


@pytest.mark.django_db
def test_eliminar_adjunto_sin_acceso_al_reporte_404(
    sesion_de_creador, seccion_s08_id, usuario_factory
):
    client, reporte = sesion_de_creador
    adjunto = _crear_adjunto(reporte, seccion_s08_id, reporte.creador)
    ajeno = usuario_factory(username="ajeno-a-todo")
    client.logout()
    client.force_login(ajeno)

    response = client.post(
        reverse("reportes_adjuntos_eliminar", args=[reporte.id, adjunto.id])
    )

    assert response.status_code == 404
    assert Adjunto.objects.filter(pk=adjunto.id).exists()


@pytest.mark.django_db
def test_eliminar_adjunto_get_no_permitido(sesion_de_creador, seccion_s08_id):
    client, reporte = sesion_de_creador
    adjunto = _crear_adjunto(reporte, seccion_s08_id, reporte.creador)

    response = client.get(
        reverse("reportes_adjuntos_eliminar", args=[reporte.id, adjunto.id])
    )

    assert response.status_code == 405
    assert Adjunto.objects.filter(pk=adjunto.id).exists()

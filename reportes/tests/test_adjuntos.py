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


# --- Metadata stripping on upload (SECURITY-REPORT.md F-05, option A) -----
#
# Vercel Blob serves attachments from a public, permanent URL: the listing is
# access-scoped, the file itself is not. A field photo therefore leaves the
# application carrying whatever its camera embedded -- most importantly GPS
# coordinates. Stripping metadata does not make the URL private (that is the
# separate, larger change); it removes the most sensitive payload from a file
# that is, in practice, world-readable.


def _jpeg_con_metadatos(ancho=40, alto=30):
    """A real JPEG carrying GPS coordinates, camera make and a timestamp --
    the metadata a phone actually writes."""
    from io import BytesIO

    from PIL import Image

    imagen = Image.new("RGB", (ancho, alto), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "ACME Phone"
    exif[0x0132] = "2026:08:15 07:30:00"
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2] = "S", (33.0, 27.0, 0.0)
    gps[3], gps[4] = "W", (70.0, 39.0, 0.0)
    buffer = BytesIO()
    imagen.save(buffer, "JPEG", exif=exif, quality=88)
    return buffer.getvalue()


def _exif_de(datos):
    from io import BytesIO

    from PIL import Image

    return Image.open(BytesIO(datos)).getexif()


def test_el_jpeg_de_prueba_realmente_trae_gps():
    """Guard on the fixture itself: if this ever stops carrying GPS, the
    stripping tests below would pass without proving anything."""
    exif = _exif_de(_jpeg_con_metadatos())

    assert dict(exif.get_ifd(0x8825)) != {}
    assert exif[0x010F] == "ACME Phone"


def test_limpiar_metadatos_elimina_exif_y_gps_de_un_jpeg():
    """F-05 RED: `limpiar_metadatos` returns a file whose EXIF block --
    including the GPS sub-IFD -- is gone."""
    from reportes.adjuntos import limpiar_metadatos

    original = SimpleUploadedFile(
        "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
    )

    limpio = limpiar_metadatos(original)

    exif = _exif_de(limpio.read())
    assert dict(exif) == {}
    assert dict(exif.get_ifd(0x8825)) == {}


def test_limpiar_metadatos_conserva_los_pixeles_del_jpeg():
    """F-05 RED: stripping must not degrade the photo. JPEG is re-encoded
    with `quality="keep"`, which reuses the original quantization tables, so
    the decoded pixels come back identical -- a report's evidence photo must
    not get visibly worse because of a privacy control."""
    from io import BytesIO

    from PIL import Image

    from reportes.adjuntos import limpiar_metadatos

    datos = _jpeg_con_metadatos()
    original = SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg")

    limpio = limpiar_metadatos(original)

    antes = Image.open(BytesIO(datos))
    despues = Image.open(BytesIO(limpio.read()))
    assert despues.size == antes.size
    assert despues.mode == antes.mode
    assert despues.format == "JPEG"
    assert list(despues.get_flattened_data()) == list(antes.get_flattened_data())


def test_limpiar_metadatos_conserva_el_nombre_y_el_content_type():
    """F-05 RED: the returned object must still be usable everywhere the
    original was -- `views.subir_adjunto` reads `.name`, `.content_type` and
    `.size` off it after the call."""
    from reportes.adjuntos import limpiar_metadatos

    original = SimpleUploadedFile(
        "croquis.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
    )

    limpio = limpiar_metadatos(original)

    assert limpio.name == "croquis.jpg"
    assert limpio.content_type == "image/jpeg"
    assert limpio.size > 0


def test_limpiar_metadatos_devuelve_el_original_si_no_puede_decodificar():
    """F-05 RED: a file Pillow cannot decode -- notably HEIC/HEIF, which the
    allowlist permits and this Pillow build has no codec for -- must pass
    through untouched rather than raise. Mirrors
    `generador._incrustar_adjuntos`'s "skip, never block" posture: a privacy
    control must not become a new way to fail an upload.

    This is a REAL LIMIT of option A, not an oversight: an unconverted HEIC
    keeps its GPS. Recorded in SECURITY-REPORT.md."""
    from reportes.adjuntos import limpiar_metadatos

    basura = b"ftypheic-pero-no-decodificable" * 4
    original = SimpleUploadedFile("foto.heic", basura, content_type="image/heic")

    limpio = limpiar_metadatos(original)

    assert limpio.read() == basura
    assert limpio.name == "foto.heic"


@pytest.mark.django_db
def test_subir_adjunto_guarda_la_foto_sin_gps(sesion_de_creador, seccion_s08_id):
    """F-05 RED (end to end): the stripping must actually be wired into the
    upload endpoint -- this is the property that protects the stored blob."""
    from reportes.adjuntos import SECCION_DE_ADJUNTOS as seccion

    client, reporte = sesion_de_creador

    respuesta = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        {
            "archivo": SimpleUploadedFile(
                "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
            ),
            "seccion_id": seccion,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
        },
    )

    assert respuesta.status_code == 201
    adjunto = Adjunto.objects.get()
    with adjunto.archivo.open("rb") as guardado:
        exif = _exif_de(guardado.read())
    assert dict(exif) == {}
    assert dict(exif.get_ifd(0x8825)) == {}


@pytest.mark.django_db
def test_eliminar_reporte_borra_los_blobs_de_sus_adjuntos(
    sesion_de_creador, seccion_s08_id
):
    """F-05 RED: `eliminar_reporte` is a soft delete by design -- every row
    stays for audit. The stored FILES are a different question: they live at
    a public, permanent URL, so leaving them behind means a report the
    creator deleted is still readable by anyone holding the link, forever.
    Deleting the blobs while keeping the `Adjunto` rows resolves both needs.
    """
    client, reporte = sesion_de_creador
    client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        {
            "archivo": SimpleUploadedFile(
                "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
            ),
            "seccion_id": SECCION_DE_ADJUNTOS,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
        },
    )
    adjunto = Adjunto.objects.get()
    almacenamiento = adjunto.archivo.storage
    nombre = adjunto.archivo.name
    assert almacenamiento.exists(nombre)

    respuesta = client.post(reverse("reportes_eliminar", args=[reporte.id]))

    assert respuesta.status_code == 302
    reporte.refresh_from_db()
    assert reporte.eliminado_en is not None
    # The audit row survives; only the publicly-readable bytes are gone.
    assert Adjunto.objects.filter(pk=adjunto.pk).exists()
    assert not almacenamiento.exists(nombre)


# --- Abuse ceiling on uploads (SECURITY-REPORT.md F-06) ------------------
#
# The spec forbids a MAXIMUM ATTACHMENT COUNT, and that stays true: nobody
# in the field is told "you already uploaded enough photos". What the spec
# never decided is whether unlimited-by-product also meant
# unlimited-by-abuse. It did not: every upload costs Vercel Blob storage and
# transfer, billed with no ceiling, and a single authenticated account can
# loop 8 MB requests forever.
#
# Real usage, per the product owner: about 4 photos per user per report. The
# hourly ceiling is set an order of magnitude above that, so it is invisible
# to anyone working normally and only ever trips on a loop.


@pytest.mark.django_db
def test_subidas_normales_no_tocan_el_techo(sesion_de_creador):
    """F-06 RED: the ceiling must be invisible in real use. Typical usage is
    ~4 photos per user per report, so a run of them must all succeed."""
    from reportes.adjuntos import SUBIDAS_MAXIMAS_POR_HORA

    client, reporte = sesion_de_creador
    assert SUBIDAS_MAXIMAS_POR_HORA >= 40, (
        "el techo debe quedar un orden de magnitud sobre el uso real (~4), "
        "o deja de ser un limite de abuso y pasa a ser un limite de producto"
    )

    for _ in range(6):
        respuesta = client.post(
            reverse("reportes_adjuntos_subir", args=[reporte.id]),
            {
                "archivo": SimpleUploadedFile(
                    "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
                ),
                "seccion_id": SECCION_DE_ADJUNTOS,
                "categoria": CategoriaDeAdjunto.EVIDENCIA,
            },
        )
        assert respuesta.status_code == 201

    assert Adjunto.objects.count() == 6


@pytest.mark.django_db
def test_pasado_el_techo_por_hora_la_subida_se_rechaza(
    sesion_de_creador, usuario_factory
):
    """F-06 RED: past the hourly ceiling the endpoint answers 429 and
    creates no row. `429` (not 400) so the client can tell "try later" from
    "this file is wrong" -- `adjuntos.js` shows a different message."""
    from django.utils import timezone

    from reportes.adjuntos import SUBIDAS_MAXIMAS_POR_HORA

    client, reporte = sesion_de_creador
    autor = reporte.creador
    for indice in range(SUBIDAS_MAXIMAS_POR_HORA):
        Adjunto.objects.create(
            reporte=reporte,
            seccion_id=SECCION_DE_ADJUNTOS,
            categoria=CategoriaDeAdjunto.EVIDENCIA,
            archivo=SimpleUploadedFile(f"previa{indice}.jpg", b"x"),
            nombre_original=f"previa{indice}.jpg",
            formato_original="image/jpeg",
            tamano_bytes=1,
            autor=autor,
        )
    antes = Adjunto.objects.count()

    respuesta = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        {
            "archivo": SimpleUploadedFile(
                "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
            ),
            "seccion_id": SECCION_DE_ADJUNTOS,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
        },
    )

    assert respuesta.status_code == 429
    assert respuesta.json()["error"] == "demasiadas-subidas"
    assert Adjunto.objects.count() == antes


@pytest.mark.django_db
def test_el_techo_es_por_usuario_no_por_reporte(sesion_de_creador, usuario_factory):
    """F-06 RED: the ceiling counts the ACTOR's own uploads. Another
    participant hitting their own limit must not lock out everyone else on a
    shared report -- that would turn an abuse control into a denial of
    service against the team."""
    from reportes.adjuntos import SUBIDAS_MAXIMAS_POR_HORA
    from reportes.models import ParticipacionEnReporte

    client, reporte = sesion_de_creador
    otro = usuario_factory(username="companero-de-cuadrilla")
    ParticipacionEnReporte.objects.create(reporte=reporte, usuario=otro)
    for indice in range(SUBIDAS_MAXIMAS_POR_HORA):
        Adjunto.objects.create(
            reporte=reporte,
            seccion_id=SECCION_DE_ADJUNTOS,
            categoria=CategoriaDeAdjunto.EVIDENCIA,
            archivo=SimpleUploadedFile(f"otro{indice}.jpg", b"x"),
            nombre_original=f"otro{indice}.jpg",
            formato_original="image/jpeg",
            tamano_bytes=1,
            autor=otro,
        )

    respuesta = client.post(
        reverse("reportes_adjuntos_subir", args=[reporte.id]),
        {
            "archivo": SimpleUploadedFile(
                "foto.jpg", _jpeg_con_metadatos(), content_type="image/jpeg"
            ),
            "seccion_id": SECCION_DE_ADJUNTOS,
            "categoria": CategoriaDeAdjunto.EVIDENCIA,
        },
    )

    assert respuesta.status_code == 201

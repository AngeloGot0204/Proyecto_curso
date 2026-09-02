"""Pure server-side validation for `Adjunto` uploads (backlog #11, spec
`adjuntos-reporte`, design D7). Mirrors `tipos_reporte.validacion`'s R1-R4
posture: `validar_adjunto` is a pure function over an `UploadedFile` — no
database access, no filesystem access beyond what Django's upload handling
already did — so it is unit-testable with no DB and shared verbatim by
`reportes.views.subir_adjunto` and this module's own tests.

`FORMATOS_PERMITIDOS` and `TAMANO_MAXIMO_BYTES` are enforced identically on
client (`adjuntos.js`, Phase 4) and server — the server NEVER trusts the
client-side compression/allowlist outcome (spec "Format Allowlist", "Server-
Side Size Ceiling").
"""

import logging

logger = logging.getLogger(__name__)

# content-type -> allowed extensions (informational only; the server checks
# content-type, matching the design's Interfaces/Contracts table — the
# client mirror lives in `adjuntos.js`, Phase 4).
FORMATOS_PERMITIDOS = {
    "image/jpeg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/webp": (".webp",),
    "image/heic": (".heic",),
    "image/heif": (".heif",),
}

TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024

# Abuse ceiling, NOT a product limit (SECURITY-REPORT.md F-06). The spec
# forbids a maximum attachment count and that still holds: nobody in the
# field is ever told "you already uploaded enough photos". What the spec did
# not decide is whether unlimited-by-product also meant unlimited-by-abuse.
# It did not — every upload costs Vercel Blob storage and transfer, billed
# with no ceiling, and one authenticated account can loop 8 MB requests
# indefinitely.
#
# Real usage is ~4 photos per user per report (product owner, 2026-09-01).
# 60/hour is an order of magnitude above that, so it is invisible to anyone
# working normally — even a long day re-shooting evidence — and only ever
# trips on a loop. Counted per USER, not per report: one participant hitting
# their own limit must not lock out the rest of a shared report, which would
# turn an abuse control into a denial of service against the crew.
SUBIDAS_MAXIMAS_POR_HORA = 60

# The only section that currently admits attachments (backlog #11 MVP,
# hardcoded to S-08 "croquis/evidencia"). Interim test-only resolution of
# design.md's open question — see `seccion_s08_id` in
# `reportes/tests/conftest.py` (tasks.md 1.5).
SECCION_DE_ADJUNTOS = "resultados"


# Formats this Pillow build can decode AND re-encode without losing image
# quality, mapped to the save options that make the round trip lossless.
# JPEG's `quality="keep"` reuses the original quantization tables, so the
# decoded pixels come back identical; PNG is lossless by definition; WEBP is
# forced lossless because we cannot tell from the decoded image whether the
# source was, and silently re-compressing someone's evidence photo is worse
# than a bigger file (which `TAMANO_MAXIMO_BYTES` still bounds below).
#
# HEIC/HEIF are deliberately absent: `FORMATOS_PERMITIDOS` admits them, but
# Pillow ships no HEIF codec here (`pillow-heif` is not a dependency), so
# those files cannot be decoded and pass through with their metadata intact.
# That is a KNOWN LIMIT of this control, not an oversight — see
# SECURITY-REPORT.md F-05. In practice `adjuntos.js` converts HEIC to JPEG
# client-side before upload, but that is best-effort and the server never
# relies on it.
_OPCIONES_DE_GUARDADO = {
    "JPEG": {"quality": "keep"},
    "PNG": {},
    "WEBP": {"lossless": True},
}


def limpiar_metadatos(archivo):
    """Return `archivo` re-encoded without its embedded metadata.

    A stored attachment is served from a public, permanent Vercel Blob URL:
    the listing is access-scoped, the file itself is not (design's known
    limitation). So whatever a phone camera embedded — GPS coordinates
    first and foremost, plus make/model and timestamps — leaves the
    application readable by anyone holding the link. Pillow writes EXIF only
    when explicitly handed it, so re-saving without passing `exif` drops the
    whole block, GPS sub-IFD included.

    Returns the ORIGINAL file untouched, never raising, when the image
    cannot be decoded, its format is not in `_OPCIONES_DE_GUARDADO`, or the
    re-encoded result would exceed `TAMANO_MAXIMO_BYTES`. This mirrors
    `generador._incrustar_adjuntos`'s "skip, never block" posture: a privacy
    control must not become a new way for a field upload to fail. The
    trade-off is explicit — an undecodable file keeps its metadata rather
    than being rejected.

    This reduces what the public URL exposes; it does not make the URL
    private. That is the separate, larger change F-05 describes.
    """
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    archivo.seek(0)
    originales = archivo.read()
    archivo.seek(0)

    try:
        imagen = Image.open(BytesIO(originales))
        opciones = _OPCIONES_DE_GUARDADO.get(imagen.format)
        if opciones is None:
            return archivo
        destino = BytesIO()
        imagen.save(destino, format=imagen.format, **opciones)
    except Exception:
        # Undecodable (HEIC/HEIF here), truncated, or a format whose
        # re-encode Pillow refuses. Keep the upload working.
        logger.info(
            "No se pudieron limpiar los metadatos de un adjunto; se guarda "
            "el archivo original.",
            exc_info=True,
        )
        archivo.seek(0)
        return archivo

    limpios = destino.getvalue()
    if len(limpios) > TAMANO_MAXIMO_BYTES:
        # Re-encoding can grow a file (a lossy WEBP forced to lossless, say).
        # The ceiling was already validated against the original, so honor it
        # rather than smuggling a larger file past it.
        archivo.seek(0)
        return archivo

    return SimpleUploadedFile(archivo.name, limpios, content_type=archivo.content_type)


def validar_adjunto(archivo) -> str | None:
    """Returns a stable error id (`formato-no-permitido`, `tamano-excedido`)
    or `None` if `archivo` (a Django `UploadedFile`) passes both checks —
    the same "stable id, free-form message elsewhere" convention
    `ProblemaDeDefinicion`/`ProblemaDeGeneracion` already use. Format is
    checked before size, matching the order this module's own tests and
    `views.subir_adjunto` exercise; the order is not semantically
    significant since callers stop on the first `None`-or-not result."""
    if archivo.content_type not in FORMATOS_PERMITIDOS:
        return "formato-no-permitido"
    if archivo.size > TAMANO_MAXIMO_BYTES:
        return "tamano-excedido"
    return None

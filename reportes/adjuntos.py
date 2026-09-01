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

# The only section that currently admits attachments (backlog #11 MVP,
# hardcoded to S-08 "croquis/evidencia"). Interim test-only resolution of
# design.md's open question — see `seccion_s08_id` in
# `reportes/tests/conftest.py` (tasks.md 1.5).
SECCION_DE_ADJUNTOS = "resultados"


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

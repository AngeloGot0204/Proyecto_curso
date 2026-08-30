"""Tests for the `adjuntos-reporte` capability (backlog #11).

PR 1 scope (tasks.md Phase 1, D1): standalone `Adjunto` model + migration
only. Server validation/endpoint/client-pipeline/Excel-embedding tests are
out of scope here and land in later PRs (Phase 2+).
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

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

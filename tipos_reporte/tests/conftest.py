import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def tipo_de_reporte_factory(db):
    """Create a TipoDeReporte with sensible defaults, overridable by kwargs.

    `plantilla` is a required FileField (spec: "TipoDeReporte model"), so the
    factory always supplies a minimal in-memory file unless the caller
    overrides it.
    """
    from tipos_reporte.models import TipoDeReporte

    def _create(**kwargs):
        defaults = {
            "nombre": "Instalación de resinas",
            "codigo": "instalacion-resinas",
            "plantilla": SimpleUploadedFile(
                "plantilla.xlsx", b"contenido-irrelevante-para-este-nivel"
            ),
        }
        defaults.update(kwargs)
        return TipoDeReporte.objects.create(**defaults)

    return _create

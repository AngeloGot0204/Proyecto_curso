import copy

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def definicion_valida():
    """A minimal but complete `estructura` dict: one section with one campo
    and one item, both fully specified, no collisions, all cells valid
    (design's Interfaces/Contracts example). Passes R1-R4 (Slice 2)
    unconditionally; `hoja`/template-anchor checks (R5-R6) are validated
    against it starting Slice 3, once `plantilla_xlsx` exists.

    Returns a factory (not the dict itself) so each test gets its own deep
    copy — callers mutate it freely (e.g. `del`, key reassignment) without
    leaking state into other tests."""

    def _crear():
        return copy.deepcopy(
            {
                "tipo": "instalacion-resinas",
                "plantilla": "JME.PC-0001.F1.xlsx",
                "hoja": "REPORTE",
                "secciones": [
                    {
                        "id": "datos-generales",
                        "titulo": "Datos generales",
                        "campos": [
                            {
                                "id": "turno",
                                "etiqueta": "Turno",
                                "tipo": "seleccion",
                                "opciones": ["Día", "Noche"],
                                "obligatorio": True,
                                "celda": "M12",
                            }
                        ],
                    },
                    {
                        "id": "proceso-instalacion",
                        "titulo": "Proceso de instalación",
                        "roles": ["construccion-jme", "qa-subterra"],
                        "items": [
                            {
                                "id": "p-01",
                                "texto": "Se verifica ángulo de perforación.",
                                "tipo": "rango-hora-inicio-fin",
                                "celda_inicio": "M25",
                                "celda_fin": "P25",
                            }
                        ],
                    },
                ],
            }
        )

    return _crear


@pytest.fixture
def plantilla_xlsx(tmp_path):
    """A real `.xlsx` workbook built with openpyxl, not committed to the
    repository (design's Testing Strategy). By default it declares one
    sheet named "REPORTE" with one merged range `M12:P12`, whose anchor
    (top-left) cell is `M12` — the exact shape ADR-0002 validated
    empirically. Returns a factory so each test can vary the sheet name
    and/or merged ranges."""

    def _crear(nombre_hoja="REPORTE", rangos=("M12:P12",)):
        wb = openpyxl.Workbook()
        wb.active.title = nombre_hoja
        for rango in rangos:
            wb.active.merge_cells(rango)
        destino = tmp_path / "plantilla.xlsx"
        wb.save(destino)
        return destino

    return _crear


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

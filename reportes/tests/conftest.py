"""Fixtures for the `reportes` app test suite (backlog #5).

App-local duplication of `usuario_factory`/`definicion_valida` is the
established project convention — `tipos_reporte` already duplicates
`usuario_factory` from `usuarios` deliberately (design's Testing Strategy).
"""

import copy

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone


@pytest.fixture
def usuario_factory(db):
    """Create a Usuario via `create_user`, so passwords hash (design's
    Testing Strategy — distinct from `tipos_reporte`'s plaintext-password
    fixture because `cliente_autenticado` needs a real login)."""
    from usuarios.models import Usuario

    def _create(**kwargs):
        defaults = {
            "username": "usuario_test",
            "password": "contrasena-de-prueba-123",
        }
        defaults.update(kwargs)
        return Usuario.objects.create_user(**defaults)

    return _create


@pytest.fixture
def definicion_valida():
    """A minimal but complete `estructura` dict: one section with one campo
    and one item, both fully specified (mirrored from
    `tipos_reporte/tests/conftest.py`, deep-copied per call)."""

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
def tipo_con_definicion_activa_factory(db, definicion_valida):
    """Create a `TipoDeReporte` with an already-activated `DefinicionDeTipo`
    (design D11): the row is built directly in activated shape
    (`estado=ACTIVA`, `version=1`, `activada_en=now`) to satisfy the
    `definicion_estado_implica_version` CheckConstraint, bypassing
    `servicios.activar_definicion` — activation itself is #3's tested
    responsibility, not the wizard's. Returns `(tipo, definicion)`."""
    from tipos_reporte.models import DefinicionDeTipo, Estado, TipoDeReporte

    def _crear(**kwargs):
        estructura = kwargs.pop("estructura", None) or definicion_valida()
        tipo = TipoDeReporte.objects.create(
            nombre=kwargs.pop("nombre", "Instalación de resinas"),
            codigo=kwargs.pop("codigo", "instalacion-resinas"),
            plantilla=kwargs.pop(
                "plantilla",
                SimpleUploadedFile(
                    "plantilla.xlsx", b"contenido-irrelevante-para-este-nivel"
                ),
            ),
        )
        definicion = DefinicionDeTipo.objects.create(
            tipo=tipo,
            archivo_yaml=SimpleUploadedFile(
                "definicion.yaml", b"secciones: []"
            ),
            yaml_fuente="secciones: []",
            estructura=estructura,
            estado=Estado.ACTIVA,
            version=1,
            activada_en=timezone.now(),
        )
        tipo.definicion_activa = definicion
        tipo.save(update_fields=["definicion_activa"])
        return tipo, definicion

    return _crear


@pytest.fixture
def reporte_factory(db, usuario_factory, tipo_con_definicion_activa_factory):
    """Create a `Reporte` with sensible defaults, overridable by kwargs."""
    from reportes.models import Reporte

    def _crear(**kwargs):
        if "tipo" not in kwargs or "definicion" not in kwargs:
            tipo, definicion = tipo_con_definicion_activa_factory()
            kwargs.setdefault("tipo", tipo)
            kwargs.setdefault("definicion", definicion)
        # `setdefault(key, usuario_factory())` would call `usuario_factory()`
        # eagerly on every invocation regardless of whether `creador` is
        # already in `kwargs` (Python evaluates arguments before the call),
        # creating an unwanted extra Usuario row that can collide with an
        # already-created "usuario_test" from another fixture in the same
        # test (e.g. `cliente_autenticado`). Only call it when actually
        # needed.
        if "creador" not in kwargs:
            kwargs["creador"] = usuario_factory()
        return Reporte.objects.create(**kwargs)

    return _crear


@pytest.fixture
def cliente_autenticado(client, usuario_factory):
    """A Django test client already logged in as a fresh Usuario
    (`client.force_login` — authentication itself is #2's tested concern,
    per design's Testing Strategy)."""
    usuario = usuario_factory()
    client.force_login(usuario)
    return client

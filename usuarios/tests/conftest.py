import pytest


@pytest.fixture
def usuario_factory(db):
    """Create a Usuario with sensible defaults, overridable by kwargs."""
    from usuarios.models import Usuario

    def _create(**kwargs):
        defaults = {
            "username": "usuario_test",
            "password": "irrelevant-not-hashed-for-this-fixture",
        }
        defaults.update(kwargs)
        return Usuario.objects.create(**defaults)

    return _create


@pytest.fixture
def administrador_factory(db):
    """Create a Usuario with `rol=Rol.ADMINISTRADOR`. Mirrors
    `tipos_reporte/tests/conftest.py`'s fixture (app-local convention)."""
    from usuarios.models import Rol, Usuario

    def _create(**kwargs):
        defaults = {
            "username": "administrador_test",
            "password": "irrelevant-not-hashed-for-this-fixture",
            "rol": Rol.ADMINISTRADOR,
        }
        defaults.update(kwargs)
        return Usuario.objects.create(**defaults)

    return _create

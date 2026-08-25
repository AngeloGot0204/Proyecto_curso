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

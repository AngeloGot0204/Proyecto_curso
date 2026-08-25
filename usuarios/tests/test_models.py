import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from usuarios.models import Usuario


@pytest.mark.django_db
def test_default_rol_is_usuario(usuario_factory):
    """A new Usuario with no explicit rol defaults to the least-privileged role."""
    usuario = usuario_factory(username="alguien")
    assert usuario.rol == "usuario"


@pytest.mark.django_db
def test_rol_rejects_invalid_value():
    """full_clean() rejects a rol value outside the declared choices."""
    usuario = Usuario(username="invalido", rol="superadmin")
    with pytest.raises(ValidationError):
        usuario.full_clean()


@pytest.mark.django_db
def test_setting_rol_administrador_grants_is_staff(usuario_factory):
    """Changing rol to administrador and saving sets is_staff automatically."""
    usuario = usuario_factory(username="promovido", rol="usuario")
    assert usuario.is_staff is False

    usuario.rol = "administrador"
    usuario.save()
    usuario.refresh_from_db()

    assert usuario.is_staff is True


@pytest.mark.django_db
def test_reverting_rol_to_usuario_revokes_is_staff(usuario_factory):
    """Downgrading rol from administrador to usuario revokes is_staff on save."""
    usuario = usuario_factory(username="degradado", rol="administrador")
    assert usuario.is_staff is True

    usuario.rol = "usuario"
    usuario.save()
    usuario.refresh_from_db()

    assert usuario.is_staff is False


@pytest.mark.django_db
def test_unchanged_administrador_save_preserves_is_staff_and_is_superuser(usuario_factory):
    """Re-saving an administrador with no rol change keeps is_staff True and
    does not touch is_superuser, which is independently managed."""
    usuario = usuario_factory(username="admin_estable", rol="administrador")
    assert usuario.is_staff is True
    assert usuario.is_superuser is False

    usuario.save()
    usuario.refresh_from_db()

    assert usuario.is_staff is True
    assert usuario.is_superuser is False


@pytest.mark.django_db
def test_bulk_update_bypassing_rol_invariant_raises_integrity_error(usuario_factory):
    """QuerySet.update() bypasses Usuario.save(), so the CheckConstraint
    usuario_rol_implica_is_staff must catch an inconsistent write."""
    usuario = usuario_factory(username="via_update", rol="usuario")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.filter(pk=usuario.pk).update(rol="administrador")


@pytest.mark.django_db
def test_bulk_update_clearing_is_staff_for_administrador_raises_integrity_error(usuario_factory):
    """QuerySet.update() setting is_staff=False on an administrador must be
    rejected by the same CheckConstraint from the database side."""
    usuario = usuario_factory(username="via_update_2", rol="administrador")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.filter(pk=usuario.pk).update(is_staff=False)


@pytest.mark.django_db
def test_create_superuser_forces_rol_administrador():
    """createsuperuser (is_superuser=True) forces rol=administrador and
    therefore is_staff=True, with no manual follow-up required."""
    usuario = Usuario.objects.create_superuser(
        username="root", email="root@example.com", password="irrelevant"
    )
    assert usuario.rol == "administrador"
    assert usuario.is_staff is True

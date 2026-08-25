from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CheckConstraint, Q


class Rol(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    USUARIO = "usuario", "Usuario"


class Usuario(AbstractUser):
    """Custom user model. `rol` is the source of truth for admin access;
    `is_staff` is a derived mirror kept in sync by save() and backstopped
    by database-level CheckConstraints (see design decision 1)."""

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.USUARIO)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=(
                    Q(rol=Rol.ADMINISTRADOR, is_staff=True)
                    | (~Q(rol=Rol.ADMINISTRADOR) & Q(is_staff=False))
                ),
                name="usuario_rol_implica_is_staff",
            ),
            CheckConstraint(
                condition=Q(is_superuser=False) | Q(rol=Rol.ADMINISTRADOR),
                name="usuario_superuser_es_administrador",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_superuser:
            # A superuser always wins over rol — the single documented
            # exception where a flag overrides rol (design decision 1).
            self.rol = Rol.ADMINISTRADOR
        self.is_staff = self.rol == Rol.ADMINISTRADOR
        super().save(*args, **kwargs)

    @property
    def es_administrador(self) -> bool:
        return self.rol == Rol.ADMINISTRADOR

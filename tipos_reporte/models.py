"""Models for the `tipos_reporte` app (backlog #3).

`DefinicionDeTipo` is a version row, not a mutable single record: each
successful activation freezes a content snapshot rather than overwriting the
previous one, and `TipoDeReporte.definicion_activa` is the single source of
truth for "which version is active" (design decision D1). See the design
doc (Engram `sdd/motor-definicion-tipo-reporte/design`) for the full
rationale, including why this invariant has no database-level backstop for
raw SQL writes (D3).
"""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import CheckConstraint, Q, UniqueConstraint


class Estado(models.TextChoices):
    """A DefinicionDeTipo's lifecycle state (design D1)."""

    BORRADOR = "borrador", "Borrador"
    ACTIVA = "activa", "Activa"
    HISTORICA = "historica", "Histórica"


class TipoDeDato(models.TextChoices):
    """Closed catalog of field/item data types (spec: Closed data-type
    catalog). Used by the activation validator in a later slice; declared
    here so both `tipos_reporte.models` and `tipos_reporte.validacion` share
    one definition."""

    TEXTO = "texto", "Texto"
    NUMERO = "numero", "Número"
    FECHA = "fecha", "Fecha"
    HORA = "hora", "Hora"
    SELECCION = "seleccion", "Selección"
    BOOLEANO = "booleano", "Booleano"
    RANGO_HORA_INICIO_FIN = "rango-hora-inicio-fin", "Rango hora inicio-fin"


# Fields whose value may never change once a DefinicionDeTipo leaves
# `borrador` — enforced by DefinicionDeTipo.save() (design D3). `version` is
# included because it is assigned once, at first activation, and must never
# be reassigned even by a later re-activation of the same row (design D2).
CONGELADOS = ("tipo_id", "estructura", "yaml_fuente", "version")
CONGELADOS_SET = frozenset(CONGELADOS)


class DefinicionDeTipoQuerySet(models.QuerySet):
    """Backstops the two ways application code can bypass `save()`/
    `delete()`'s instance-level guards (design D3, D9)."""

    def update(self, **kwargs):
        campos_congelados_tocados = CONGELADOS_SET.intersection(kwargs)
        if campos_congelados_tocados:
            filas_no_borrador = self.exclude(estado=Estado.BORRADOR)
            if filas_no_borrador.exists():
                raise ValidationError(
                    "No se pueden modificar campos congelados "
                    f"({', '.join(sorted(campos_congelados_tocados))}) de una "
                    "definición que ya no es borrador mediante update()."
                )
        return super().update(**kwargs)

    def delete(self):
        if self.filter(activada_en__isnull=False).exists():
            raise ValidationError(
                "No se puede eliminar una definición que ya fue activada "
                "alguna vez. Desactivá el tipo en su lugar."
            )
        return super().delete()


class TipoDeReporteQuerySet(models.QuerySet):
    """Backstops bulk deletion of a TipoDeReporte with an ever-activated
    history (design D9)."""

    def delete(self):
        if self.filter(definiciones__activada_en__isnull=False).distinct().exists():
            raise ValidationError(
                "No se puede eliminar un tipo de reporte que tuvo alguna "
                "definición activada alguna vez. Desactivalo en su lugar."
            )
        return super().delete()


class TipoDeReporte(models.Model):
    """A report type an administrator defines and (once validated) activates.

    `activo` is a property over `definicion_activa`, not a mirrored boolean:
    the active definition IS the source of truth, so there is no second copy
    that can drift (design D1).
    """

    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=100, unique=True)

    # The client's own document revision (e.g. "F1"), distinct from
    # DefinicionDeTipo.version, which is a system-assigned content-snapshot
    # integer (design D7). Optional: not every tipo names one yet.
    version_formato = models.CharField(max_length=20, blank=True, default="")

    logo = models.ImageField(upload_to="tipos_reporte/logos/", null=True, blank=True)
    plantilla = models.FileField(upload_to="tipos_reporte/plantillas/")

    definicion_activa = models.ForeignKey(
        "tipos_reporte.DefinicionDeTipo",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tipos_donde_es_activa",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = TipoDeReporteQuerySet.as_manager()

    class Meta:
        verbose_name = "Tipo de reporte"
        verbose_name_plural = "Tipos de reporte"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def activo(self) -> bool:
        return self.definicion_activa_id is not None

    def delete(self, *args, **kwargs):
        if self.definiciones.filter(activada_en__isnull=False).exists():
            raise ValidationError(
                "No se puede eliminar un tipo de reporte que tuvo alguna "
                "definición activada alguna vez. Desactivalo en su lugar."
            )
        super().delete(*args, **kwargs)


class DefinicionDeTipo(models.Model):
    """One version snapshot of a TipoDeReporte's structure (design D1).

    `estructura` is the normalized JSON tree that backlog items #4/#5 read
    from. `yaml_fuente` and `archivo_yaml` preserve the original upload for
    traceability, independent of file storage (design D4).
    """

    tipo = models.ForeignKey(
        TipoDeReporte,
        on_delete=models.CASCADE,
        related_name="definiciones",
    )

    archivo_yaml = models.FileField(upload_to="tipos_reporte/definiciones/")
    yaml_fuente = models.TextField()
    estructura = models.JSONField()

    # NULL while borrador: a draft has no version because it has never been
    # frozen (design D1). Assigned once, at first successful activation
    # (design D2), and never reassigned by a later re-activation.
    version = models.PositiveIntegerField(null=True, blank=True)

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR
    )
    activada_en = models.DateTimeField(null=True, blank=True)

    objects = DefinicionDeTipoQuerySet.as_manager()

    class Meta:
        verbose_name = "Definición de tipo"
        verbose_name_plural = "Definiciones de tipo"
        constraints = [
            UniqueConstraint(
                fields=["tipo"],
                condition=Q(estado=Estado.ACTIVA),
                name="definicion_una_activa_por_tipo",
            ),
            UniqueConstraint(
                fields=["tipo"],
                condition=Q(estado=Estado.BORRADOR),
                name="definicion_un_borrador_por_tipo",
            ),
            UniqueConstraint(
                fields=["tipo", "version"],
                condition=Q(version__isnull=False),
                name="definicion_version_unica_por_tipo",
            ),
            CheckConstraint(
                condition=(
                    Q(estado=Estado.BORRADOR)
                    & Q(version__isnull=True)
                    & Q(activada_en__isnull=True)
                )
                | (
                    ~Q(estado=Estado.BORRADOR)
                    & Q(version__isnull=False)
                    & Q(activada_en__isnull=False)
                ),
                name="definicion_estado_implica_version",
            ),
        ]

    def __str__(self):
        return f"{self.tipo.codigo} v{self.version or '(borrador)'}"

    def save(self, *args, **kwargs):
        # Checked against `anterior.estado` (the row's state BEFORE this
        # save), not `self.estado`: the borrador -> activa transition
        # itself legitimately assigns `version` for the first time (design
        # D2), so it must not trip this guard. Immutability only applies
        # once the row has ALREADY left borrador (design D3).
        #
        # Code-review fix: the read of `anterior` is locked with
        # `select_for_update()` inside an explicit transaction — without it,
        # two concurrent processes could both read the row BEFORE either
        # writes, both pass the guard (neither sees the other's pending
        # change), and the second overwrite fields that should be immutable.
        # The lock is held for the read+check+write, serializing concurrent
        # saves of the SAME row.
        if self.pk:
            with transaction.atomic():
                anterior = type(self).objects.select_for_update().get(pk=self.pk)
                if anterior.estado != Estado.BORRADOR:
                    cambiados = [
                        campo
                        for campo in CONGELADOS
                        if getattr(anterior, campo) != getattr(self, campo)
                    ]
                    if cambiados:
                        raise ValidationError(
                            f"Una definición {anterior.estado} es inmutable; "
                            f"campos modificados: {', '.join(cambiados)}. "
                            "Desactivá el tipo y subí una definición nueva."
                        )
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.activada_en is not None:
            raise ValidationError(
                "No se puede eliminar una definición que ya fue activada "
                "alguna vez. Desactivá el tipo en su lugar."
            )
        super().delete(*args, **kwargs)

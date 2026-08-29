"""Models for the `reportes` app (backlog #5).

`Reporte` snapshots the `DefinicionDeTipo` version in effect at creation
time, and `ValorDeReporte` persists exactly one row per captured value,
keyed by `identificador_de_campo` — the same key
`tipos_reporte.generador.claves_de_valor(nodo)` derives (design D5), so the
wizard's writes and the generator's reads never drift. See the design doc
(`openspec/changes/wizard-captura-server-rendered/design.md`) for the full
rationale, including why `estado` currently declares only `EN_PROGRESO`
(design D6) and why `valor` is a single `TextField` (design D1).
"""

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint


class EstadoDeReporte(models.TextChoices):
    """A `Reporte`'s lifecycle state (design D6). Only `EN_PROGRESO` is
    declared for now — every state past it belongs to later backlog items
    (#7 visto bueno, #9 offline, #10 sync); `TextChoices` + `CharField`
    makes adding members purely additive (no column change)."""

    EN_PROGRESO = "en_progreso", "En progreso"


class Reporte(models.Model):
    """One capture session against a `TipoDeReporte` (spec: Reporte
    creation). `definicion` snapshots the `DefinicionDeTipo` version in
    effect when the session started, independent of later re-activations of
    `tipo` (design's Interfaces/Contracts invariant, service-enforced)."""

    tipo = models.ForeignKey(
        "tipos_reporte.TipoDeReporte",
        on_delete=models.PROTECT,
        related_name="reportes",
    )
    definicion = models.ForeignKey(
        "tipos_reporte.DefinicionDeTipo",
        on_delete=models.PROTECT,
        related_name="reportes",
    )
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reportes_creados",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoDeReporte.choices,
        default=EstadoDeReporte.EN_PROGRESO,
    )

    class Meta:
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"

    def __str__(self):
        return f"Reporte #{self.pk} ({self.tipo.codigo})"


class ValorDeReporte(models.Model):
    """One captured value row, keyed by `identificador_de_campo` (spec:
    ValorDeReporte per captured value). `valor` is a single canonical
    `TextField` (design D1) — the codec in `reportes.valores` (Phase 3)
    serializes/rehydrates through the owning Django form field."""

    reporte = models.ForeignKey(
        Reporte, on_delete=models.CASCADE, related_name="valores"
    )
    identificador_de_campo = models.CharField(max_length=200)
    valor = models.TextField(blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="valores_escritos",
    )
    fecha = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Valor de reporte"
        verbose_name_plural = "Valores de reporte"
        constraints = [
            UniqueConstraint(
                fields=["reporte", "identificador_de_campo"],
                name="valor_unico_por_reporte_y_campo",
            ),
        ]

    def __str__(self):
        return f"{self.identificador_de_campo} = {self.valor!r}"

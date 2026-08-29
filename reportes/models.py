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
    """A `Reporte`'s lifecycle state (design D6). `TERMINADO` (backlog #7,
    spec `cierre-reporte`) is additive to `EN_PROGRESO` — `TextChoices` +
    `CharField` makes adding it purely a `choices`-metadata change, no
    column change. Every state past it (#9 offline, #10 sync) is still
    future work."""

    EN_PROGRESO = "en_progreso", "En progreso"
    TERMINADO = "terminado", "Terminado"


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


class VistoBueno(models.Model):
    """The creator's manual approval closing a `Reporte` (backlog #7, spec
    `cierre-reporte`, design D1). `OneToOneField` — not `ForeignKey` — so
    the database itself enforces at most one closure per `Reporte`;
    revocation/re-approval is out of scope (design D1's rationale), and
    widening to a `ForeignKey` later is an additive migration, not a data
    loss."""

    reporte = models.OneToOneField(
        Reporte, on_delete=models.CASCADE, related_name="visto_bueno"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vistos_buenos",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Visto bueno"
        verbose_name_plural = "Vistos buenos"

    def __str__(self):
        return f"Visto bueno de Reporte #{self.reporte_id}"


class ParticipacionEnReporte(models.Model):
    """One invited user's access grant to a `Reporte` (backlog #8, spec
    `colaboracion-reporte`, design D1/D2). The creator never gets a row here
    — "is creator" is checked independently, mirroring `cerrar_reporte`'s
    creator check (ADR-0006). No role/responsibility field: access is
    binary, fully open editing among participants."""

    reporte = models.ForeignKey(
        Reporte, on_delete=models.CASCADE, related_name="participaciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="participaciones",
    )
    fecha_invitacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Participación en reporte"
        verbose_name_plural = "Participaciones en reporte"
        constraints = [
            UniqueConstraint(
                fields=["reporte", "usuario"],
                name="participacion_unica_por_reporte_y_usuario",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} participa en Reporte #{self.reporte_id}"


class CambioDeValor(models.Model):
    """One immutable audit row per actual `ValorDeReporte` write (backlog
    #8, spec `colaboracion-reporte`, design D3-D5). `valor_anterior` is
    `NULL` for a first-time write on a field with no prior stored value —
    `""` never collides with that meaning because `guardar_valor` deletes
    empty values instead of storing them (design D3). FIFO-30 retention per
    `Reporte`, across all fields combined, is enforced by
    `reportes.valores._recortar_historial`, not by this model."""

    reporte = models.ForeignKey(
        Reporte, on_delete=models.CASCADE, related_name="cambios"
    )
    identificador_de_campo = models.CharField(max_length=200)
    valor_anterior = models.TextField(blank=True, null=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cambios_de_valor",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio de valor"
        verbose_name_plural = "Cambios de valor"

    def __str__(self):
        return f"Cambio de {self.identificador_de_campo} en Reporte #{self.reporte_id}"


class Generacion(models.Model):
    """One audit row per successful `.xlsx` generation (backlog #7, spec
    `generacion-documento`, design D3). Unbounded — creator or invited
    participant, unlimited repeats — so no uniqueness constraint is
    declared; `definicion` is recorded alongside `usuario`/`fecha` so the
    audit trail says which template version produced the file, independent
    of `Reporte.definicion` ever being re-pointed."""

    reporte = models.ForeignKey(
        Reporte, on_delete=models.CASCADE, related_name="generaciones"
    )
    definicion = models.ForeignKey(
        "tipos_reporte.DefinicionDeTipo",
        on_delete=models.PROTECT,
        related_name="generaciones",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generaciones",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Generación"
        verbose_name_plural = "Generaciones"

    def __str__(self):
        return f"Generación de Reporte #{self.reporte_id} ({self.fecha})"

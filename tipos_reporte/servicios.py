"""Activation service for `DefinicionDeTipo` (design D8).

`activar_definicion` is the ONLY place a `DefinicionDeTipo` transitions
`borrador -> activa`. It never mutates on a failed validation: the full
`validar_definicion` pass runs first, outside any transaction, and only a
clean result (`resultado.es_valida is True`) enters the atomic block that
performs the actual state transition (design D8's ordering guarantee,
ADR-0008's clean-failure requirement).

`desactivar_tipo` is the inverse, plain toggle S-14 offers: it clears the
tipo's FK and moves its active definition back to `historica`, keeping the
row's version (design D2 — a version identifies a content snapshot, not an
activation event, so deactivating and later re-activating the SAME row
must not allocate a new one).
"""

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from tipos_reporte.models import DefinicionDeTipo, Estado
from tipos_reporte.validacion import ResultadoDeValidacion, validar_definicion


def _siguiente_version(tipo) -> int:
    maxima = (
        DefinicionDeTipo.objects.filter(tipo=tipo)
        .exclude(version__isnull=True)
        .aggregate(maxima=Max("version"))["maxima"]
    )
    return (maxima or 0) + 1


def activar_definicion(definicion: DefinicionDeTipo) -> ResultadoDeValidacion:
    """Validate `definicion` against its tipo's real uploaded template and,
    only on a clean result, activate it atomically. Always returns the
    `ResultadoDeValidacion` — never raises for a validation failure."""
    tipo = definicion.tipo
    plantilla = tipo.plantilla
    plantilla.open("rb")
    try:
        resultado = validar_definicion(definicion.estructura, plantilla)
    finally:
        plantilla.close()

    if not resultado.es_valida:
        return resultado

    with transaction.atomic():
        anterior_activa = (
            DefinicionDeTipo.objects.filter(tipo=tipo, estado=Estado.ACTIVA)
            .exclude(pk=definicion.pk)
            .first()
        )
        if anterior_activa is not None:
            anterior_activa.estado = Estado.HISTORICA
            anterior_activa.save()

        if definicion.version is None:
            definicion.version = _siguiente_version(tipo)
        if definicion.activada_en is None:
            definicion.activada_en = timezone.now()
        definicion.estado = Estado.ACTIVA
        definicion.save()

        tipo.definicion_activa = definicion
        tipo.save(update_fields=["definicion_activa"])

    return resultado


def desactivar_tipo(tipo) -> None:
    """Clear `tipo.definicion_activa` and move its (former) active
    definition to `historica`. A no-op when the tipo has none."""
    with transaction.atomic():
        definicion_activa = tipo.definicion_activa
        if definicion_activa is None:
            return
        tipo.definicion_activa = None
        tipo.save(update_fields=["definicion_activa"])
        definicion_activa.estado = Estado.HISTORICA
        definicion_activa.save()

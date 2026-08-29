"""Pure access predicate for `Reporte` (backlog #8, spec
`colaboracion-reporte`, design D1). Mirrors `reportes.valores`/
`reportes.validacion`: no HTTP here, `views.py`'s `_reporte_accesible`
shim owns the `Http404` translation.
"""

from reportes.models import ParticipacionEnReporte


def tiene_acceso(reporte, usuario) -> bool:
    """True if `usuario` is `reporte`'s creator or an invited participant
    (design D1). Creator has no `ParticipacionEnReporte` row (ADR-0006) —
    the creator check runs first and independently."""
    if not usuario.is_authenticated:
        return False
    if reporte.creador_id == usuario.id:
        return True
    return ParticipacionEnReporte.objects.filter(
        reporte=reporte, usuario=usuario
    ).exists()

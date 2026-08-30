"""Pure query/search/filter helpers for the "Mis reportes" list (backlog
#12, spec `listado-reportes`, design D2/D3/D4). No HTTP, no `request` —
mirrors `reportes.permisos`/`reportes.valores`/`reportes.validacion`.
`reportes/views.py::mis_reportes` (PR 2 of this chain) owns the `request`
translation.
"""

import unicodedata

from django.db.models import Q, QuerySet

from reportes.models import EstadoDeReporte, Reporte


def _sin_acentos(texto: str) -> str:
    """Fold accents and case for a locale-lenient comparison (design D4).
    NFKD-decompose, drop combining marks, then casefold."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def reportes_accesibles(usuario) -> QuerySet:
    """Every `Reporte` `usuario` can access — creator or invited
    participant (spec 'Access-Scoped Report List'), the verbatim access
    query already used by `paso`/`revision`/`generar`/`participantes`
    (backlog #8, design D1). Deterministically ordered (design D2)."""
    return (
        Reporte.objects.filter(
            Q(creador=usuario) | Q(participaciones__usuario=usuario)
        )
        .distinct()
        .select_related("tipo", "creador")
        .order_by("-fecha_creacion", "-id")
    )


def aplicar_busqueda(qs: QuerySet, q: str) -> QuerySet:
    """Filter `qs` by `tipo__nombre`, `tipo__codigo` (accent-folded, design
    D4) OR `creador__username` (plain `icontains`). A blank/whitespace-only
    `q` is a no-op (spec 'Search and Estado Filter')."""
    q = (q or "").strip()
    if not q:
        return qs

    from tipos_reporte.models import TipoDeReporte

    q_plegado = _sin_acentos(q)
    ids_tipo = [
        tipo.id
        for tipo in TipoDeReporte.objects.all()
        if q_plegado in _sin_acentos(tipo.nombre)
        or q_plegado in _sin_acentos(tipo.codigo)
    ]
    return qs.filter(Q(tipo_id__in=ids_tipo) | Q(creador__username__icontains=q))


def normalizar_estado(valor) -> str:
    """Normalize a raw `?estado=` value against the real
    `EstadoDeReporte.values`; anything unrecognized (including `None` or
    empty) becomes `""` — never an error (design D3)."""
    if valor in EstadoDeReporte.values:
        return valor
    return ""

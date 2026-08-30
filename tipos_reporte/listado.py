"""Pure query/search helpers for the tipos-de-reporte administration screen
(backlog #13, S-14, spec `administracion-tipos-reporte`, design D3). No
HTTP, no `request` — mirrors `reportes/listado.py`'s exact pattern.
`tipos_reporte/views.py` (PR 1 of this chain) owns the `request`
translation and `Paginator.get_page()` usage.

**Documented deviation (design D3)**: `_sin_acentos` is duplicated here
verbatim rather than imported from `reportes.listado` — its twin lives at
`reportes/listado.py::_sin_acentos`. `tipos_reporte` must never import
`reportes` (dependency direction, backlog #11's design D5 rationale).
"""

import unicodedata

from django.db.models import Q, QuerySet

from tipos_reporte.models import TipoDeReporte


def _sin_acentos(texto: str) -> str:
    """Fold accents and case for a locale-lenient comparison (design D3,
    twin of `reportes/listado.py::_sin_acentos`). NFKD-decompose, drop
    combining marks, then casefold."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def tipos_administrables() -> QuerySet:
    """Every `TipoDeReporte` row, ordered alphabetically by `nombre` with a
    mandatory `id` tiebreaker (design D3), `select_related` on
    `definicion_activa` to avoid N+1 queries when the list/detail views
    render each row's active definition."""
    return TipoDeReporte.objects.select_related("definicion_activa").order_by(
        "nombre", "id"
    )


def aplicar_busqueda(qs: QuerySet, q: str) -> QuerySet:
    """Filter `qs` by `nombre` or `codigo` (accent-folded, design D3). A
    blank/whitespace-only `q` is a no-op (spec 'List supports search')."""
    q = (q or "").strip()
    if not q:
        return qs

    q_plegado = _sin_acentos(q)
    ids = [
        tipo.id
        for tipo in TipoDeReporte.objects.all()
        if q_plegado in _sin_acentos(tipo.nombre) or q_plegado in _sin_acentos(tipo.codigo)
    ]
    return qs.filter(Q(id__in=ids))

"""Pure query/search/filter/bucket/avance helpers for the "Mis reportes"
list (backlog #12; spec `listado-reportes`; design D1-D5). No HTTP, no
`request` — mirrors `reportes.permisos`/`reportes.valores`/
`reportes.validacion`. `reportes/views.py::mis_reportes` owns the `request`
translation and rendering (design's Technical Approach).
"""

import unicodedata
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from reportes.models import Reporte
from reportes.validacion import validar_reporte

# Design's Interfaces/Contracts: the three computed status buckets, in
# display/grouping order (first match wins — spec 'Status Bucket Grouping').
# `en_progreso`/`terminado` are byte-identical to the old `EstadoDeReporte`
# values so the `cierre-reporte` redirect target keeps working unchanged;
# `listo_para_generar` is new.
BUCKETS = (
    ("en_progreso", "En progreso"),
    ("listo_para_generar", "Listos para generar"),
    ("terminado", "Terminados"),
)
_BUCKET_IDS = tuple(id_ for id_, _titulo in BUCKETS)

# Design's Interfaces/Contracts: the `?relacion=` filter values, one
# non-nested level applied before bucketing.
RELACIONES = ("creados", "compartidos", "todos")

# Design D1's rationale: the `regla` id `reportes.validacion` assigns to a
# missing obligatorio field — the only errore kind that feeds the avance
# denominator/numerator (never a rango-hora/"no cumple" advertencia).
_REGLA_OBLIGATORIO_FALTANTE = "valor-obligatorio-faltante"


@dataclass(frozen=True)
class TarjetaDeReporte:
    """One card's presentation contract for the "Mis reportes" list (design
    D4) — a view-model, not the raw `Reporte`, so `numero_registro is None`
    (offline/unsynced, per `sincronizacion-numero-registro`) has somewhere
    to live even though a persisted `Reporte.numero_registro` can never
    itself be null."""

    reporte: Reporte
    bucket: str
    avance: int
    numero_registro: int | None


def _sin_acentos(texto: str) -> str:
    """Fold accents and case for a locale-lenient comparison (design D4).
    NFKD-decompose, drop combining marks, then casefold."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def reportes_accesibles(usuario) -> QuerySet:
    """Every `Reporte` `usuario` can access — creator or invited
    participant (spec 'Access-Scoped Report List'), the verbatim access
    query already used by `paso`/`revision`/`generar`/`participantes`
    (backlog #8, design D1). Deterministically ordered (design D2).
    Excludes soft-deleted reports (`eliminado_en__isnull=True`) — a deleted
    report behaves as if it never existed, for creator and participants
    alike."""
    return (
        Reporte.objects.filter(
            Q(creador=usuario) | Q(participaciones__usuario=usuario),
            eliminado_en__isnull=True,
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
    """Normalize a raw `?estado=` value against the computed BUCKETS ids
    (design's Interfaces/Contracts — retargeted from the raw
    `EstadoDeReporte` field to the 3 bucket ids); anything unrecognized
    (including `None` or empty) becomes `""` — never an error (design D3)."""
    if valor in _BUCKET_IDS:
        return valor
    return ""


def normalizar_relacion(valor) -> str:
    """Normalize a raw `?relacion=` value against `RELACIONES`; anything
    unrecognized (including `None` or empty) becomes `"todos"` — the
    default, never an error (spec 'Creador/Compartido/Todos Filter')."""
    if valor in RELACIONES:
        return valor
    return "todos"


def aplicar_relacion(qs: QuerySet, usuario, relacion: str) -> QuerySet:
    """Narrow an already access-scoped `qs` by `relacion` (spec 'Filter
    restricts before grouping'). `qs` is assumed pre-filtered to rows
    `usuario` can access (creator or invited participant), so "compartidos"
    is simply "not created by me" within that already-scoped set — never a
    second `ParticipacionEnReporte` join."""
    if relacion == "creados":
        return qs.filter(creador=usuario)
    if relacion == "compartidos":
        return qs.exclude(creador=usuario)
    return qs


def porcentaje_de_avance(estructura: dict, faltantes) -> int:
    """% avance = (obligatorios llenos) / (total obligatorios), floored
    (design D5 — `round` would show 100% for 249/250; floor keeps '100% ⟺
    nothing obligatory missing' exact). `total == 0` ⇒ 100 (design D5,
    spec 'Percent avance matches wizard completeness')."""
    from tipos_reporte.generador import claves_obligatorias

    total = len(claves_obligatorias(estructura))
    if total == 0:
        return 100
    llenas = total - len(faltantes)
    return 100 * llenas // total


def bucket_de_reporte(tiene_visto_bueno: bool, puede_generar: bool) -> str:
    """First-match-wins bucket priority (spec 'Status Bucket Grouping'):
    `terminado` (has `VistoBueno`) > `listo_para_generar` (no missing
    obligatorio field) > `en_progreso` (otherwise)."""
    if tiene_visto_bueno:
        return "terminado"
    if puede_generar:
        return "listo_para_generar"
    return "en_progreso"


def construir_tarjetas(qs) -> list:
    """Build one `TarjetaDeReporte` per row of `qs` (design's Data Flow).
    `qs` must already be `.annotate(tiene_visto_bueno=Exists(...))`'d
    (design D2) — bucketing reuses that annotation instead of an extra
    query per row. `validar_reporte` supplies both `puede_generar` (design
    D3 — the authoritative ready predicate) and the exact
    `valor-obligatorio-faltante` ids `porcentaje_de_avance` needs as its
    numerator/denominator gap (design D1)."""
    tarjetas = []
    for reporte in qs:
        resultado = validar_reporte(reporte)
        faltantes = tuple(
            errore.identificador_de_campo
            for errore in resultado.errores
            if errore.regla == _REGLA_OBLIGATORIO_FALTANTE
        )
        bucket = bucket_de_reporte(reporte.tiene_visto_bueno, resultado.puede_generar)
        avance = porcentaje_de_avance(reporte.definicion.estructura, faltantes)
        tarjetas.append(
            TarjetaDeReporte(
                reporte=reporte,
                bucket=bucket,
                avance=avance,
                numero_registro=reporte.numero_registro,
            )
        )
    return tarjetas


def agrupar_por_bucket(tarjetas) -> list:
    """Partition `tarjetas` into BUCKETS-ordered groups (design's
    Interfaces/Contracts): `[{id, titulo, tarjetas}]`, one entry per bucket
    in `BUCKETS` order, always present even when empty (spec 'CTA is always
    present' relies on the surrounding template, not this list being
    non-empty)."""
    por_bucket = {id_: [] for id_, _titulo in BUCKETS}
    for tarjeta in tarjetas:
        por_bucket[tarjeta.bucket].append(tarjeta)
    return [
        {"id": id_, "titulo": titulo, "tarjetas": por_bucket[id_]}
        for id_, titulo in BUCKETS
    ]

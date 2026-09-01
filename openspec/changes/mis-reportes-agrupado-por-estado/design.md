# Design: Mis Reportes — Agrupado por Estado + Selección de Tipo (S-02/S-03)

## Technical Approach

Keep the established split: `reportes/listado.py` stays pure (no `request`,
no HTTP) and owns bucketing, `?relacion=`/`?estado=` normalization and %
avance; `views.py::mis_reportes` owns only request translation and
rendering. Buckets are computed read-time — no model/migration change
(spec "Status Bucket Grouping"). S-03 is an additive route/view/template
that only POSTs to the untouched `reportes_nuevo`.

Note: the delta spec supersedes `proposal.md` — **3** buckets, not 4;
"pendiente de otra parte" was dropped, so grouping never depends on the
requesting user.

## Architecture Decisions

### D1 — Denominator of % avance comes from a new public `claves_obligatorias`

**Choice**: extract `tipos_reporte.generador.claves_obligatorias(estructura)`
(the exact comprehension `_validar_completitud` already runs) and make
`_validar_completitud` call it. Numerator = `total − len(faltantes)`, where
`faltantes` are the `regla == "valor-obligatorio-faltante"` errores of one
`validar_reporte(reporte)` call.
**Alternatives**: re-walk `_iterar_nodos` inside `listado.py` (drift, the
exact risk the proposal names); parse `ValoresIncompletos` only (gives the
numerator, never the denominator).
**Rationale**: mirrors the existing `claves_de_valor` extraction — one
owner, `_destinos`-consistent keys, zero behavior change. Guarantees the
spec scenario "`puede_generar` ⇒ 100%" by construction.

### D2 — Bucket, then filter, then paginate (over the whole scoped queryset)

**Choice**: build cards for every access-scoped row, apply `?estado=`, then
`Paginator`. `terminado` is detected DB-side via
`annotate(tiene_visto_bueno=Exists(VistoBueno...))`; `select_related("definicion")`
and `prefetch_related("valores")` keep it at ~4 queries regardless of N.
**Alternatives**: paginate first, then bucket (today's shape) — breaks
`?estado=terminado` paging and the `cierre-reporte` redirect, which must find
the just-closed report on page 1; DB-side bucket annotation — impossible,
"obligatorio" lives in `DefinicionDeTipo.estructura` JSON, not in columns.
**Rationale**: correctness of the estado filter outranks the O(N) in-memory
cost at this corpus size; the query count stays constant.

### D3 — `puede_generar` stays the authoritative ready predicate

**Choice**: bucket 2 calls `validar_reporte(reporte)`, not a local
"faltantes == 0" check.
**Alternatives**: reuse `listado`'s own missing-count.
**Rationale**: spec cites `validacion-reporte`; with `valores` prefetched the
call costs no extra query, and a future non-obligatorio errore rule cannot
silently promote a report to "listo para generar".

### D4 — Cards are a `TarjetaDeReporte` view-model, not raw `Reporte`

**Choice**: frozen dataclass `TarjetaDeReporte(reporte, bucket, avance,
numero_registro: int | None)`; the template renders the `local` chip when
`numero_registro is None`.
**Alternatives**: annotate the `Reporte` instances in place.
**Rationale**: `Reporte.numero_registro` is `unique`, non-null, filled by a
`nextval` `db_default`, so a persisted row can *never* be unassigned — the
spec's `local` branch is untestable against the model. The view-model makes
it a pure, unit-testable presentation contract, ready for the offline rows
`vista-sincronizacion-pendientes` will surface.

### D5 — Floor, not round, for the percentage

**Choice**: `100 * llenas // total`; `total == 0` ⇒ 100.
**Rationale**: `round` would show 100% for 249/250. Floor keeps
"100% ⟺ nothing obligatory missing" exact.

### D6 — S-03 filters on `definicion_activa__isnull=False`

**Choice**: query all `TipoDeReporte` ordered by `nombre`; "available" =
`definicion_activa_id is not None`; section count = `len(estructura["secciones"])`.
**Rationale**: `TipoDeReporte.activo` is a **property** over
`definicion_activa` (ADR/design D1 of `motor-definicion-tipo-reporte`), not a
column — `filter(activo=True)` would raise. This is the spec's
"activo=True and definicion_activa" collapsed to its single real predicate.

## Data Flow

    GET ?q=&relacion=&estado=&page=
      │
      ├─ reportes_accesibles(user)         creador OR participación
      ├─ aplicar_busqueda(qs, q)           unchanged
      ├─ aplicar_relacion(qs, user, rel)   creados | compartidos | todos
      ├─ .annotate(Exists(VistoBueno)) .select_related(definicion)
      │                                .prefetch_related(valores)
      ├─ construir_tarjetas(qs) ──→ validar_reporte + claves_obligatorias
      │                                 ↓
      │                        TarjetaDeReporte(bucket, avance, n° registro)
      ├─ filter by estado (bucket id)
      ├─ Paginator(...).get_page(page)
      └─ agrupar_por_bucket(page_obj) → 3 ordered sections

    S-03:  mis_reportes ──"+ Nuevo reporte"──→ seleccion_de_tipo
                              POST (csrf, per-tipo form) ──→ reportes_nuevo (unchanged)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tipos_reporte/generador.py` | Modify | Extract public `claves_obligatorias`; `_validar_completitud` delegates to it |
| `reportes/listado.py` | Modify | `TarjetaDeReporte`, `BUCKETS`, `normalizar_relacion`, `aplicar_relacion`, `porcentaje_de_avance`, `bucket_de_reporte`, `construir_tarjetas`, `agrupar_por_bucket`; `normalizar_estado` retargeted to bucket ids |
| `reportes/views.py` | Modify | `mis_reportes` rewritten per D2; new `seleccion_de_tipo` view |
| `reportes/urls.py` | Modify | `path("nuevo/", …, name="reportes_seleccion_tipo")` placed before `<str:codigo_tipo>/nuevo/` |
| `reportes/templates/reportes/mis_reportes.html` | Modify | 3 bucket sections, relación+estado filter, avance/registro chips, fixed "+ Nuevo reporte" |
| `reportes/templates/reportes/seleccion_tipo.html` | Create | S-03 list; one POST form per available tipo, disabled + "próximamente" otherwise |
| `reportes/tests/test_listado.py` | Modify | Pure-helper unit tests |
| `reportes/tests/test_views.py` | Modify | View/integration tests |

## Interfaces / Contracts

```python
# reportes/listado.py
BUCKETS = (
    ("en_progreso", "En progreso"),
    ("listo_para_generar", "Listos para generar"),
    ("terminado", "Terminados"),
)
RELACIONES = ("creados", "compartidos", "todos")

@dataclass(frozen=True)
class TarjetaDeReporte:
    reporte: Reporte
    bucket: str            # one of BUCKETS ids
    avance: int            # 0..100
    numero_registro: int | None   # None ⇒ template renders the `local` chip

def porcentaje_de_avance(estructura: dict, faltantes: tuple[str, ...]) -> int
def bucket_de_reporte(tiene_visto_bueno: bool, puede_generar: bool) -> str
def construir_tarjetas(qs) -> list[TarjetaDeReporte]
def agrupar_por_bucket(tarjetas) -> list[dict]   # [{id, titulo, tarjetas}] in BUCKETS order

# tipos_reporte/generador.py
def claves_obligatorias(estructura: dict) -> list[str]
```

`?estado=` values are the bucket ids. `en_progreso`/`terminado` are
byte-identical to the existing `EstadoDeReporte` values, so the
`cierre-reporte` redirect keeps working unchanged; `listo_para_generar` is
new. Unrecognized ⇒ `""` (unfiltered), never an error.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `claves_obligatorias` == the ids `_validar_completitud` reports missing on an empty `valores`; `porcentaje_de_avance` 7/10→70, 249/250→99, 0 obligatorios→100; `bucket_de_reporte` priority; `normalizar_estado`/`normalizar_relacion` fallbacks; `agrupar_por_bucket` order | pytest, pure functions, no DB |
| Integration | 3-bucket placement (incl. "same bucket for creador and invitado"); `?relacion=` applied before grouping; `?estado=terminado` finds a report that would be on page 2; CTA present on an empty result set; `local` chip on `numero_registro=None`; S-03 lists activos + disabled "próximamente", anonymous redirect, POST creates via `reportes_nuevo` | pytest-django client, `--reuse-db` |
| E2E | — | Not configured in this project |

Strict TDD (`openspec/config.yaml: strict_tdd: true`): every case above is a
RED test before its production code. `test_validar_reporte_coincide_con_validar_completitud`
must stay green after D1's extraction.

## Threat Matrix

New HTTP route only; no shell, subprocess, VCS or PR automation.

| Boundary | Applicability |
|---|---|
| Documentation-like paths | N/A — no file classification or execution |
| Git repository selection | N/A — no VCS invocation |
| Commit state | N/A — no VCS invocation |
| Push state | N/A — no VCS invocation |
| PR commands | N/A — no PR automation |

Route-level safety is covered by spec scenarios instead: `@login_required` on
`seleccion_de_tipo` (anonymous ⇒ login redirect), unrecognized `?estado=`/
`?relacion=` degrade to unfiltered rather than raising, and S-03 never
duplicates `Reporte` creation (`reportes_nuevo` keeps its `@require_POST` +
`id_local` idempotency).

## Migration / Rollout

No migration — no schema change. Rollout is a straight deploy; rollback is
reverting `listado.py`/`views.py`/the template plus the additive S-03
route/view/template. `claves_obligatorias` is behavior-preserving and safe to
keep on rollback.

## Open Questions

- [ ] `cierre-en-participantes` must redirect to `?estado=terminado` (bucket
      id, unchanged string). Confirm during apply that no other estado id is used.
- [ ] `proposal.md` still describes 4 buckets; update or archive-note it so
      the 3-bucket spec stays the single source of truth.

"""String codec between a wizard form's `cleaned_data` and
`ValorDeReporte.valor` (backlog #5, Phase 3; design D2, D3).

`a_texto(campo, valor)` serializes ONE cleaned Python value into its
canonical string by dispatching on the value's TYPE — never a per-`tipo`
parser table — because Django's own field types already agree on one
canonical string representation each (`DateField`→ISO, `TimeField`→`HH:MM`,
`DecimalField`→`str(Decimal)`). `desde_texto(campo, texto)` rehydrates by
delegating straight to `campo.to_python(texto)`: the SAME field that would
have produced the string is the only thing trusted to parse it back, so no
second parser can silently disagree with the first (design D2).

`guardar_valor` implements design D3's completeness-safe upsert: an empty
submitted value (`None` or `""`) DELETES the row instead of persisting an
empty string, because `tipos_reporte.generador._validar_completitud` uses a
*membership* test — an `""` row would silently satisfy an `obligatorio`
field. `booleano` values are never "empty" under this rule: `False` is a
provided value, serialized as `"false"`, and persists its own row.

`guardar_valor` also records an immutable `CambioDeValor` audit row on
every ACTUAL write (backlog #8, spec `colaboracion-reporte`, design D4/D5):
read-before-write captures `valor_anterior` (`None` on a field's first
write), a no-op guard skips unchanged resubmits (design D4 — load-bearing,
since `paso`'s per-step POST loop calls `guardar_valor` for every field on
every submit), and `_recortar_historial` enforces FIFO-30 retention scoped
per `Reporte` across all fields combined, all inside one
`transaction.atomic()`.
"""

import datetime
from decimal import Decimal

from django.db import transaction

from reportes.models import CambioDeValor, ValorDeReporte

TAMANO_MAXIMO_HISTORIAL = 30


def _serializar(valor) -> str:
    """Dispatch on `valor`'s own Python type (design D2). `bool` is checked
    BEFORE the numeric branches — `bool` is a subclass of `int` in Python —
    so a `booleano` field's value is never coerced through a numeric/date
    branch and always becomes `"true"`/`"false"` (design D3)."""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime.time):
        return valor.strftime("%H:%M")
    if isinstance(valor, datetime.date):
        return valor.isoformat()
    return str(valor)


def a_texto(campo, valor) -> str:
    """Serialize one cleaned form value to its canonical string (design D2).
    `campo` is accepted for symmetry with `desde_texto` — the canonical
    string is fully determined by `valor`'s own Python type, never by which
    field produced it."""
    return _serializar(valor)


def desde_texto(campo, texto):
    """Rehydrate one persisted `ValorDeReporte.valor` string back into the
    Python value its owning form field understands, by delegating to that
    SAME field's `to_python` (design D2)."""
    return campo.to_python(texto)


def valores_de_reporte(reporte) -> dict[str, str]:
    """Build the `{identificador_de_campo: valor}` dict for `reporte` from
    its persisted `ValorDeReporte` rows (design D5) — the ONE shared
    construction both `validacion.py::validar_reporte` and
    `views.py::paso`/`generar` use, replacing what used to be a duplicated
    inline comprehension in each call site."""
    return {
        valor.identificador_de_campo: valor.valor
        for valor in reporte.valores.all()
    }


def _recortar_historial(reporte):
    """Enforce FIFO-30 retention on `reporte`'s `CambioDeValor` rows, scoped
    per `Reporte` across all fields combined (design D5). Ordered by
    `-fecha, -id` — `-id` breaks `fecha` ties deterministically, since a
    step POST can write several fields inside the same microsecond.
    Materialized via `list(...)` before `pk__in` because Django forbids
    `.delete()` on a sliced queryset and MySQL disallows self-referencing
    subselects; Postgres would allow it, but this stays backend-agnostic."""
    sobrantes = list(
        CambioDeValor.objects.filter(reporte=reporte)
        .order_by("-fecha", "-id")
        .values_list("pk", flat=True)[TAMANO_MAXIMO_HISTORIAL:]
    )
    if sobrantes:
        CambioDeValor.objects.filter(pk__in=sobrantes).delete()


def guardar_valor(reporte, identificador_de_campo, valor, autor):
    """Upsert or delete one `ValorDeReporte` row for `identificador_de_campo`
    on `reporte` (design D3). Equality against `None`/`""` — never
    truthiness — so a `Decimal("0")` or `False` boolean is never mistaken
    for "not provided".

    Also records a `CambioDeValor` audit row on every ACTUAL change (backlog
    #8, design D4): reads the prior `ValorDeReporte` before writing so
    `valor_anterior` is `None` on a field's first write, skips the audit
    insert entirely on a no-op (unchanged resubmit, or an empty submit with
    no existing row — design D4's load-bearing guard), and trims the
    report's history to the newest 30 rows via `_recortar_historial`. All
    inside one `transaction.atomic()`."""
    with transaction.atomic():
        fila_previa = ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo=identificador_de_campo
        ).first()
        valor_anterior = fila_previa.valor if fila_previa is not None else None

        if valor is None or valor == "":
            if fila_previa is None:
                return
            ValorDeReporte.objects.filter(
                reporte=reporte, identificador_de_campo=identificador_de_campo
            ).delete()
        else:
            valor_serializado = _serializar(valor)
            if fila_previa is not None and fila_previa.valor == valor_serializado:
                return
            ValorDeReporte.objects.update_or_create(
                reporte=reporte,
                identificador_de_campo=identificador_de_campo,
                defaults={"valor": valor_serializado, "autor": autor},
            )

        CambioDeValor.objects.create(
            reporte=reporte,
            identificador_de_campo=identificador_de_campo,
            valor_anterior=valor_anterior,
            autor=autor,
        )
        _recortar_historial(reporte)

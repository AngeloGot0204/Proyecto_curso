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
"""

import datetime
from decimal import Decimal

from reportes.models import ValorDeReporte


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


def guardar_valor(reporte, identificador_de_campo, valor, autor):
    """Upsert or delete one `ValorDeReporte` row for `identificador_de_campo`
    on `reporte` (design D3). Equality against `None`/`""` — never
    truthiness — so a `Decimal("0")` or `False` boolean is never mistaken
    for "not provided"."""
    if valor is None or valor == "":
        ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo=identificador_de_campo
        ).delete()
        return

    ValorDeReporte.objects.update_or_create(
        reporte=reporte,
        identificador_de_campo=identificador_de_campo,
        defaults={"valor": _serializar(valor), "autor": autor},
    )

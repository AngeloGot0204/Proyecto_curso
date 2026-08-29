"""Dynamic Django `Form` builder for one wizard-captura section (backlog
#5, Phase 3; design D4, D5, D8).

`construir_formulario_seccion(seccion)` turns one `estructura["secciones"][i]`
dict into a Django `Form` **class** whose field NAMES are exactly
`tipos_reporte.generador.claves_de_valor(nodo)` — so `reportes.valores`'s
codec writes/reads the same `ValorDeReporte.identificador_de_campo` keys
`generador.generar_reporte` consumes (design D5). Node traversal reuses
`validacion._iterar_nodos` (design D4) rather than a parallel iterator, so
`clave_de_etiqueta` (`etiqueta` for campos, `texto` for items) never drifts
from the generator's own label rule.

Every field is `required=False` (design D8): the class must support both
`Form(initial=...)` (GET) and `Form(data=...)` (POST), and blocking on a
missing `obligatorio` value is explicitly out of scope (backlog #6). An
`obligatorio` node only adds the HTML `required` widget attribute plus its
own visual marker in the template — never server-side validation here.
"""

from django import forms

from tipos_reporte.generador import claves_de_valor
from tipos_reporte.models import TipoDeDato
from tipos_reporte.validacion import _iterar_nodos

_FORMATO_FECHA = "%Y-%m-%d"
_FORMATO_HORA = "%H:%M"


def _widget_fecha():
    return forms.DateInput(attrs={"type": "date"}, format=_FORMATO_FECHA)


def _widget_hora():
    return forms.TimeInput(attrs={"type": "time"}, format=_FORMATO_HORA)


def _campo_escalar(tipo, opciones):
    """One Django form field for a non-range node's `tipo` (design's Type
    mapping table). Raises for a `tipo` outside the closed catalog — every
    caller here already iterated an already-validated `estructura`, so this
    is a programming-error guard, not a user-facing path."""
    if tipo == TipoDeDato.TEXTO:
        return forms.CharField(required=False, widget=forms.TextInput())
    if tipo == TipoDeDato.NUMERO:
        return forms.DecimalField(
            required=False,
            localize=False,
            widget=forms.NumberInput(attrs={"step": "any"}),
        )
    if tipo == TipoDeDato.FECHA:
        return forms.DateField(required=False, widget=_widget_fecha())
    if tipo == TipoDeDato.HORA:
        return forms.TimeField(required=False, widget=_widget_hora())
    if tipo == TipoDeDato.SELECCION:
        opciones_con_vacio = [("", "—")] + [(o, o) for o in (opciones or [])]
        return forms.ChoiceField(
            required=False, choices=opciones_con_vacio, widget=forms.Select()
        )
    if tipo == TipoDeDato.BOOLEANO:
        return forms.BooleanField(required=False, widget=forms.CheckboxInput())
    raise ValueError(f"Tipo de dato sin mapeo de campo de formulario: {tipo!r}")


def _marcar_obligatorio(campo, obligatorio):
    """HTML `required` attribute only — Python `required` stays `False`
    (design D8: the non-blocking `obligatorio` marker)."""
    if obligatorio:
        campo.widget.attrs["required"] = True
    return campo


def _campos_de_rango(clave_inicio, clave_fin, etiqueta, obligatorio):
    """`rango-hora-inicio-fin` → two independent `TimeField`s (design's Type
    mapping table), labeled `"{etiqueta} — Inicio"` / `"— Fin"` so the
    template can iterate the form without special-casing ranges."""
    inicio = forms.TimeField(
        required=False, label=f"{etiqueta} — Inicio", widget=_widget_hora()
    )
    fin = forms.TimeField(
        required=False, label=f"{etiqueta} — Fin", widget=_widget_hora()
    )
    _marcar_obligatorio(inicio, obligatorio)
    _marcar_obligatorio(fin, obligatorio)
    return {clave_inicio: inicio, clave_fin: fin}


def construir_formulario_seccion(seccion: dict) -> type[forms.Form]:
    """`type("FormularioDeSeccion", (forms.Form,), campos)` (design's
    Interfaces/Contracts). A section with an empty `campos`/`items` list
    yields a `Form` class with zero fields — the spec's "Section with no
    campos/items still renders" scenario relies on this being a valid,
    renderable class."""
    campos: dict[str, forms.Field] = {}

    for _ubicacion, nodo, clave_de_etiqueta in _iterar_nodos({"secciones": [seccion]}):
        etiqueta = nodo.get(clave_de_etiqueta, "")
        tipo = nodo.get("tipo")
        obligatorio = bool(nodo.get("obligatorio"))

        if tipo == TipoDeDato.RANGO_HORA_INICIO_FIN:
            clave_inicio, clave_fin = claves_de_valor(nodo)
            campos.update(
                _campos_de_rango(clave_inicio, clave_fin, etiqueta, obligatorio)
            )
            continue

        (clave,) = claves_de_valor(nodo)
        campo = _campo_escalar(tipo, nodo.get("opciones"))
        campo.label = etiqueta
        campos[clave] = _marcar_obligatorio(campo, obligatorio)

    return type("FormularioDeSeccion", (forms.Form,), campos)

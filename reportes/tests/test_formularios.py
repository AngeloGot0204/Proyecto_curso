"""Tests for `reportes.formularios.construir_formulario_seccion` (backlog
#5, Phase 3).

Strict TDD: every scenario below is written RED (failing, referencing
production code that does not exist yet) before `reportes/formularios.py`
lands. Covers spec `wizard-captura`, Requirement "One URL and dynamic form
per section" (both scenarios) and design's Type mapping table (D4, D5, D8).
"""

from decimal import Decimal

from django import forms

from reportes.formularios import construir_formulario_seccion
from tipos_reporte.generador import claves_de_valor
from tipos_reporte.validacion import _iterar_nodos


def _seccion_con(campos=None, items=None):
    return {
        "id": "seccion-test",
        "titulo": "Sección de prueba",
        "campos": campos or [],
        "items": items or [],
    }


# --- Scenario: Section renders with correct widgets -------------------------


def test_texto_campo_produce_charfield_con_textinput():
    seccion = _seccion_con(
        campos=[{"id": "obs", "etiqueta": "Observaciones", "tipo": "texto"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    assert "obs" in Formulario.base_fields
    campo = Formulario.base_fields["obs"]
    assert isinstance(campo, forms.CharField)
    assert isinstance(campo.widget, forms.TextInput)
    assert campo.required is False
    assert campo.label == "Observaciones"


def test_numero_campo_produce_decimalfield_con_numberinput():
    seccion = _seccion_con(
        campos=[{"id": "cantidad", "etiqueta": "Cantidad", "tipo": "numero"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["cantidad"]
    assert isinstance(campo, forms.DecimalField)
    assert isinstance(campo.widget, forms.NumberInput)
    assert campo.widget.attrs.get("step") == "any"
    assert campo.localize is False


def test_fecha_campo_produce_datefield_con_dateinput_formato_iso():
    seccion = _seccion_con(
        campos=[{"id": "fecha-inicio", "etiqueta": "Fecha de inicio", "tipo": "fecha"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["fecha-inicio"]
    assert isinstance(campo, forms.DateField)
    assert isinstance(campo.widget, forms.DateInput)
    # Django's `Input.__init__` pops `attrs["type"]` into `self.input_type`
    # (it renders `type` from there, never from `attrs`), so the widget's
    # HTML `type="date"` is asserted through `input_type`, not `attrs`.
    assert campo.widget.input_type == "date"
    assert campo.widget.format == "%Y-%m-%d"


def test_hora_campo_produce_timefield_con_timeinput_formato_hhmm():
    seccion = _seccion_con(
        campos=[{"id": "hora-llegada", "etiqueta": "Hora de llegada", "tipo": "hora"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["hora-llegada"]
    assert isinstance(campo, forms.TimeField)
    assert isinstance(campo.widget, forms.TimeInput)
    assert campo.widget.input_type == "time"
    assert campo.widget.format == "%H:%M"


def test_seleccion_campo_produce_choicefield_con_opcion_vacia_primero():
    seccion = _seccion_con(
        campos=[
            {
                "id": "turno",
                "etiqueta": "Turno",
                "tipo": "seleccion",
                "opciones": ["Día", "Noche"],
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["turno"]
    assert isinstance(campo, forms.ChoiceField)
    assert isinstance(campo.widget, forms.Select)
    assert campo.choices == [("", "—"), ("Día", "Día"), ("Noche", "Noche")]


def test_booleano_campo_produce_booleanfield_con_checkbox():
    seccion = _seccion_con(
        campos=[{"id": "verificado", "etiqueta": "Verificado", "tipo": "booleano"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["verificado"]
    assert isinstance(campo, forms.BooleanField)
    assert isinstance(campo.widget, forms.CheckboxInput)
    assert campo.required is False


def test_rango_hora_inicio_fin_produce_dos_timefields():
    seccion = _seccion_con(
        items=[
            {
                "id": "p-01",
                "texto": "Se verifica ángulo de perforación.",
                "tipo": "rango-hora-inicio-fin",
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    assert set(Formulario.base_fields) == {"p-01_inicio", "p-01_fin"}
    inicio = Formulario.base_fields["p-01_inicio"]
    fin = Formulario.base_fields["p-01_fin"]
    assert isinstance(inicio, forms.TimeField)
    assert isinstance(fin, forms.TimeField)
    assert inicio.widget.format == "%H:%M"
    assert fin.widget.format == "%H:%M"
    assert inicio.label == "Se verifica ángulo de perforación. — Inicio"
    assert fin.label == "Se verifica ángulo de perforación. — Fin"


# --- Scenario: Section with no campos/items still renders -------------------


def test_seccion_sin_campos_ni_items_produce_formulario_sin_campos():
    seccion = _seccion_con()

    Formulario = construir_formulario_seccion(seccion)

    assert Formulario.base_fields == {}


# --- Requirement: Client-side hora range feedback (JS data-attr contract) ---


def test_rango_hora_inicio_fin_agrega_atributos_data_rango():
    seccion = _seccion_con(
        items=[
            {
                "id": "p-01",
                "texto": "Se verifica ángulo de perforación.",
                "tipo": "rango-hora-inicio-fin",
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    inicio = Formulario.base_fields["p-01_inicio"]
    fin = Formulario.base_fields["p-01_fin"]
    assert inicio.widget.attrs.get("data-rango") == "p-01"
    assert inicio.widget.attrs.get("data-rango-extremo") == "inicio"
    assert fin.widget.attrs.get("data-rango") == "p-01"
    assert fin.widget.attrs.get("data-rango-extremo") == "fin"


# --- Requirement: "No cumple" observación toggling (JS data-attr contract) --


def test_seleccion_con_no_cumple_agrega_campo_observacion_companero():
    seccion = _seccion_con(
        campos=[
            {
                "id": "turno",
                "etiqueta": "Turno",
                "tipo": "seleccion",
                "opciones": ["Cumple", "No cumple"],
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    assert "turno_observacion" in Formulario.base_fields
    observacion = Formulario.base_fields["turno_observacion"]
    assert isinstance(observacion, forms.CharField)
    assert observacion.required is False
    assert observacion.label == "Turno — Observación"
    assert observacion.widget.attrs.get("data-observacion-de") == "turno"

    turno = Formulario.base_fields["turno"]
    assert turno.widget.attrs.get("data-requiere-observacion") == "turno_observacion"


def test_seleccion_sin_no_cumple_no_agrega_campo_observacion_companero():
    seccion = _seccion_con(
        campos=[
            {
                "id": "turno",
                "etiqueta": "Turno",
                "tipo": "seleccion",
                "opciones": ["Día", "Noche"],
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    assert "turno_observacion" not in Formulario.base_fields
    turno = Formulario.base_fields["turno"]
    assert "data-requiere-observacion" not in turno.widget.attrs


# --- Requirement: Non-blocking obligatorio marker ---------------------------


def test_campo_obligatorio_agrega_atributo_html_required_pero_sigue_required_false():
    seccion = _seccion_con(
        campos=[
            {
                "id": "turno",
                "etiqueta": "Turno",
                "tipo": "seleccion",
                "opciones": ["Día", "Noche"],
                "obligatorio": True,
            }
        ]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["turno"]
    assert campo.widget.attrs.get("required") is True
    assert campo.required is False


def test_campo_no_obligatorio_no_agrega_atributo_html_required():
    seccion = _seccion_con(
        campos=[{"id": "obs", "etiqueta": "Observaciones", "tipo": "texto"}]
    )

    Formulario = construir_formulario_seccion(seccion)

    campo = Formulario.base_fields["obs"]
    assert "required" not in campo.widget.attrs


# --- Design's Testing Strategy row 5: contract with generador.claves_de_valor


def test_nombres_de_campo_del_formulario_coinciden_con_claves_de_valor():
    seccion = _seccion_con(
        campos=[
            {"id": "turno", "etiqueta": "Turno", "tipo": "seleccion", "opciones": ["Día"]}
        ],
        items=[
            {
                "id": "p-01",
                "texto": "Ítem de rango.",
                "tipo": "rango-hora-inicio-fin",
            }
        ],
    )

    Formulario = construir_formulario_seccion(seccion)

    esperado = set()
    for _ubicacion, nodo, _clave_de_etiqueta in _iterar_nodos({"secciones": [seccion]}):
        esperado.update(claves_de_valor(nodo))

    assert set(Formulario.base_fields) == esperado

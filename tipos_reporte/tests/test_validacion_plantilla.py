"""Template validation tests (Slice 3: R5-R6) plus the two security REDs the
design's Threat Matrix marks as applicable to this change.

Covers spec requirements "Definition names its sheet" and the R5/R6 clauses
of "Exhaustive activation validation (accumulate all errors)": the
associated `.xlsx` template must be readable, its declared `hoja` must
exist, and every destination cell must be the anchor (top-left) cell of its
merged range — verified against a REAL workbook built by the `plantilla_xlsx`
fixture (conftest.py), never a hand-rolled regex.

`validar_contra_plantilla` takes an open binary file object, not a
`FieldFile` (design D5) — tests open the path `plantilla_xlsx` returns
themselves, mirroring how the activation service will call it in Slice 4.

`validar_definicion` is the composer introduced in this slice (design D5):
it runs `validar_estructura` (R1-R4) and `validar_contra_plantilla` (R5-R6)
and never returns early, so a document that fails both groups reports both.

The two security REDs come from the design's Threat Matrix:
- Untrusted deserialization: an uploaded YAML document must never be parsed
  with `yaml.load`'s default loader, which constructs arbitrary Python
  objects from attacker-controlled input. Only `yaml.safe_load` is used.
- Untrusted file parsing: any exception raised while opening/reading the
  `.xlsx` template becomes exactly one `plantilla-ilegible` problem, never
  an uncaught exception.
"""

import io

import pytest
import yaml

from tipos_reporte.validacion import (
    ProblemaDeDefinicion,
    ResultadoDeValidacion,
    analizar_yaml_seguro,
    validar_contra_plantilla,
    validar_definicion,
)


def _reglas(problemas):
    return {p.regla for p in problemas}


# --- Requirement: Definition names its sheet --------------------------------


def test_definicion_sin_hoja_es_rechazada(definicion_valida, plantilla_xlsx):
    """Spec scenario: Definition without a declared sheet is rejected."""
    definicion = definicion_valida()
    del definicion["hoja"]
    destino = plantilla_xlsx()

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "hoja-ausente" in _reglas(problemas)


def test_hoja_declarada_que_no_existe_en_la_plantilla_es_rechazada(
    definicion_valida, plantilla_xlsx
):
    """Spec scenario: Declared sheet that does not exist in the template is
    rejected."""
    definicion = definicion_valida()
    definicion["hoja"] = "REPORTE"
    destino = plantilla_xlsx(nombre_hoja="OTRA-HOJA")

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "hoja-no-encontrada" in _reglas(problemas)
    encontrado = next(p for p in problemas if p.regla == "hoja-no-encontrada")
    assert "REPORTE" in encontrado.mensaje


def test_hoja_declarada_que_existe_pasa(definicion_valida, plantilla_xlsx):
    """Positive counterpart: a `hoja` that exists in the template raises no
    sheet-related problem."""
    definicion = definicion_valida()
    destino = plantilla_xlsx(nombre_hoja="REPORTE")

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "hoja-no-encontrada" not in _reglas(problemas)
    assert "hoja-ausente" not in _reglas(problemas)


# --- Requirement: Exhaustive activation validation — rule 6 (merge anchor) -


def test_celda_ancla_de_rango_combinado_pasa(definicion_valida, plantilla_xlsx):
    """Spec scenario: Anchor cell of a merged range passes."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "M12"
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "celda-no-es-ancla" not in _reglas(problemas)


def test_celda_no_ancla_de_rango_combinado_es_rechazada(
    definicion_valida, plantilla_xlsx
):
    """Spec scenario: Non-anchor cell of a merged range is rejected."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "N12"
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "celda-no-es-ancla" in _reglas(problemas)
    encontrado = next(p for p in problemas if p.regla == "celda-no-es-ancla")
    assert "M12" in encontrado.mensaje


def test_celda_sin_fusion_pasa(definicion_valida, plantilla_xlsx):
    """A cell belonging to no merged range at all is perfectly valid (design
    data flow note)."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "Z40"
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "celda-no-es-ancla" not in _reglas(problemas)


def test_celda_mal_formada_no_se_revisa_contra_el_ancla(
    definicion_valida, plantilla_xlsx
):
    """Design: R6 only considers cells that already passed R3 (notation) —
    feeding a typo to openpyxl would produce a second, derived complaint
    about the same problem."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "1A"
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        problemas = validar_contra_plantilla(definicion, plantilla)

    assert "celda-no-es-ancla" not in _reglas(problemas)


# --- Threat Matrix: untrusted file parsing (.xlsx) --------------------------


def test_plantilla_ilegible_produce_un_unico_problema(definicion_valida):
    """Threat Matrix: any exception opening/reading the `.xlsx` template
    becomes exactly one `plantilla-ilegible` problem, never an uncaught
    exception and never a partial per-cell check."""
    definicion = definicion_valida()
    plantilla_invalida = io.BytesIO(b"esto no es un archivo xlsx valido")

    problemas = validar_contra_plantilla(definicion, plantilla_invalida)

    assert len(problemas) == 1
    assert problemas[0].regla == "plantilla-ilegible"


# --- Composer: ResultadoDeValidacion / validar_definicion -------------------


def test_definicion_completamente_valida_activa_sin_problemas(
    definicion_valida, plantilla_xlsx
):
    """Spec scenario: Fully valid definition activates cleanly — R1-R6
    together report no problems."""
    definicion = definicion_valida()
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        resultado = validar_definicion(definicion, plantilla)

    assert isinstance(resultado, ResultadoDeValidacion)
    assert resultado.es_valida is True
    assert resultado.problemas == ()


def test_composer_acumula_problemas_estructurales_y_de_plantilla(
    definicion_valida, plantilla_xlsx
):
    """Design D5: the composer never returns early — a document that fails
    both an R1-R4 rule AND an R5-R6 rule reports both problem kinds
    together."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["tipo"]  # R1 violation
    definicion["secciones"][1]["items"][0]["celda_inicio"] = "N12"  # R6 violation
    destino = plantilla_xlsx(nombre_hoja="REPORTE", rangos=("M12:P12",))

    with open(destino, "rb") as plantilla:
        resultado = validar_definicion(definicion, plantilla)

    assert resultado.es_valida is False
    assert _reglas(resultado.problemas) == {
        "campo-obligatorio-ausente",
        "celda-no-es-ancla",
    }


def test_composer_reporta_r1_r4_junto_a_plantilla_ilegible(definicion_valida):
    """Design D5: 'If the template cannot be opened at all,
    validar_contra_plantilla returns exactly one problem
    (plantilla-ilegible) and skips per-cell checks — but R1-R4's problems
    are still reported alongside it.' Accumulation survives a hard
    dependency failure instead of collapsing to a single message."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["tipo"]  # R1 violation
    plantilla_invalida = io.BytesIO(b"esto no es un archivo xlsx valido")

    resultado = validar_definicion(definicion, plantilla_invalida)

    assert resultado.es_valida is False
    assert _reglas(resultado.problemas) == {
        "campo-obligatorio-ausente",
        "plantilla-ilegible",
    }


def test_composer_sin_plantilla_solo_ejecuta_r1_r4(definicion_valida):
    """`validar_definicion` accepts `plantilla=None` (design's default) —
    useful whenever a caller only wants the structural pass, e.g. while a
    draft is being edited and no activation is being attempted."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["tipo"]

    resultado = validar_definicion(definicion)

    assert _reglas(resultado.problemas) == {"campo-obligatorio-ausente"}


def test_resultado_de_validacion_es_inmutable():
    """`ResultadoDeValidacion` is a frozen dataclass (design D5), matching
    `ProblemaDeDefinicion`'s own immutability guarantee (Slice 2)."""
    resultado = ResultadoDeValidacion(problemas=())

    with pytest.raises(Exception):
        resultado.problemas = (
            ProblemaDeDefinicion(regla="x", ubicacion="y", mensaje="z"),
        )


# --- Threat Matrix: untrusted deserialization (YAML) ------------------------


def test_yaml_no_confiable_es_rechazado():
    """Threat Matrix: 'A YAML document containing a `!!python/object/apply`
    tag must be rejected, not executed — a genuine behavioural RED.' Only
    `yaml.safe_load` is used (design D4); it has no constructor registered
    for that tag, so it raises instead of instantiating anything."""
    yaml_malicioso = (
        "tipo: !!python/object/apply:os.system ['echo pwned']\n"
    )

    with pytest.raises(yaml.YAMLError):
        analizar_yaml_seguro(yaml_malicioso)


def test_yaml_seguro_es_analizado_normalmente():
    """Positive counterpart: ordinary YAML is parsed into a plain dict."""
    resultado = analizar_yaml_seguro("tipo: instalacion-resinas\nhoja: REPORTE\n")

    assert resultado == {"tipo": "instalacion-resinas", "hoja": "REPORTE"}

"""Structural validation tests (Slice 2: R1-R4).

Covers spec requirement "Exhaustive activation validation (accumulate all
errors)" for the four rules that need no filesystem/openpyxl access, and the
"Closed data-type catalog" requirement. R5-R6 (merged-range anchor, template
readability) and the security RED for untrusted YAML deserialization belong
to Slice 3 and are NOT exercised here (design D5, D6).

`validar_estructura` is a pure function over dicts: no DB, no `TipoDeReporte`
instance, no filesystem — every test here builds a plain dict via the
`definicion_valida` fixture (conftest.py) and mutates its own copy.
"""

import pytest

from tipos_reporte.validacion import ProblemaDeDefinicion, validar_estructura


def _reglas(problemas):
    return {p.regla for p in problemas}


# --- Requirement: Exhaustive activation validation — rule 1 (required keys)


def test_definicion_valida_pasa_sin_problemas(definicion_valida):
    """Fully valid definition: R1-R4 report nothing."""
    problemas = validar_estructura(definicion_valida())

    assert problemas == []


def test_campo_sin_tipo_es_rechazado(definicion_valida):
    """Spec scenario: Missing required field is rejected with an actionable
    message — a campo missing its `tipo` key."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["tipo"]

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)
    encontrado = next(p for p in problemas if p.regla == "campo-obligatorio-ausente")
    assert "secciones[0].campos[0]" in encontrado.ubicacion


def test_campo_sin_celda_es_rechazado(definicion_valida):
    """A campo of a `celda`-keyed type missing `celda` is a missing required
    field too — same rule, different missing key (design D5's per-type R1)."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["celda"]

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)


def test_item_sin_texto_es_rechazado(definicion_valida):
    """An item missing its label key (`texto`, not `etiqueta` — design's
    example distinguishes campos from items) is a missing required field."""
    definicion = definicion_valida()
    del definicion["secciones"][1]["items"][0]["texto"]

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)


def test_item_de_rango_sin_celda_fin_es_rechazado(definicion_valida):
    """`rango-hora-inicio-fin` requires BOTH `celda_inicio` and `celda_fin`
    (design's catalog table) — missing just one is still a violation."""
    definicion = definicion_valida()
    del definicion["secciones"][1]["items"][0]["celda_fin"]

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)


def test_campo_seleccion_sin_opciones_es_rechazado(definicion_valida):
    """`seleccion` requires a non-empty `opciones` list (design's catalog
    table, extra required key)."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["opciones"]

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)


def test_campo_seleccion_con_opciones_vacias_es_rechazado(definicion_valida):
    """An empty `opciones` list is treated the same as a missing one."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["opciones"] = []

    problemas = validar_estructura(definicion)

    assert "campo-obligatorio-ausente" in _reglas(problemas)


# --- Requirement: Closed data-type catalog — rule 2 (known tipo)


def test_campo_con_tipo_reconocido_pasa(definicion_valida):
    """Spec scenario: Field with a recognized type passes the type-check
    rule."""
    definicion = definicion_valida()

    problemas = validar_estructura(definicion)

    assert "tipo-de-dato-desconocido" not in _reglas(problemas)


def test_campo_con_tipo_desconocido_es_rechazado(definicion_valida):
    """Spec scenario: Field with an unknown type is rejected."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["tipo"] = "numero-decimal"

    problemas = validar_estructura(definicion)

    assert "tipo-de-dato-desconocido" in _reglas(problemas)
    encontrado = next(p for p in problemas if p.regla == "tipo-de-dato-desconocido")
    assert "secciones[0].campos[0]" in encontrado.ubicacion


# --- Requirement: Exhaustive activation validation — rule 3 (cell notation)


def test_celda_valida_pasa(definicion_valida):
    """A well-formed Excel-style cell reference passes rule 3."""
    definicion = definicion_valida()

    problemas = validar_estructura(definicion)

    assert "celda-mal-formada" not in _reglas(problemas)


def test_celda_mal_formada_es_rechazada(definicion_valida):
    """Spec scenario: Invalid cell notation is rejected."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "1A"

    problemas = validar_estructura(definicion)

    assert "celda-mal-formada" in _reglas(problemas)
    encontrado = next(p for p in problemas if p.regla == "celda-mal-formada")
    assert "secciones[0].campos[0]" in encontrado.ubicacion


@pytest.mark.parametrize("valor", ["$M$12", "M12:P12", "REPORTE!M12"])
def test_celda_con_referencia_absoluta_rango_u_hoja_es_rechazada(
    definicion_valida, valor
):
    """Design (Interfaces/Contracts): `$`, `:` and `!` are rejected
    explicitly — absolute references, ranges and sheet-qualified references
    are not shapes the generator supports."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = valor

    problemas = validar_estructura(definicion)

    assert "celda-mal-formada" in _reglas(problemas)


# --- Requirement: Exhaustive activation validation — rule 4 (collisions)


def test_celdas_sin_colision_pasan(definicion_valida):
    """Two fields targeting different cells: rule 4 reports nothing."""
    definicion = definicion_valida()

    problemas = validar_estructura(definicion)

    assert "celda-duplicada" not in _reglas(problemas)


def test_colision_de_celda_entre_dos_campos_es_rechazada(definicion_valida):
    """Spec scenario: Cell collision between two fields is rejected."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "M25"
    definicion["secciones"][1]["items"][0]["celda_inicio"] = "M25"

    problemas = validar_estructura(definicion)

    assert "celda-duplicada" in _reglas(problemas)
    ubicaciones = {p.ubicacion for p in problemas if p.regla == "celda-duplicada"}
    assert ubicaciones == {"secciones[0].campos[0]", "secciones[1].items[0]"}


def test_colision_de_celda_entre_celda_inicio_y_celda_de_otro_campo(
    definicion_valida,
):
    """Design (Interfaces/Contracts): R4 collects targets from `celda`,
    `celda_inicio` AND `celda_fin` into one namespace — a `celda_fin`
    colliding with another field's plain `celda` is a real collision."""
    definicion = definicion_valida()
    definicion["secciones"][0]["campos"][0]["celda"] = "P25"
    definicion["secciones"][1]["items"][0]["celda_fin"] = "P25"

    problemas = validar_estructura(definicion)

    assert "celda-duplicada" in _reglas(problemas)


# --- Requirement: Exhaustive activation validation — accumulation ----------


def test_todos_los_problemas_acumulados_se_reportan_en_un_solo_intento(
    definicion_valida,
):
    """Spec scenario: All accumulated errors are reported in one activation
    attempt. Mirrors the design's own accumulation example: a document with
    a missing celda, an unknown tipo, and a cell collision must report all
    three problem kinds together, not just the first one found."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["celda"]
    definicion["secciones"][1]["items"][0]["tipo"] = "numero-decimal"
    # Force a collision independent of the deleted celda above.
    definicion["secciones"][1]["items"][0]["celda_inicio"] = "Z40"
    definicion["secciones"][1]["items"][0]["celda_fin"] = "Z41"
    definicion["secciones"].append(
        {
            "id": "otra-seccion",
            "titulo": "Otra sección",
            "campos": [
                {
                    "id": "otro-campo",
                    "etiqueta": "Otro campo",
                    "tipo": "texto",
                    "celda": "Z40",
                }
            ],
        }
    )

    problemas = validar_estructura(definicion)

    assert _reglas(problemas) == {
        "campo-obligatorio-ausente",
        "tipo-de-dato-desconocido",
        "celda-duplicada",
    }


def test_acumulacion_no_se_detiene_en_el_primer_error(definicion_valida):
    """A first-error-only implementation would pass every individual rule
    test above and fail only this one — the sole mechanical proof that
    accumulation, not short-circuiting, is what actually runs (design D5)."""
    definicion = definicion_valida()
    del definicion["secciones"][0]["campos"][0]["tipo"]
    definicion["secciones"][1]["items"][0]["tipo"] = "numero-decimal"

    problemas = validar_estructura(definicion)

    assert len(problemas) >= 2
    # Sanity: an untouched definition alone reports nothing, proving the two
    # problems above come from the two deliberate mutations, not noise.
    assert validar_estructura(definicion_valida()) == []


def test_problema_de_definicion_es_inmutable():
    """`ProblemaDeDefinicion` is a frozen dataclass (design D5) — its fields
    cannot be reassigned after construction."""
    problema = ProblemaDeDefinicion(
        regla="celda-mal-formada", ubicacion="x", mensaje="y"
    )

    with pytest.raises(Exception):
        problema.regla = "otra-regla"

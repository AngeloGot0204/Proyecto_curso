"""Tests for `reportes.valores` — the string codec between a wizard form's
`cleaned_data` and `ValorDeReporte.valor` (backlog #5, Phase 3, design
D2/D3).

Strict TDD: every scenario below is written RED (failing, referencing
production code that does not exist yet) before `reportes/valores.py`
lands. Covers spec `wizard-captura`'s "Per-step durable persistence" and
"GET rehydration from persisted rows" requirements, and design D2 (codec
round-trip via `campo.to_python`) / D3 (empty deletes; `booleano` always
writes `"true"`/`"false"`).
"""

import datetime
from decimal import Decimal

import pytest
from django import forms

from reportes.models import ValorDeReporte
from reportes.valores import a_texto, desde_texto, guardar_valor, valores_de_reporte


# --- a_texto: serialize cleaned form value to canonical string -------------


def test_a_texto_serializa_str_tal_cual():
    campo = forms.CharField(required=False)
    assert a_texto(campo, "Observación libre") == "Observación libre"


def test_a_texto_serializa_decimal_sin_notacion_exponencial():
    campo = forms.DecimalField(required=False)
    assert a_texto(campo, Decimal("12.50")) == "12.50"
    assert a_texto(campo, Decimal("3")) == "3"


def test_a_texto_serializa_date_en_formato_iso():
    campo = forms.DateField(required=False)
    assert a_texto(campo, datetime.date(2026, 1, 15)) == "2026-01-15"


def test_a_texto_serializa_time_en_formato_hhmm():
    campo = forms.TimeField(required=False)
    assert a_texto(campo, datetime.time(8, 30)) == "08:30"


def test_a_texto_serializa_booleano_true_como_texto_true():
    campo = forms.BooleanField(required=False)
    assert a_texto(campo, True) == "true"


def test_a_texto_serializa_booleano_false_como_texto_false():
    """Design D3: `booleano` ALWAYS writes `"true"`/`"false"` — a `False`
    checkbox is a provided value, distinct from `bool` being a subclass of
    `int` (must not become `"0"`)."""
    campo = forms.BooleanField(required=False)
    assert a_texto(campo, False) == "false"


# --- desde_texto: rehydrate via campo.to_python(texto) ----------------------


def test_desde_texto_rehidrata_decimal_via_to_python():
    campo = forms.DecimalField(required=False)
    assert desde_texto(campo, "12.50") == Decimal("12.50")


def test_desde_texto_rehidrata_date_via_to_python():
    campo = forms.DateField(required=False)
    assert desde_texto(campo, "2026-01-15") == datetime.date(2026, 1, 15)


def test_desde_texto_rehidrata_time_via_to_python():
    campo = forms.TimeField(required=False)
    assert desde_texto(campo, "08:30") == datetime.time(8, 30)


def test_desde_texto_rehidrata_booleano_false_desde_texto_false():
    campo = forms.BooleanField(required=False)
    assert desde_texto(campo, "false") is False


def test_desde_texto_rehidrata_booleano_true_desde_texto_true():
    campo = forms.BooleanField(required=False)
    assert desde_texto(campo, "true") is True


# --- guardar_valor: empty deletes; non-empty upserts (design D3) -----------


@pytest.mark.django_db
def test_guardar_valor_none_elimina_la_fila_existente(reporte_factory):
    reporte = reporte_factory()
    usuario = reporte.creador
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="obs", valor="algo", autor=usuario
    )

    guardar_valor(reporte, "obs", None, usuario)

    assert not ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="obs"
    ).exists()


@pytest.mark.django_db
def test_guardar_valor_cadena_vacia_elimina_la_fila_existente(reporte_factory):
    """Design D3's central invariant: `generador._validar_completitud` uses
    a *membership* test, so an `""` row would silently satisfy an
    `obligatorio` field. An empty submitted value must delete, not persist
    empty."""
    reporte = reporte_factory()
    usuario = reporte.creador
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="turno", valor="Día", autor=usuario
    )

    guardar_valor(reporte, "turno", "", usuario)

    assert not ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="turno"
    ).exists()


@pytest.mark.django_db
def test_guardar_valor_none_sin_fila_existente_no_falla(reporte_factory):
    reporte = reporte_factory()
    usuario = reporte.creador

    guardar_valor(reporte, "obs", None, usuario)

    assert not ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="obs"
    ).exists()


@pytest.mark.django_db
def test_guardar_valor_no_vacio_crea_la_fila_con_valor_serializado(reporte_factory):
    reporte = reporte_factory()
    usuario = reporte.creador

    guardar_valor(reporte, "cantidad", Decimal("7"), usuario)

    fila = ValorDeReporte.objects.get(reporte=reporte, identificador_de_campo="cantidad")
    assert fila.valor == "7"
    assert fila.autor_id == usuario.id


@pytest.mark.django_db
def test_guardar_valor_no_vacio_actualiza_fila_existente_sin_duplicar(reporte_factory):
    """Design's Testing Strategy: "POST upserts (no duplicate rows on
    re-POST)"."""
    reporte = reporte_factory()
    usuario = reporte.creador
    guardar_valor(reporte, "obs", "primer valor", usuario)

    guardar_valor(reporte, "obs", "segundo valor", usuario)

    filas = ValorDeReporte.objects.filter(reporte=reporte, identificador_de_campo="obs")
    assert filas.count() == 1
    assert filas.get().valor == "segundo valor"


@pytest.mark.django_db
def test_guardar_valor_booleano_false_persiste_fila_con_texto_false(reporte_factory):
    """Design D3: an unchecked `booleano` is a PROVIDED `False`, not an
    empty value — it must persist a `"false"` row, never delete/skip it."""
    reporte = reporte_factory()
    usuario = reporte.creador

    guardar_valor(reporte, "verificado", False, usuario)

    fila = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="verificado"
    )
    assert fila.valor == "false"


# --- valores_de_reporte: shared dict-builder (design D5) -------------------


@pytest.mark.django_db
def test_valores_de_reporte_construye_dict_desde_filas(reporte_factory):
    """Design D5: `valores_de_reporte` builds the same
    `{identificador_de_campo: valor}` dict that `validar_reporte` and
    `paso` each built inline before the refactor."""
    reporte = reporte_factory()
    usuario = reporte.creador
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="turno", valor="Día", autor=usuario
    )
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="observaciones-generales",
        valor="Todo en orden.",
        autor=usuario,
    )

    resultado = valores_de_reporte(reporte)

    assert resultado == {
        "turno": "Día",
        "observaciones-generales": "Todo en orden.",
    }


@pytest.mark.django_db
def test_valores_de_reporte_reporte_vacio_retorna_dict_vacio(reporte_factory):
    """A `Reporte` with no persisted `ValorDeReporte` rows produces `{}` —
    the empty result must come from a real, empty queryset, not a hardcoded
    stub (proven by the non-empty companion test above)."""
    reporte = reporte_factory()

    resultado = valores_de_reporte(reporte)

    assert resultado == {}

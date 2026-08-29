"""Test for the `reporte_listo_para_cerrar` fixture added to
`reportes/tests/conftest.py` (backlog #7, task 3.2, design's Testing
Strategy). Deferred from PR 1 to PR 2 (`cerrar_reporte` work unit).

Strict TDD: written RED (referencing a fixture that does not exist yet)
before the fixture lands in `conftest.py`.
"""

import pytest

from reportes.models import ValorDeReporte
from reportes.validacion import validar_reporte


@pytest.mark.django_db
def test_reporte_listo_para_cerrar_es_elegible_para_generar(
    reporte_listo_para_cerrar,
):
    client, reporte = reporte_listo_para_cerrar

    resultado = validar_reporte(reporte)

    assert resultado.puede_generar is True
    assert resultado.errores == ()
    assert (
        ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo="observaciones-generales"
        ).get().valor
        == "Todo en orden."
    )
    assert (
        ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo="estado-general"
        ).get().valor
        == "Cumple"
    )
    assert client.session.get("_auth_user_id") is not None
    assert int(client.session["_auth_user_id"]) == reporte.creador_id

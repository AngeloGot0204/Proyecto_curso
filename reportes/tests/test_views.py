"""Integration tests for the wizard-captura views (backlog #5, Phase 4;
design D7, D8, D9; specs `wizard-captura` and `reportes-modelo`).

`test_post_nuevo_*` / `test_get_nuevo_*` cover design D7 (`POST
/reportes/<codigo>/nuevo/` creates the `Reporte`, `require_POST`,
`login_required`). `test_*_paso_*` cover GET rehydration, POST upsert (no
duplicate rows on re-POST), the creator-only 404 (D9), the unknown-
`seccion_id` 404, and the non-blocking `obligatorio` marker (spec:
Non-blocking obligatorio marker).
"""

from io import BytesIO
from unittest import mock

import pytest
from django.contrib.messages import get_messages
from django.template.loader import render_to_string
from django.urls import reverse
from openpyxl import load_workbook

from reportes.models import EstadoDeReporte, Generacion, Reporte, ValorDeReporte, VistoBueno
from reportes.validacion import validar_reporte
from tipos_reporte.generador import PlantillaIlegible


@pytest.fixture
def sesion_de_creador(client, usuario_factory, reporte_factory):
    """A `(client, reporte)` pair where the logged-in user IS the `Reporte`'s
    `creador` — needed for every test exercising the happy path through
    `paso`, since `reporte_factory`'s default creador is otherwise an
    unrelated, freshly-made usuario."""
    creador = usuario_factory(username="creador_del_reporte")
    reporte = reporte_factory(creador=creador)
    client.force_login(creador)
    return client, reporte


# ---------------------------------------------------------------------------
# iniciar_reporte
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_nuevo_crea_un_reporte(cliente_autenticado, tipo_con_definicion_activa_factory):
    tipo, definicion = tipo_con_definicion_activa_factory()

    response = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo.codigo])
    )

    assert Reporte.objects.count() == 1
    reporte = Reporte.objects.get()
    assert reporte.tipo_id == tipo.id
    assert reporte.definicion_id == definicion.id
    assert response.status_code == 302
    primera_seccion = definicion.estructura["secciones"][0]["id"]
    assert response.url == reverse(
        "reportes_paso", args=[reporte.id, primera_seccion]
    )


@pytest.mark.django_db
def test_get_nuevo_no_permitido(cliente_autenticado, tipo_con_definicion_activa_factory):
    tipo, _definicion = tipo_con_definicion_activa_factory()

    response = cliente_autenticado.get(reverse("reportes_nuevo", args=[tipo.codigo]))

    assert response.status_code == 405
    assert Reporte.objects.count() == 0


@pytest.mark.django_db
def test_nuevo_anonimo_redirige_a_login(client, tipo_con_definicion_activa_factory):
    tipo, _definicion = tipo_con_definicion_activa_factory()

    response = client.post(reverse("reportes_nuevo", args=[tipo.codigo]))

    assert response.status_code == 302
    assert reverse("login") in response.url
    assert Reporte.objects.count() == 0


# ---------------------------------------------------------------------------
# paso — GET rehydration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_paso_rehidrata_valores_guardados(sesion_de_creador):
    client, reporte = sesion_de_creador
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="turno",
        valor="Día",
        autor=reporte.creador,
    )

    response = client.get(reverse("reportes_paso", args=[reporte.id, "datos-generales"]))

    assert response.status_code == 200
    assert response.context["form"].initial.get("turno") == "Día"


@pytest.mark.django_db
def test_paso_anonimo_redirige_a_login(client, reporte_factory):
    reporte = reporte_factory()

    response = client.get(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"])
    )

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_paso_reporte_de_otro_usuario_da_404(
    cliente_autenticado, usuario_factory, reporte_factory
):
    # A distinct usuario than the one `cliente_autenticado` logged in
    # (design D9) — `usuario_factory`'s default username collides with
    # `cliente_autenticado`'s own default user otherwise.
    otro_creador = usuario_factory(username="otro_usuario")
    reporte = reporte_factory(creador=otro_creador)

    response = cliente_autenticado.get(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_paso_seccion_desconocida_da_404(sesion_de_creador):
    client, reporte = sesion_de_creador

    response = client.get(
        reverse("reportes_paso", args=[reporte.id, "seccion-inexistente"])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_get_paso_seccion_vacia_renderiza_sin_error(
    client, usuario_factory, tipo_con_definicion_activa_factory
):
    """Spec: "Section with no campos/items still renders" — the step shell
    must render without error, showing zero fields, and still expose next-
    step navigation."""
    estructura = {
        "secciones": [
            {"id": "vacia", "titulo": "Sección vacía", "campos": []},
            {"id": "siguiente", "titulo": "Siguiente", "campos": []},
        ]
    }
    tipo, definicion = tipo_con_definicion_activa_factory(estructura=estructura)
    creador = usuario_factory(username="creador_seccion_vacia")
    client.force_login(creador)

    from reportes.models import Reporte

    reporte = Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=creador
    )

    response = client.get(reverse("reportes_paso", args=[reporte.id, "vacia"]))

    assert response.status_code == 200
    assert list(response.context["form"].fields) == []
    assert response.context["url_siguiente"] == reverse(
        "reportes_paso", args=[reporte.id, "siguiente"]
    )


# ---------------------------------------------------------------------------
# paso — POST upsert
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_paso_persiste_valores(sesion_de_creador):
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={"turno": "Noche"},
    )

    assert response.status_code == 302
    valor = ValorDeReporte.objects.get(reporte=reporte, identificador_de_campo="turno")
    assert valor.valor == "Noche"


@pytest.mark.django_db
def test_post_paso_repetido_no_duplica_fila(sesion_de_creador):
    client, reporte = sesion_de_creador

    client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={"turno": "Día"},
    )
    client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={"turno": "Noche"},
    )

    assert (
        ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo="turno"
        ).count()
        == 1
    )
    valor = ValorDeReporte.objects.get(reporte=reporte, identificador_de_campo="turno")
    assert valor.valor == "Noche"


@pytest.mark.django_db
def test_post_paso_rango_hora_inicio_fin_persiste_dos_filas(sesion_de_creador):
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "proceso-instalacion"]),
        data={"p-01_inicio": "08:00", "p-01_fin": "10:00"},
    )

    assert response.status_code == 302
    inicio = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="p-01_inicio"
    )
    fin = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="p-01_fin"
    )
    assert inicio.valor == "08:00"
    assert fin.valor == "10:00"


@pytest.mark.django_db
def test_post_paso_ultima_seccion_redirige_a_si_misma(sesion_de_creador):
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "proceso-instalacion"]),
        data={},
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "reportes_paso", args=[reporte.id, "proceso-instalacion"]
    )


@pytest.mark.django_db
def test_post_paso_no_ultima_seccion_redirige_a_siguiente(sesion_de_creador):
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={"turno": "Día"},
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "reportes_paso", args=[reporte.id, "proceso-instalacion"]
    )


# ---------------------------------------------------------------------------
# paso — client-side JS contract (backlog validacion-datos-formulario, Phase 5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_paso_incluye_atributos_data_y_script_paso_js(
    client, estructura_con_validaciones, reporte_con_validaciones_factory
):
    """GET `paso` HTML must carry the JS contract's data attributes plus a
    deferred `paso.js` script tag (spec: "Client-side hora range feedback",
    "\"No cumple\" observación toggling"; design's `paso.html`/`paso.js`
    File Changes rows and "the JS contract" subsection). No JS test runner
    exists in this project, so this rendered-attribute contract is the only
    coverage for `paso.js` (design's Testing Strategy, explicitly
    accepted)."""
    reporte = reporte_con_validaciones_factory(client, estructura_con_validaciones)

    respuesta_datos = client.get(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"])
    )
    contenido_datos = respuesta_datos.content.decode()

    assert respuesta_datos.status_code == 200
    assert 'data-campo="observaciones-generales"' in contenido_datos
    assert 'data-campo="estado-general"' in contenido_datos
    assert 'data-campo="estado-general_observacion"' in contenido_datos
    assert 'data-requiere-observacion="estado-general_observacion"' in contenido_datos
    assert "data-siguiente" in contenido_datos
    assert 'reportes/paso.js"' in contenido_datos
    assert " defer" in contenido_datos

    respuesta_proceso = client.get(
        reverse("reportes_paso", args=[reporte.id, "proceso-instalacion"])
    )
    contenido_proceso = respuesta_proceso.content.decode()

    assert respuesta_proceso.status_code == 200
    assert 'data-campo="p-01_inicio"' in contenido_proceso
    assert 'data-campo="p-01_fin"' in contenido_proceso
    assert 'data-rango="p-01"' in contenido_proceso


# ---------------------------------------------------------------------------
# revision (S-09 review screen; spec `validacion-reporte`)
# ---------------------------------------------------------------------------


@pytest.fixture
def reporte_con_validaciones_factory(
    usuario_factory, tipo_con_definicion_activa_factory, reporte_factory
):
    """Build a `Reporte` whose `estructura` is `estructura_con_validaciones`
    (spec scenarios 1-6), owned by a fresh creador. Returns `(client,
    reporte)` with the creador already logged in — mirrors
    `sesion_de_creador` but lets each `revision` test choose its own
    persisted `ValorDeReporte` rows."""

    def _crear(client, estructura_con_validaciones):
        tipo, definicion = tipo_con_definicion_activa_factory(
            estructura=estructura_con_validaciones()
        )
        creador = usuario_factory(username="creador_de_revision")
        reporte = reporte_factory(tipo=tipo, definicion=definicion, creador=creador)
        client.force_login(creador)
        return reporte

    return _crear


@pytest.mark.django_db
def test_get_revision_como_creador_lista_errores_y_advertencias(
    client, estructura_con_validaciones, reporte_con_validaciones_factory, usuario_factory
):
    reporte = reporte_con_validaciones_factory(client, estructura_con_validaciones)
    autor = usuario_factory(username="autor-de-valores-revision")
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="observaciones-generales",
        valor="Todo en orden.",
        autor=autor,
    )
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="estado-general",
        valor="No cumple",
        autor=autor,
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="p-01_inicio", valor="09:00", autor=autor
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="p-01_fin", valor="08:00", autor=autor
    )
    # "estado-general" obligatorio filled, but as "No cumple" with no
    # observación (advertencia) and a stray hora range (advertencia). No
    # errores expected here since every obligatorio is present.

    response = client.get(reverse("reportes_revision", args=[reporte.id]))

    assert response.status_code == 200
    resultado = response.context["resultado"]
    assert resultado.errores == ()
    assert len(resultado.advertencias) == 2


@pytest.mark.django_db
def test_get_revision_reporte_de_otro_usuario_da_404(
    cliente_autenticado, usuario_factory, reporte_factory
):
    otro_creador = usuario_factory(username="otro_usuario_revision")
    reporte = reporte_factory(creador=otro_creador)

    response = cliente_autenticado.get(reverse("reportes_revision", args=[reporte.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_get_revision_anonimo_redirige_a_login(client, reporte_factory):
    reporte = reporte_factory()

    response = client.get(reverse("reportes_revision", args=[reporte.id]))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_get_revision_con_errores_deshabilita_generar(
    client, estructura_con_validaciones, reporte_con_validaciones_factory
):
    # No `ValorDeReporte` rows persisted at all — every obligatorio is
    # missing, so `errores` is non-empty (spec: "Errores present disables
    # Generar").
    reporte = reporte_con_validaciones_factory(client, estructura_con_validaciones)

    response = client.get(reverse("reportes_revision", args=[reporte.id]))

    assert response.status_code == 200
    assert response.context["resultado"].errores != ()
    assert "disabled" in response.content.decode()


@pytest.mark.django_db
def test_get_revision_sin_errores_habilita_generar(
    client, estructura_con_validaciones, reporte_con_validaciones_factory, usuario_factory
):
    reporte = reporte_con_validaciones_factory(client, estructura_con_validaciones)
    autor = usuario_factory(username="autor-sin-errores")
    ValorDeReporte.objects.create(
        reporte=reporte,
        identificador_de_campo="observaciones-generales",
        valor="Todo en orden.",
        autor=autor,
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="estado-general", valor="Cumple", autor=autor
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="p-01_inicio", valor="08:00", autor=autor
    )
    ValorDeReporte.objects.create(
        reporte=reporte, identificador_de_campo="p-01_fin", valor="09:00", autor=autor
    )

    response = client.get(reverse("reportes_revision", args=[reporte.id]))

    assert response.status_code == 200
    assert response.context["resultado"].errores == ()
    assert "disabled" not in response.content.decode()


@pytest.mark.django_db
def test_post_paso_sin_valor_obligatorio_no_bloquea(sesion_de_creador):
    """Non-blocking obligatorio marker: submitting without a value for a
    field marked `obligatorio` must NOT return a validation error, and the
    other submitted values must still be persisted (spec scenario "Missing
    obligatorio field does not block persistence")."""
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={"turno": ""},
    )

    assert response.status_code == 302
    assert not ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="turno"
    ).exists()


@pytest.mark.django_db
def test_post_paso_con_rango_invalido_no_bloquea(sesion_de_creador):
    """Server-side non-blocking hora range re-check (spec: "Direct POST
    with invalid hora range still persists"): a stray `fin <= inicio` POST
    must still upsert both values and must NOT be blocked server-side —
    the design decision routes the actual check through `validar_reporte`
    at the S-09 gate, not through `paso`'s POST handler, so this test
    proves the existing non-blocking POST contract already covers it
    without any new server-side branch."""
    client, reporte = sesion_de_creador

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "proceso-instalacion"]),
        data={"p-01_inicio": "10:00", "p-01_fin": "08:00"},
    )

    assert response.status_code == 302
    inicio = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="p-01_inicio"
    )
    fin = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="p-01_fin"
    )
    assert inicio.valor == "10:00"
    assert fin.valor == "08:00"


# ---------------------------------------------------------------------------
# cerrar_reporte (backlog #7, task 4; spec `cierre-reporte`; design D2, D9)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cerrar_reporte_no_creador_devuelve_404(
    cliente_autenticado, usuario_factory, reporte_factory
):
    otro_creador = usuario_factory(username="otro_creador_cierre")
    reporte = reporte_factory(creador=otro_creador)

    response = cliente_autenticado.post(
        reverse("reportes_cerrar", args=[reporte.id])
    )

    assert response.status_code == 404
    assert not VistoBueno.objects.filter(reporte=reporte).exists()


@pytest.mark.django_db
def test_cerrar_reporte_rechazado_si_no_puede_generar(
    client, estructura_con_validaciones, reporte_con_validaciones_factory
):
    # No `ValorDeReporte` rows persisted — every obligatorio is missing, so
    # `puede_generar` is False.
    reporte = reporte_con_validaciones_factory(client, estructura_con_validaciones)

    response = client.post(reverse("reportes_cerrar", args=[reporte.id]))

    assert not VistoBueno.objects.filter(reporte=reporte).exists()
    reporte.refresh_from_db()
    assert reporte.estado == EstadoDeReporte.EN_PROGRESO


@pytest.mark.django_db
def test_cerrar_reporte_creador_exitoso(reporte_listo_para_cerrar):
    client, reporte = reporte_listo_para_cerrar

    response = client.post(reverse("reportes_cerrar", args=[reporte.id]))

    assert VistoBueno.objects.filter(
        reporte=reporte, usuario=reporte.creador
    ).exists()
    reporte.refresh_from_db()
    assert reporte.estado == EstadoDeReporte.TERMINADO
    assert response.status_code == 302
    assert response.url == reverse("reportes_revision", args=[reporte.id])


@pytest.mark.django_db
def test_cerrar_reporte_doble_post_es_idempotente(reporte_listo_para_cerrar):
    client, reporte = reporte_listo_para_cerrar

    primera = client.post(reverse("reportes_cerrar", args=[reporte.id]))
    segunda = client.post(reverse("reportes_cerrar", args=[reporte.id]))

    assert primera.status_code == 302
    assert segunda.status_code == 302
    assert VistoBueno.objects.filter(reporte=reporte).count() == 1
    mensajes_segunda = list(get_messages(segunda.wsgi_request))
    assert any(mensaje.level_tag == "success" for mensaje in mensajes_segunda)


# ---------------------------------------------------------------------------
# generar (backlog #7, task 5; spec `generacion-documento`; design D3, D6)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_generar_sin_visto_bueno_redirige_con_error(reporte_listo_para_cerrar):
    # `reporte_listo_para_cerrar` is eligible but never closed — no
    # `VistoBueno` row exists yet (spec: "Generation attempted before
    # closure").
    client, reporte = reporte_listo_para_cerrar

    response = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert response.status_code == 302
    assert response.url == reverse("reportes_revision", args=[reporte.id])
    assert not Generacion.objects.filter(reporte=reporte).exists()
    mensajes = list(get_messages(response.wsgi_request))
    assert any(mensaje.level_tag == "error" for mensaje in mensajes)


@pytest.mark.django_db
def test_generar_rechazado_si_no_puede_generar_pese_a_visto_bueno(
    reporte_listo_para_cerrar,
):
    # `VistoBueno` exists, but a later edit made the report ineligible
    # again (spec: "Generation rejected when no longer eligible").
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))
    ValorDeReporte.objects.filter(
        reporte=reporte, identificador_de_campo="observaciones-generales"
    ).delete()

    response = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert response.status_code == 302
    assert response.url == reverse("reportes_revision", args=[reporte.id])
    assert not Generacion.objects.filter(reporte=reporte).exists()
    mensajes = list(get_messages(response.wsgi_request))
    assert any(mensaje.level_tag == "error" for mensaje in mensajes)


@pytest.mark.django_db
def test_generar_no_creador_tambien_puede_generar(
    reporte_listo_para_cerrar, usuario_factory
):
    # Spec: "Any Authenticated User May Generate" — non-creator user B
    # succeeds once the report is closed.
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))
    client.logout()
    otro = usuario_factory(username="usuario-no-creador-generar")
    client.force_login(otro)

    response = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert response.status_code == 200
    generacion = Generacion.objects.get(reporte=reporte)
    assert generacion.usuario == otro


@pytest.mark.django_db
def test_generar_captura_problema_de_generacion_y_redirige(reporte_listo_para_cerrar):
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))

    with mock.patch(
        "reportes.views.generador.generar_reporte",
        side_effect=PlantillaIlegible("plantilla rota"),
    ):
        response = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert response.status_code == 302
    assert response.url == reverse("reportes_revision", args=[reporte.id])
    assert not Generacion.objects.filter(reporte=reporte).exists()
    mensajes = list(get_messages(response.wsgi_request))
    assert any(mensaje.level_tag == "error" for mensaje in mensajes)


@pytest.mark.django_db
def test_generar_exitoso_streamea_xlsx_con_headers_correctos(
    reporte_listo_para_cerrar,
):
    from django.utils import timezone

    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))

    response = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    esperado = (
        f"{reporte.tipo.codigo}-{reporte.id}-{timezone.localdate():%Y%m%d}.xlsx"
    )
    assert response["Content-Disposition"] == f'attachment; filename="{esperado}"'
    libro = load_workbook(BytesIO(response.content))
    assert libro.sheetnames == ["REPORTE"]
    assert libro["REPORTE"]["M10"].value == "Todo en orden."
    assert libro["REPORTE"]["M25"].value == "08:00"


@pytest.mark.django_db
def test_generar_repetido_crea_multiples_filas_generacion(reporte_listo_para_cerrar):
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))

    primera = client.post(reverse("reportes_generar", args=[reporte.id]))
    segunda = client.post(reverse("reportes_generar", args=[reporte.id]))

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert Generacion.objects.filter(reporte=reporte).count() == 2


# ---------------------------------------------------------------------------
# Template & messages wiring (backlog #7, task 6; design D4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_revision_con_visto_bueno_muestra_form_generar(reporte_listo_para_cerrar):
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))

    response = client.get(reverse("reportes_revision", args=[reporte.id]))
    contenido = response.content.decode()

    assert response.status_code == 200
    assert f'action="{reverse("reportes_generar", args=[reporte.id])}"' in contenido
    assert "csrfmiddlewaretoken" in contenido
    assert "<form" in contenido


@pytest.mark.django_db
def test_get_revision_no_creador_no_ve_boton_cerrar(
    reporte_listo_para_cerrar, usuario_factory, rf
):
    _client, reporte = reporte_listo_para_cerrar
    otro = usuario_factory(username="otro-no-creador-revision")
    request = rf.get(reverse("reportes_revision", args=[reporte.id]))
    request.user = otro

    resultado = validar_reporte(reporte)
    contenido = render_to_string(
        "reportes/revision.html",
        {"reporte": reporte, "resultado": resultado, "tiene_visto_bueno": False},
        request=request,
    )

    assert "Cerrar reporte" not in contenido


@pytest.mark.django_db
def test_edicion_post_cierre_sigue_funcionando(reporte_listo_para_cerrar):
    # Spec `cierre-reporte`: "Editing a value after closure succeeds" —
    # `paso` stays fully open even once `estado == TERMINADO`.
    client, reporte = reporte_listo_para_cerrar
    client.post(reverse("reportes_cerrar", args=[reporte.id]))
    reporte.refresh_from_db()
    assert reporte.estado == EstadoDeReporte.TERMINADO

    response = client.post(
        reverse("reportes_paso", args=[reporte.id, "datos-generales"]),
        data={
            "observaciones-generales": "Actualizado tras cierre.",
            "estado-general": "Cumple",
        },
    )

    assert response.status_code == 302
    valor = ValorDeReporte.objects.get(
        reporte=reporte, identificador_de_campo="observaciones-generales"
    )
    assert valor.valor == "Actualizado tras cierre."

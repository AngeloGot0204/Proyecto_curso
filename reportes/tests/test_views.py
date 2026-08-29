"""Integration tests for the wizard-captura views (backlog #5, Phase 4;
design D7, D8, D9; specs `wizard-captura` and `reportes-modelo`).

`test_post_nuevo_*` / `test_get_nuevo_*` cover design D7 (`POST
/reportes/<codigo>/nuevo/` creates the `Reporte`, `require_POST`,
`login_required`). `test_*_paso_*` cover GET rehydration, POST upsert (no
duplicate rows on re-POST), the creator-only 404 (D9), the unknown-
`seccion_id` 404, and the non-blocking `obligatorio` marker (spec:
Non-blocking obligatorio marker).
"""

import pytest
from django.urls import reverse

from reportes.models import Reporte, ValorDeReporte


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

"""Tests for `Reporte.id_local`/`numero_registro` and idempotent
`iniciar_reporte` (change `sincronizacion-numero-registro`; design D1-D3,
D8; specs `reporte-idempotent-creation`).

Model-level scenarios (1-5) prove the Postgres `db_default` machinery
(`RETURNING`, sequence monotonicity, uniqueness) without going through the
view. View-level scenarios (6-10, 12) prove `iniciar_reporte`'s
`get_or_create(id_local=..., creador=...)` idempotency contract, including
the hostile-reuse and session-expiry cases design D3 calls out.
"""

import uuid

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from reportes.models import Reporte

# ---------------------------------------------------------------------------
# Model-level: id_local / numero_registro DB defaults (design D1, D2)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_asigna_numero_registro_sin_refresh(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Scenario 1: `create()` returns an instance whose `numero_registro`
    is already set, without `refresh_from_db()` — proves Django's
    `INSERT ... RETURNING` fires for a `db_default` column (design D1)."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()

    reporte = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)

    assert reporte.numero_registro is not None


@pytest.mark.django_db
def test_numero_registro_avanza_por_secuencia(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Scenario 2: two consecutive creates get strictly increasing
    `numero_registro` values (gaps from rolled-back transactions are
    expected — the assertion is `>`, never `== +1`)."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()

    primero = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)
    segundo = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)

    assert segundo.numero_registro > primero.numero_registro


@pytest.mark.django_db
def test_numero_registro_es_unico(usuario_factory, tipo_con_definicion_activa_factory):
    """Scenario 3: manually forcing a duplicate `numero_registro` raises
    `IntegrityError` — the DB `unique=True` constraint is real, not just a
    Django-level check."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()
    primero = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Reporte.objects.create(
                tipo=tipo,
                definicion=definicion,
                creador=usuario,
                numero_registro=primero.numero_registro,
            )


@pytest.mark.django_db
def test_id_local_unico_a_nivel_bd(usuario_factory, tipo_con_definicion_activa_factory):
    """Scenario 4: two `Reporte`s sharing the same `id_local` raise
    `IntegrityError` (design D2/D3's DB-level uniqueness backstop)."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()
    compartido = uuid.uuid4()
    Reporte.objects.create(
        tipo=tipo, definicion=definicion, creador=usuario, id_local=compartido
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Reporte.objects.create(
                tipo=tipo,
                definicion=definicion,
                creador=usuario,
                id_local=compartido,
            )


@pytest.mark.django_db
def test_id_local_por_defecto_es_distinto_por_fila(
    usuario_factory, tipo_con_definicion_activa_factory
):
    """Scenario 5: two DB-default creates (no explicit `id_local`) get
    different UUIDs — proves `gen_random_uuid()` is volatile per-row, not a
    single Python-level default shared across INSERTs."""
    usuario = usuario_factory()
    tipo, definicion = tipo_con_definicion_activa_factory()

    primero = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)
    segundo = Reporte.objects.create(tipo=tipo, definicion=definicion, creador=usuario)

    assert primero.id_local != segundo.id_local


# ---------------------------------------------------------------------------
# View-level: iniciar_reporte idempotency (design D3, D8)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_nuevo_repetido_mismo_id_local_no_duplica(
    cliente_autenticado, tipo_con_definicion_activa_factory
):
    """Scenario 6: the same `id_local` POSTed twice by the same user
    creates exactly one `Reporte`, with an identical redirect `Location`
    and identical `numero_registro` on both responses."""
    tipo, _definicion = tipo_con_definicion_activa_factory()
    id_local = str(uuid.uuid4())

    primera = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )
    segunda = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )

    assert Reporte.objects.count() == 1
    assert primera.status_code == 302
    assert segunda.status_code == 302
    assert primera.url == segunda.url
    reporte = Reporte.objects.get()
    assert reporte.numero_registro is not None


@pytest.mark.django_db
def test_post_nuevo_sin_id_local_sigue_funcionando(
    cliente_autenticado, tipo_con_definicion_activa_factory
):
    """Scenario 7: backwards compatibility — a POST with no `id_local`
    (existing non-JS callers) still creates a `Reporte` normally, getting
    a server-generated `id_local` as the fallback (design's Interfaces)."""
    tipo, _definicion = tipo_con_definicion_activa_factory()

    response = cliente_autenticado.post(reverse("reportes_nuevo", args=[tipo.codigo]))

    assert response.status_code == 302
    assert Reporte.objects.count() == 1
    reporte = Reporte.objects.get()
    assert reporte.id_local is not None


@pytest.mark.django_db
def test_id_local_invalido_devuelve_400(
    cliente_autenticado, tipo_con_definicion_activa_factory
):
    """Scenario 8: a syntactically invalid `id_local` (not a UUID) is
    rejected with 400 and creates nothing."""
    tipo, _definicion = tipo_con_definicion_activa_factory()

    response = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": "no-es-un-uuid"}
    )

    assert response.status_code == 400
    assert Reporte.objects.count() == 0


@pytest.mark.django_db
def test_id_local_de_otro_usuario_devuelve_400(
    cliente_autenticado, usuario_factory, tipo_con_definicion_activa_factory
):
    """Scenario 9: hostile reuse — user B POSTs the `id_local` already
    owned by user A. `creador` is part of the `get_or_create` lookup
    (design D3), so it falls through to `create()`, and the global unique
    constraint on `id_local` turns that into a 400 instead of silently
    handing B access to A's `Reporte`."""
    tipo, _definicion = tipo_con_definicion_activa_factory()
    usuario_a = usuario_factory(username="usuario_a")
    id_local = str(uuid.uuid4())
    Reporte.objects.create(
        tipo=tipo,
        definicion=tipo.definicion_activa,
        creador=usuario_a,
        id_local=id_local,
    )

    response = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )

    assert response.status_code == 400
    assert Reporte.objects.count() == 1


@pytest.mark.django_db
def test_id_local_de_otro_tipo_devuelve_400(
    cliente_autenticado, tipo_con_definicion_activa_factory
):
    """Scenario 10: the same user reuses an `id_local` that already
    belongs to a `Reporte` of a DIFFERENT `TipoDeReporte` — `get_or_create`
    matches on `(id_local, creador)` alone, so this returns the EXISTING
    row; the view must independently reject it (`tipo_id` mismatch) with
    400, rather than silently returning a `Reporte` of the wrong type."""
    tipo_a, _definicion_a = tipo_con_definicion_activa_factory(
        nombre="Tipo A", codigo="tipo-a"
    )
    tipo_b, _definicion_b = tipo_con_definicion_activa_factory(
        nombre="Tipo B", codigo="tipo-b"
    )
    id_local = str(uuid.uuid4())
    primera = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo_a.codigo]), {"id_local": id_local}
    )
    assert primera.status_code == 302

    segunda = cliente_autenticado.post(
        reverse("reportes_nuevo", args=[tipo_b.codigo]), {"id_local": id_local}
    )

    assert segunda.status_code == 400
    assert Reporte.objects.count() == 1


@pytest.mark.django_db
def test_sesion_expirada_no_rompe_idempotencia(
    client, usuario_factory, tipo_con_definicion_activa_factory
):
    """Scenario 12: a draft replayed after a session expiry + re-login is
    idempotent, never a duplicate — the server-testable half of the
    session-expiry contract `paso-offline.js`/Dexie relies on (design's
    Testing Strategy)."""
    usuario = usuario_factory()
    tipo, _definicion = tipo_con_definicion_activa_factory()
    id_local = str(uuid.uuid4())

    client.force_login(usuario)
    primera = client.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )
    assert primera.status_code == 302
    assert Reporte.objects.count() == 1

    client.logout()
    expirada = client.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )
    assert expirada.status_code == 302
    assert reverse("login") in expirada.url
    assert Reporte.objects.count() == 1

    client.force_login(usuario)
    reingreso = client.post(
        reverse("reportes_nuevo", args=[tipo.codigo]), {"id_local": id_local}
    )
    assert reingreso.status_code == 302
    assert Reporte.objects.count() == 1
    reporte = Reporte.objects.get()
    assert reingreso.url == primera.url
    assert reporte.numero_registro is not None

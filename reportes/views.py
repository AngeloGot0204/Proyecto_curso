"""Views for the wizard-captura (backlog #5, Phase 4; design D7, D8, D9).

`iniciar_reporte` creates exactly one `Reporte` per `POST`, referencing the
`TipoDeReporte`'s currently-active `DefinicionDeTipo` snapshot (design D7 —
never on `GET`, so a refresh/prefetch can never spawn an orphan `Reporte`).
`paso` renders and persists one section at a time: `GET` rehydrates the
dynamic form from existing `ValorDeReporte` rows (spec: GET rehydration
from persisted rows), `POST` upserts via `guardar_valor` and redirects
Post/Redirect/Get-style to the next section — or back to itself on the
last section, since a finish screen is out of scope here (backlog #7; see
design's Open Questions).

Creator-or-invited-participant access (backlog #8; design D1; widened from
the original creator-only D9) is enforced by `_reporte_accesible`: fetch
via `get_object_or_404(Reporte, pk=…)`, then check `permisos.tiene_acceso`,
raising `Http404` manually otherwise. A `Reporte` that exists but the
requesting user has no access to 404s exactly like one that does not exist,
leaking no existence information. `paso`, `revision`, and `generar` all use
this shim; `cerrar_reporte` (and `invitar`) stay strictly creator-only and
do NOT widen with invitations (spec `cierre-reporte`).

`revision` (S-09 review screen; backlog `validacion-datos-formulario`;
spec `validacion-reporte`) is a GET-only, creator-or-participant-scoped
view that calls `reportes.validacion.validar_reporte` and renders its two
buckets.
"""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from reportes.formularios import construir_formulario_seccion
from reportes.models import (
    CambioDeValor,
    EstadoDeReporte,
    Generacion,
    ParticipacionEnReporte,
    Reporte,
    ValorDeReporte,
    VistoBueno,
)
from reportes.permisos import tiene_acceso
from reportes.valores import desde_texto, guardar_valor, valores_de_reporte
from reportes.validacion import validar_reporte
from tipos_reporte import generador
from tipos_reporte.generador import ProblemaDeGeneracion
from tipos_reporte.models import TipoDeReporte

logger = logging.getLogger(__name__)


def service_worker(request):
    """`GET /sw.js` (change `capa-offline`; spec `capa-offline` — "Root-
    Scoped Service Worker Route"; design's Decision "sw.js served as a
    Django template"). Public, unauthenticated route served at the domain
    root (outside WhiteNoise's `/static/` prefix) so the SW can register
    with root scope via `Service-Worker-Allowed: /`. Rendered from
    `reportes/templates/reportes/sw.js`, a Django template (not a static
    file), so `{% static %}` URLs inside it stay authoritative in every
    environment."""
    respuesta = render(request, "reportes/sw.js", content_type="application/javascript")
    respuesta["Service-Worker-Allowed"] = "/"
    respuesta["Cache-Control"] = "no-cache"
    return respuesta


def _seccion_por_id(estructura, seccion_id):
    """Return the section dict matching `seccion_id`, or `None`. Section
    order in `estructura["secciones"]` IS wizard order (design's Data Flow
    note — no `orden` key exists)."""
    for seccion in estructura.get("secciones", []):
        if seccion["id"] == seccion_id:
            return seccion
    return None


def _ids_de_secciones(estructura):
    return [seccion["id"] for seccion in estructura.get("secciones", [])]


def _reporte_accesible(reporte_id, usuario):
    """Fetch-then-check-then-404 shim (design D1): used by `paso`,
    `revision`, and `generar`, which are creator-OR-invited-participant
    scoped. `get_object_or_404` cannot take an arbitrary boolean, and it
    itself only ever raises `Http404` — raising `Http404` manually here
    produces a byte-identical response, preserving D9's no-existence-leak
    (same 404 for "absent" and "no access"). `cerrar_reporte` and `invitar`
    stay creator-only and do NOT use this shim."""
    reporte = get_object_or_404(Reporte, pk=reporte_id)
    if not tiene_acceso(reporte, usuario):
        raise Http404("Reporte inexistente o sin acceso.")
    return reporte


@login_required
@require_POST
def iniciar_reporte(request, codigo_tipo):
    """`POST /reportes/<codigo_tipo>/nuevo/` (design D7)."""
    tipo = get_object_or_404(TipoDeReporte, codigo=codigo_tipo)
    if tipo.definicion_activa_id is None:
        raise Http404("Este tipo de reporte no tiene una definición activa.")

    reporte = Reporte.objects.create(
        tipo=tipo,
        definicion=tipo.definicion_activa,
        creador=request.user,
    )

    ids_de_secciones = _ids_de_secciones(tipo.definicion_activa.estructura)
    primera_seccion = ids_de_secciones[0]
    return redirect("reportes_paso", reporte_id=reporte.id, seccion_id=primera_seccion)


@login_required
def paso(request, reporte_id, seccion_id):
    """`GET`/`POST /reportes/<reporte_id>/paso/<seccion_id>/`."""
    reporte = _reporte_accesible(reporte_id, request.user)
    estructura = reporte.definicion.estructura
    ids_de_secciones = _ids_de_secciones(estructura)
    seccion = _seccion_por_id(estructura, seccion_id)
    if seccion is None:
        raise Http404("Sección desconocida para este reporte.")

    FormularioDeSeccion = construir_formulario_seccion(seccion)

    if request.method == "POST":
        form = FormularioDeSeccion(data=request.POST)
        form.is_valid()  # every field is required=False (design D8) — never
        # blocks; cleaned_data below always reflects the submitted values.
        for nombre_campo in form.fields:
            valor = form.cleaned_data.get(nombre_campo)
            guardar_valor(reporte, nombre_campo, valor, request.user)

        posicion_actual = ids_de_secciones.index(seccion_id)
        es_ultima = posicion_actual == len(ids_de_secciones) - 1
        siguiente_id = (
            seccion_id if es_ultima else ids_de_secciones[posicion_actual + 1]
        )
        return redirect("reportes_paso", reporte_id=reporte.id, seccion_id=siguiente_id)

    valores_guardados = valores_de_reporte(reporte)
    initial = {}
    for nombre_campo, campo in FormularioDeSeccion.base_fields.items():
        texto = valores_guardados.get(nombre_campo)
        if texto is not None:
            initial[nombre_campo] = desde_texto(campo, texto)
    form = FormularioDeSeccion(initial=initial)

    posicion_actual = ids_de_secciones.index(seccion_id)
    pasos = [
        {
            "id": sid,
            "titulo": _seccion_por_id(estructura, sid).get("titulo", sid),
            "es_actual": sid == seccion_id,
        }
        for sid in ids_de_secciones
    ]
    url_anterior = None
    if posicion_actual > 0:
        url_anterior = _url_paso(reporte.id, ids_de_secciones[posicion_actual - 1])
    url_siguiente = None
    if posicion_actual < len(ids_de_secciones) - 1:
        url_siguiente = _url_paso(reporte.id, ids_de_secciones[posicion_actual + 1])

    servidor_actualizado = _servidor_actualizado(reporte, seccion)

    contexto = {
        "reporte": reporte,
        "seccion": seccion,
        "form": form,
        "pasos": pasos,
        "url_anterior": url_anterior,
        "url_siguiente": url_siguiente,
        "posicion": f"Paso {posicion_actual + 1} de {len(ids_de_secciones)}",
        "servidor_actualizado": servidor_actualizado,
    }
    return render(request, "reportes/paso.html", contexto)


def _servidor_actualizado(reporte, seccion):
    """`max(ValorDeReporte.fecha)` across every campo/item declared in this
    `seccion`, or `""` if none has been saved yet (change `capa-offline`;
    design's Technical Approach — the sole signal `paso-offline.js` uses to
    decide whether a local IndexedDB draft is newer than what the server
    already has). Scoped to the section's own field identifiers, not the
    whole `Reporte`, so an update in another section never marks this one as
    server-newer."""
    identificadores = [campo["id"] for campo in seccion.get("campos", [])]
    for item in seccion.get("items", []):
        if item.get("tipo") == "rango-hora-inicio-fin":
            identificadores.append(f"{item['id']}_inicio")
            identificadores.append(f"{item['id']}_fin")
        else:
            identificadores.append(item["id"])

    ultimo = (
        ValorDeReporte.objects.filter(
            reporte=reporte, identificador_de_campo__in=identificadores
        )
        .order_by("-fecha")
        .values_list("fecha", flat=True)
        .first()
    )
    return ultimo.isoformat() if ultimo is not None else ""


def _url_paso(reporte_id, seccion_id):
    return reverse("reportes_paso", args=[reporte_id, seccion_id])


@login_required
def revision(request, reporte_id):
    """`GET /reportes/<reporte_id>/revision/` (S-09; spec
    `validacion-reporte`). Creator-or-invited-participant scoped, exactly
    like `paso` (backlog #8; design D1; spec `cierre-reporte` — "Revision
    View Access Widens With Invitations"); calls `validar_reporte` and
    renders both buckets plus the derived `puede_generar` flag the template
    uses to disable "Generar"."""
    reporte = _reporte_accesible(reporte_id, request.user)
    resultado = validar_reporte(reporte)
    contexto = {
        "reporte": reporte,
        "resultado": resultado,
        "tiene_visto_bueno": VistoBueno.objects.filter(reporte=reporte).exists(),
    }
    return render(request, "reportes/revision.html", contexto)


@login_required
@require_POST
def cerrar_reporte(request, reporte_id):
    """`POST /reportes/<reporte_id>/cerrar/` (backlog #7; spec
    `cierre-reporte`; design D2, D9). Strictly creator-scoped, unaffected
    by `ParticipacionEnReporte` (backlog #8; spec `cierre-reporte` —
    "Cerrar Reporte Access Is Unaffected By Invitations"): a `Reporte`
    that exists but belongs to someone else — including an invited
    non-creator participant — 404s exactly like one that does not exist.
    Re-validates
    `puede_generar` server-side — independent of any client-side gating in
    `revision.html` — before creating the `VistoBueno`. `get_or_create`
    inside `transaction.atomic()` makes a double-POST an idempotent no-op
    (design D2): a bare `create()` would raise `IntegrityError` on the
    `OneToOneField` for a double-click, which is exactly the raw-500
    failure mode this design forbids."""
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
    if not validar_reporte(reporte).puede_generar:
        messages.error(
            request,
            "El reporte todavía tiene errores pendientes; no puede cerrarse.",
        )
        return redirect("reportes_revision", reporte_id=reporte.id)

    with transaction.atomic():
        VistoBueno.objects.get_or_create(
            reporte=reporte, defaults={"usuario": request.user}
        )
        reporte.estado = EstadoDeReporte.TERMINADO
        reporte.save(update_fields=["estado"])

    messages.success(request, "Reporte cerrado. Ya puede generarse el documento.")
    return redirect("reportes_revision", reporte_id=reporte.id)


@login_required
@require_POST
def generar(request, reporte_id):
    """`POST /reportes/<reporte_id>/generar/` (backlog #7, spec
    `generacion-documento`; design D3, D6). Creator-or-invited-participant
    scoped via `_reporte_accesible` (backlog #8; design D1; spec
    `generacion-documento` — "Creator or Invited Participant May Generate",
    superseding the prior "Any Authenticated User May Generate"). Requires
    an existing `VistoBueno` (checked independently of `puede_generar`),
    then re-validates `puede_generar` server-side (defense in depth,
    mirrors `cerrar_reporte`'s own re-check). Catches
    `ProblemaDeGeneracion` and degrades to a flash message + redirect —
    never a raw 500 (design D6: logged via stdlib `logger.exception`,
    Sentry-ready but not wired). On success, records a `Generacion` audit
    row and streams the `.xlsx` as an attachment with a server-derived
    filename (never user-supplied)."""
    reporte = _reporte_accesible(reporte_id, request.user)

    if not VistoBueno.objects.filter(reporte=reporte).exists():
        messages.error(
            request,
            "El reporte todavía no fue cerrado (visto bueno pendiente).",
        )
        return redirect("reportes_revision", reporte_id=reporte.id)

    if not validar_reporte(reporte).puede_generar:
        messages.error(
            request,
            "El reporte todavía tiene errores pendientes; no puede generarse.",
        )
        return redirect("reportes_revision", reporte_id=reporte.id)

    valores = valores_de_reporte(reporte)
    try:
        buffer = generador.generar_reporte(reporte.definicion, valores)
    except ProblemaDeGeneracion:
        logger.exception(
            "Fallo al generar el documento del reporte #%s", reporte.id
        )
        messages.error(
            request, "No se pudo generar el documento. Intentá nuevamente."
        )
        return redirect("reportes_revision", reporte_id=reporte.id)

    Generacion.objects.create(
        reporte=reporte, definicion=reporte.definicion, usuario=request.user
    )

    nombre = (
        f"{reporte.tipo.codigo}-{reporte.id}-{timezone.localdate():%Y%m%d}.xlsx"
    )
    respuesta = HttpResponse(
        buffer.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


@login_required
@require_POST
def invitar(request, reporte_id):
    """`POST /reportes/<reporte_id>/invitar/` (backlog #8; spec
    `colaboracion-reporte` — "Creator-Only Invite Action"; design's "Invite
    view shape"). Strictly creator-scoped, like `cerrar_reporte` — does NOT
    use `_reporte_accesible`, since only the creator may invite. Resolves
    `Usuario.username` by exact match; unknown username or self-invite (to
    protect "creator has no participation row", ADR-0006) sets an error
    flash message with no row created; a valid, not-yet-invited username is
    granted access idempotently via `get_or_create`, mirroring
    `cerrar_reporte`'s idempotency pattern."""
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
    username = (request.POST.get("username") or "").strip()
    invitado = get_user_model().objects.filter(username=username).first()
    if invitado is None:
        messages.error(request, f"No existe un usuario con el nombre «{username}».")
    elif invitado.id == reporte.creador_id:
        messages.error(request, "El creador ya tiene acceso al reporte.")
    else:
        ParticipacionEnReporte.objects.get_or_create(reporte=reporte, usuario=invitado)
        messages.success(request, f"{username} ya puede trabajar en este reporte.")
    return redirect("reportes_participantes", reporte_id=reporte.id)


@login_required
def participantes(request, reporte_id):
    """`GET /reportes/<reporte_id>/participantes/` (backlog #8; spec
    `colaboracion-reporte` — "Participants and History View"; design D6).
    Creator-or-invited-participant scoped via `_reporte_accesible`, like
    `paso`/`revision`/`generar`. Lists invited users plus the creator (shown
    as a label, not a queried `ParticipacionEnReporte` row), the
    creator-only invite form, and the `Reporte`'s `CambioDeValor` history
    ordered most-recent-first (`-fecha, -id`, matching
    `valores._recortar_historial`'s tiebreaker)."""
    reporte = _reporte_accesible(reporte_id, request.user)
    participaciones = ParticipacionEnReporte.objects.filter(
        reporte=reporte
    ).select_related("usuario")
    cambios = CambioDeValor.objects.filter(reporte=reporte).select_related(
        "autor"
    ).order_by("-fecha", "-id")
    contexto = {
        "reporte": reporte,
        "participaciones": participaciones,
        "cambios": cambios,
    }
    return render(request, "reportes/participantes.html", contexto)

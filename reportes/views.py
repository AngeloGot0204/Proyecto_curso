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

Creator-only access (design D9) is enforced by scoping every `Reporte`
lookup to `creador=request.user` inside `get_object_or_404`: a `Reporte`
that exists but belongs to someone else 404s exactly like one that does not
exist, leaking no existence information.

`revision` (S-09 review screen; backlog `validacion-datos-formulario`;
spec `validacion-reporte`) is a GET-only, creator-scoped view that calls
`reportes.validacion.validar_reporte` and renders its two buckets.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from reportes.formularios import construir_formulario_seccion
from reportes.models import Reporte
from reportes.valores import desde_texto, guardar_valor, valores_de_reporte
from reportes.validacion import validar_reporte
from tipos_reporte.models import TipoDeReporte


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
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
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

    contexto = {
        "reporte": reporte,
        "seccion": seccion,
        "form": form,
        "pasos": pasos,
        "url_anterior": url_anterior,
        "url_siguiente": url_siguiente,
        "posicion": f"Paso {posicion_actual + 1} de {len(ids_de_secciones)}",
    }
    return render(request, "reportes/paso.html", contexto)


def _url_paso(reporte_id, seccion_id):
    return reverse("reportes_paso", args=[reporte_id, seccion_id])


@login_required
def revision(request, reporte_id):
    """`GET /reportes/<reporte_id>/revision/` (S-09; spec
    `validacion-reporte`). Creator-scoped exactly like `paso` (design D9);
    calls `validar_reporte` and renders both buckets plus the derived
    `puede_generar` flag the template uses to disable "Generar"."""
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
    resultado = validar_reporte(reporte)
    contexto = {
        "reporte": reporte,
        "resultado": resultado,
    }
    return render(request, "reportes/revision.html", contexto)

"""Views for the tipos-de-reporte administration screen (backlog #13, S-14,
PR 1 of a stacked-to-main chain; spec `administracion-tipos-reporte`; design
D1, D3, D6).

`lista` and `detalle` are read-only, thin wrappers over
`tipos_reporte.listado`'s pure helpers plus Django's `Paginator`
(design D3, mirrors `reportes/views.py::mis_reportes`). `activar_definicion_
vista` and `desactivar_tipo_vista` are POST-only, PRG + `messages` wrappers
over `tipos_reporte.servicios.activar_definicion`/`desactivar_tipo`, called
exactly as they exist today — zero changes to that module (design D6, spec
"Activation/Desactivation Reuses Existing Service Unchanged").

Every view in this module is gated by `usuarios.decorators.solo_
administradores` — the single gating mechanism the spec requires (design
D1). No per-view inline duplicate guard exists.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tipos_reporte import listado, servicios
from tipos_reporte.forms import DefinicionDeTipoForm, TipoDeReporteForm
from tipos_reporte.models import DefinicionDeTipo, Estado, TipoDeReporte
from usuarios.decorators import solo_administradores

TAMANO_DE_PAGINA = 20


@solo_administradores
def lista(request):
    """`GET /tipos-reporte/` (design D3, spec "List View With Search and
    Pagination"). `?q=` search is optional; `Paginator.get_page` clamps an
    invalid/out-of-range `?page=` instead of raising, mirroring `reportes/
    views.py::mis_reportes`."""
    q = (request.GET.get("q") or "").strip()
    qs = listado.aplicar_busqueda(listado.tipos_administrables(), q)
    page_obj = Paginator(qs, TAMANO_DE_PAGINA).get_page(request.GET.get("page"))
    contexto = {"page_obj": page_obj, "q": q}
    return render(request, "tipos_reporte/lista.html", contexto)


@solo_administradores
def detalle(request, tipo_id):
    """`GET /tipos-reporte/<int:tipo_id>/` (spec "Detail View"). Shows the
    tipo's own fields plus its full `DefinicionDeTipo` history, most-recently
    -activated first (borrador rows — `activada_en is None` — sort first via
    `nulls_first=True`, so a pending draft is never buried under old
    history)."""
    tipo = get_object_or_404(TipoDeReporte, pk=tipo_id)
    definiciones = tipo.definiciones.order_by(
        F("activada_en").desc(nulls_first=True), "-id"
    )
    contexto = {"tipo": tipo, "definiciones": definiciones}
    return render(request, "tipos_reporte/detalle.html", contexto)


@solo_administradores
@require_POST
def activar_definicion_vista(request, definicion_id):
    """`POST /tipos-reporte/definiciones/<int:definicion_id>/activar/`
    (design D6, spec "Activation Reuses Existing Service Unchanged").
    `servicios.activar_definicion` runs exactly as it exists today; on
    success this surfaces one `messages.SUCCESS`, on failure one
    `messages.ERROR` per accumulated `ProblemaDeDefinicion`, rendered
    `"{ubicacion}: {mensaje}"` (byte-identical to `DefinicionDeTipoAdmin.
    activar`'s existing behavior)."""
    definicion = get_object_or_404(DefinicionDeTipo, pk=definicion_id)
    resultado = servicios.activar_definicion(definicion)
    if resultado.es_valida:
        messages.success(request, "Definición activada correctamente.")
    else:
        for problema in resultado.problemas:
            messages.error(request, f"{problema.ubicacion}: {problema.mensaje}")
    return redirect("tipos_detalle", tipo_id=definicion.tipo_id)


@solo_administradores
@require_POST
def desactivar_tipo_vista(request, tipo_id):
    """`POST /tipos-reporte/<int:tipo_id>/desactivar/` (design D6, spec
    "Desactivation Reuses Existing Service Unchanged"). `servicios.
    desactivar_tipo` runs exactly as it exists today."""
    tipo = get_object_or_404(TipoDeReporte, pk=tipo_id)
    servicios.desactivar_tipo(tipo)
    messages.success(request, "Tipo de reporte desactivado.")
    return redirect("tipos_detalle", tipo_id=tipo.id)


@solo_administradores
def crear_tipo(request):
    """`GET/POST /tipos-reporte/nuevo/` (PR2, spec "Create and Edit Forms
    for TipoDeReporte"). A newly created tipo has no active definición, so
    `TipoDeReporteForm`'s `plantilla` field is always editable here."""
    if request.method == "POST":
        form = TipoDeReporteForm(request.POST, request.FILES)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, "Tipo de reporte creado correctamente.")
            return redirect("tipos_detalle", tipo_id=tipo.id)
    else:
        form = TipoDeReporteForm()
    return render(request, "tipos_reporte/formulario_tipo.html", {"form": form})


@solo_administradores
def editar_tipo(request, tipo_id):
    """`GET/POST /tipos-reporte/<int:tipo_id>/editar/` (PR2). `plantilla`
    renders read-only once the tipo has an active definición (design D4);
    editing without re-uploading `logo` keeps the existing file (design
    D8, plain `ModelForm` default)."""
    tipo = get_object_or_404(TipoDeReporte, pk=tipo_id)
    if request.method == "POST":
        form = TipoDeReporteForm(request.POST, request.FILES, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, "Tipo de reporte actualizado correctamente.")
            return redirect("tipos_detalle", tipo_id=tipo.id)
    else:
        form = TipoDeReporteForm(instance=tipo)
    return render(
        request, "tipos_reporte/formulario_tipo.html", {"form": form, "tipo": tipo}
    )


@solo_administradores
def crear_definicion(request, tipo_id):
    """`GET/POST /tipos-reporte/<int:tipo_id>/definiciones/nueva/` (PR2,
    spec "Create and Edit Form for DefinicionDeTipo"). `tipo` is fixed by
    the URL (design D5) — the form never exposes it."""
    tipo = get_object_or_404(TipoDeReporte, pk=tipo_id)
    if request.method == "POST":
        form = DefinicionDeTipoForm(request.POST, request.FILES)
        form.instance.tipo = tipo
        if form.is_valid():
            form.save()
            messages.success(request, "Definición creada correctamente.")
            return redirect("tipos_detalle", tipo_id=tipo.id)
    else:
        form = DefinicionDeTipoForm()
    return render(
        request, "tipos_reporte/formulario_definicion.html", {"form": form, "tipo": tipo}
    )


@solo_administradores
def editar_definicion(request, tipo_id, definicion_id):
    """`GET/POST /tipos-reporte/<int:tipo_id>/definiciones/<int:definicion_
    id>/editar/` (PR2, design D5). Edit is restricted to `borrador` rows —
    `models.py`'s `CONGELADOS` guard makes `estructura`/`yaml_fuente`
    immutable once a row leaves borrador, so a non-borrador row 404s
    rather than reaching a form that could only ever fail on save."""
    tipo = get_object_or_404(TipoDeReporte, pk=tipo_id)
    definicion = get_object_or_404(
        DefinicionDeTipo, pk=definicion_id, tipo=tipo, estado=Estado.BORRADOR
    )
    if request.method == "POST":
        form = DefinicionDeTipoForm(request.POST, request.FILES, instance=definicion)
        if form.is_valid():
            form.save()
            messages.success(request, "Definición actualizada correctamente.")
            return redirect("tipos_detalle", tipo_id=tipo.id)
    else:
        form = DefinicionDeTipoForm(instance=definicion)
    return render(
        request, "tipos_reporte/formulario_definicion.html", {"form": form, "tipo": tipo}
    )

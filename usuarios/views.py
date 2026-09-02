from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from reportes import listado
from reportes.models import VistoBueno
from usuarios.decorators import solo_administradores
from usuarios.forms import ResetearPasswordForm, UsuarioCrearForm, UsuarioEditarForm
from usuarios.models import Rol, Usuario

TAMANO_DE_PAGINA = 20


@login_required
def inicio(request):
    """Post-login landing page (`LOGIN_REDIRECT_URL = "inicio"`).

    A real greeting/summary screen, not a bare redirect: one bucket count
    per `listado.BUCKETS` state (en progreso / listo para generar /
    terminado) over the user's own accessible reports, computed with the
    exact same pipeline `reportes_mis` uses (`reportes_accesibles` +
    `Exists(VistoBueno)` annotation + `construir_tarjetas`) so the numbers
    shown here can never drift from what "Mis reportes" itself would
    display — counting is just `len()` on the same bucketed list, no
    separate aggregation query to keep in sync."""
    qs = listado.reportes_accesibles(request.user).annotate(
        tiene_visto_bueno=Exists(VistoBueno.objects.filter(reporte=OuterRef("pk")))
    ).select_related("definicion")
    tarjetas = listado.construir_tarjetas(qs)
    grupos = listado.agrupar_por_bucket(tarjetas)
    conteos = [
        {"id": grupo["id"], "titulo": grupo["titulo"], "cantidad": len(grupo["tarjetas"])}
        for grupo in grupos
    ]
    contexto = {"conteos": conteos}
    return render(request, "usuarios/inicio.html", contexto)


@solo_administradores
def usuarios_lista(request):
    """`GET /usuarios/` (BACKLOG.md #1, S-13, "buscador"). `?q=` filters by
    username (`icontains`); mirrors `tipos_reporte.views.lista`'s
    `Paginator.get_page` pattern, which clamps an invalid/out-of-range
    `?page=` instead of raising."""
    q = (request.GET.get("q") or "").strip()
    qs = Usuario.objects.all().order_by("username")
    if q:
        qs = qs.filter(username__icontains=q)
    page_obj = Paginator(qs, TAMANO_DE_PAGINA).get_page(request.GET.get("page"))
    contexto = {"page_obj": page_obj, "q": q}
    return render(request, "usuarios/lista.html", contexto)


@solo_administradores
def usuarios_crear(request):
    """`GET/POST /usuarios/nuevo/` (S-13, "crear" — this app has no self-
    registration, so admin-creates-account IS the account creation path)."""
    if request.method == "POST":
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect("usuarios_lista")
    else:
        form = UsuarioCrearForm()
    return render(request, "usuarios/formulario_usuario.html", {"form": form})


@solo_administradores
def usuarios_editar(request, usuario_id):
    """`GET/POST /usuarios/<int:usuario_id>/editar/` (S-13, "editar rol/
    organización" — only `rol` is editable; "organización" has no backing
    model in this codebase, see `usuarios/forms.py` module docstring)."""
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if request.method == "POST":
        form = UsuarioEditarForm(request.POST, instance=usuario)
        if form.is_valid():
            # Same reasoning as `usuarios_suspender`'s self-suspend guard:
            # dropping your own administrator role locks you out of every
            # `solo_administradores` screen with no self-service way back
            # in, and recovering needs database or `manage.py` access
            # against production. Demoting a DIFFERENT admin stays
            # unrestricted — the actor is mid-request as an active admin, so
            # no single request can leave zero administrators.
            se_autodegrada = (
                usuario.id == request.user.id
                and form.cleaned_data["rol"] != Rol.ADMINISTRADOR
            )
            if se_autodegrada:
                messages.error(
                    request,
                    "No podés quitarte a vos mismo el rol de administrador.",
                )
                return redirect("usuarios_lista")
            form.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("usuarios_lista")
    else:
        form = UsuarioEditarForm(instance=usuario)
    return render(
        request, "usuarios/formulario_usuario.html", {"form": form, "usuario": usuario}
    )


@solo_administradores
def usuarios_resetear_password(request, usuario_id):
    """`GET/POST /usuarios/<int:usuario_id>/resetear-password/` (S-13,
    "resetear contraseña" — admin sets a new password without knowing the
    old one, via `set_password` + `Usuario.save()`)."""
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if request.method == "POST":
        form = ResetearPasswordForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data["nueva_password"])
            usuario.save()
            messages.success(request, "Contraseña reestablecida correctamente.")
            return redirect("usuarios_lista")
    else:
        form = ResetearPasswordForm()
    return render(
        request,
        "usuarios/resetear_password.html",
        {"form": form, "usuario": usuario},
    )


@solo_administradores
@require_POST
def usuarios_suspender(request, usuario_id):
    """`POST /usuarios/<int:usuario_id>/suspender/` (S-13, "suspender" —
    toggles `is_active`, Django's natural fit for account suspension/
    reactivation; PRG pattern mirrors `tipos_reporte.views.
    desactivar_tipo_vista`). Reactivating is always allowed; suspending
    yourself is blocked — it would lock the acting admin out of
    `solo_administradores`-gated screens with no self-service way back in.
    Suspending some OTHER admin is unrestricted: the actor themselves
    stays active by definition (they're mid-request as an active admin),
    so no single request can ever suspend every admin — a "last admin"
    check would be unreachable dead code."""
    usuario = get_object_or_404(Usuario, pk=usuario_id)

    if usuario.is_active and usuario.id == request.user.id:
        messages.error(request, "No podés suspender tu propia cuenta.")
        return redirect("usuarios_lista")

    usuario.is_active = not usuario.is_active
    usuario.save()
    if usuario.is_active:
        messages.success(request, "Usuario reactivado.")
    else:
        messages.success(request, "Usuario suspendido.")
    return redirect("usuarios_lista")

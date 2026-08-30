"""Access-control decorators for `usuarios` (backlog #13, S-14; spec
`administracion-tipos-reporte` — "Admin-Role-Gated Access"; design D1).

`solo_administradores` is the single gating mechanism for every view in the
`tipos_reporte` administration screen — no per-view inline duplicate guard.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def solo_administradores(vista):
    """Restrict `vista` to authenticated users for whom
    `Usuario.es_administrador` is `True`.

    `login_required` is applied LAST here — which means it wraps
    `_envoltura`, so it runs FIRST at request time: an anonymous request is
    redirected to `LOGIN_URL` before `request.user.es_administrador` is ever
    read (`AnonymousUser` has no such attribute). An authenticated
    non-administrator raises `PermissionDenied`, which Django's `handler403`
    turns into a 403 response with the view body never executed."""

    @wraps(vista)
    def _envoltura(request, *args, **kwargs):
        if not request.user.es_administrador:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return login_required(_envoltura)

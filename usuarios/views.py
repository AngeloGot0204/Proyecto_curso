from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def inicio(request):
    """Post-login landing page.

    Backlog item #12 consumed this view's scope guard: it now redirects
    (302, not 301, to preserve revert-based rollback) to the real
    dashboard at ``reportes_mis``. This view keeps its own URL name/path
    and ``@login_required`` decorator so ``LOGIN_REDIRECT_URL = "inicio"``
    keeps working transparently.
    """
    return redirect("reportes_mis")

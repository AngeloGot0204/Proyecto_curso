from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def inicio(request):
    """Minimal post-login landing page.

    Scope guard: this view must accumulate no report-domain logic.
    Backlog item #12 replaces it with the real dashboard.
    """
    return render(request, "inicio.html")

"""Content-Security-Policy middleware (SECURITY-REPORT.md F-02).

Django ships no CSP support, and this project had no policy at all: if
anything ever managed to inject a script tag, nothing in the browser would
stop it. A hand-written middleware is used instead of `django-csp` for the
same reason ADR-0001 keeps the frontend dependency-free — the policy here is
a single static string, and a dependency to emit one header is not a trade
worth making.

The policy is deliberately strict, which is only possible because this app
carries no inline JavaScript: the three former inline `<script>` blocks live
in `static/js/registrar-sw.js` and `reportes/static/reportes/
nuevo-reporte-form.js`, and the three `onsubmit="return confirm(...)"`
attributes (inline script as far as CSP is concerned) were replaced by
`static/js/confirmar-accion.js`'s `data-confirmar` contract. A policy that
has to allow `'unsafe-inline'` blocks almost nothing worth blocking, so
keeping the pages inline-free is what gives this header its value —
`reportes/tests/test_estatico.py` guards that.

`style-src` still allows `'unsafe-inline'`: Django's own form widgets and
several templates set `style=` attributes, and tightening that is a separate
change with no security payoff while `script-src` holds.

`DJANGO_CSP_REPORT_ONLY` (default `True`) decides which header is sent.
Report-only first is deliberate: an enforcing policy that is wrong breaks
the app for everyone at once, and this one has never run in production. Flip
it to `False` once the browser console is quiet.
"""

import os

from config.storage import HOST_PUBLICO_DE_BLOB

# Ordered for reading, not for the parser.
_DIRECTIVAS = (
    # Nothing loads from anywhere by default; every allowance below is
    # explicit.
    "default-src 'self'",
    # Third-party libraries are vendored under `static/vendor/`, so no CDN
    # needs allowing here (SECURITY-REPORT.md F-02).
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    # Attachments and logos are served from Vercel Blob's public host, and
    # `adjuntos.js` renders local previews from blob:/data: URLs before
    # upload. The hostname is imported, never repeated here: `config.storage`
    # is its single owner and `test_a7_blob_consumption_scoped_to_storage_
    # module` enforces that.
    f"img-src 'self' data: blob: {HOST_PUBLICO_DE_BLOB}",
    "font-src 'self'",
    # `adjuntos.js` and `envio-paso.js` only ever fetch same-origin.
    "connect-src 'self'",
    # No plugins, and no <base> tag that could re-point every relative URL.
    "object-src 'none'",
    "base-uri 'none'",
    # Every form in this app posts to itself; `logout` included.
    "form-action 'self'",
    # Clickjacking, belt and braces with X-Frame-Options.
    "frame-ancestors 'none'",
)

POLITICA = "; ".join(_DIRECTIVAS)


def _es_report_only():
    """Default `True`. Unlike `DJANGO_HTTPS_ONLY`, this is not fail-loud:
    a missing value must not stop the app from booting, and the safe default
    (report, don't block) cannot break a page."""
    return os.environ.get("DJANGO_CSP_REPORT_ONLY", "True") != "False"


def content_security_policy(get_response):
    """Attach the policy to every response.

    Never overwrites a header a view already set, so a future endpoint that
    genuinely needs a different policy can opt out by setting its own.
    """

    cabecera = (
        "Content-Security-Policy-Report-Only"
        if _es_report_only()
        else "Content-Security-Policy"
    )

    def middleware(request):
        respuesta = get_response(request)
        if cabecera not in respuesta:
            respuesta[cabecera] = POLITICA
        return respuesta

    return middleware

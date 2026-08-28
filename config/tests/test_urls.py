"""Code-review fix: `MEDIA_URL`/`MEDIA_ROOT` must be served in development
(`DEBUG=True`) — without this, uploaded files (e.g. `TipoDeReporte.logo`,
`plantilla`) are unreachable at their URL even locally, so the admin's
"Currently: <file>" link 404s.

Follows this directory's established pattern (`conftest.py`'s
`_load_settings`): `config/urls.py` reads `django.conf.settings.DEBUG` at
IMPORT time to decide whether to append the media-serving pattern, so this
probe re-executes the real module fresh under `override_settings` instead of
depending on the developer's own `.env` DEBUG value (ambient, not
controlled).
"""

import importlib.util
from pathlib import Path

from django.test import override_settings

URLS_PATH = Path(__file__).resolve().parents[2] / "config" / "urls.py"


def _load_urls_module():
    spec = importlib.util.spec_from_file_location("config._urls_probe", URLS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # deliberately NOT put in sys.modules
    return module


@override_settings(DEBUG=True)
def test_media_pattern_is_added_when_debug_true():
    modulo = _load_urls_module()

    rutas = [str(patron.pattern) for patron in modulo.urlpatterns]

    assert any("media" in ruta for ruta in rutas), (
        "urlpatterns debe incluir el patrón de MEDIA_URL cuando DEBUG=True"
    )


@override_settings(DEBUG=False)
def test_media_pattern_is_absent_when_debug_false():
    modulo = _load_urls_module()

    rutas = [str(patron.pattern) for patron in modulo.urlpatterns]

    assert not any("media" in ruta for ruta in rutas), (
        "urlpatterns no debe servir MEDIA_URL cuando DEBUG=False"
    )

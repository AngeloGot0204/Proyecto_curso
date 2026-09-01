"""Tests for the visual retrofit's static-asset plumbing (change
`retrofit-visual-design2`, PR1a, tasks.md Phase 1 tasks 1.1-1.4).

Covers: `STATICFILES_DIRS` makes the repo-root `static/` directory visible to
`django.contrib.staticfiles.finders` (design D2); the two self-hosted IBM
Plex Mono `.woff2` files are real, non-empty webfont binaries (design D2,
Threat Matrix "Third-party binary assets in-repo"); `tokens.css` defines the
full DESIGN2 §1 palette with no red/danger hue (spec `visual-design-system`,
Requirement "Design Token Stylesheet").
"""

import re

from django.contrib.staticfiles import finders

# DESIGN2 §1 palette, exactly as recorded in design.md D1. Fifteen entries.
COLORES_DESIGN2_SECCION1 = (
    "#f4f3f1",  # --color-fondo
    "#ffffff",  # --color-superficie
    "#14130f",  # --color-tinta
    "#4a463f",  # --color-tinta-2
    "#6f6a61",  # --color-tinta-mono
    "#d9d5cf",  # --color-linea
    "#eeece8",  # --color-linea-interna
    "#d9d5cf",  # --color-bloqueado-fondo (repeats --color-linea's hex, distinct token)
    "#8b867d",  # --color-bloqueado-texto
    "#b06a00",  # --color-ambar-borde
    "#e0bd7c",  # --color-ambar-borde-suave
    "#fdf1dc",  # --color-ambar-fondo
    "#7a5a1c",  # --color-ambar-texto
    "rgba(20,19,15,.5)",  # --color-velo
    "#a8a29a",  # --color-punteado
)


def test_finders_resuelve_tokens_css():
    """`finders.find()` resolves `css/tokens.css` once `STATICFILES_DIRS`
    exposes the repo-root `static/` directory (design D2)."""
    ruta = finders.find("css/tokens.css")

    assert ruta is not None
    assert ruta.replace("\\", "/").endswith("static/css/tokens.css")


def test_finders_resuelve_components_css():
    """`finders.find()` resolves `css/components.css` (design D2)."""
    ruta = finders.find("css/components.css")

    assert ruta is not None
    assert ruta.replace("\\", "/").endswith("static/css/components.css")


def test_finders_resuelve_woff2_regular_y_medium():
    """Both self-hosted IBM Plex Mono weights resolve via the static
    finders (spec 'Self-Hosted Mono Font, No CDN Dependency')."""
    ruta_regular = finders.find("fonts/IBMPlexMono-Regular.woff2")
    ruta_medium = finders.find("fonts/IBMPlexMono-Medium.woff2")

    assert ruta_regular is not None
    assert ruta_regular.replace("\\", "/").endswith(
        "static/fonts/IBMPlexMono-Regular.woff2"
    )
    assert ruta_medium is not None
    assert ruta_medium.replace("\\", "/").endswith(
        "static/fonts/IBMPlexMono-Medium.woff2"
    )


def test_woff2_regular_firma_wof2_y_mayor_a_10kb():
    """`IBMPlexMono-Regular.woff2` starts with the `wOF2` magic bytes and
    weighs more than 10KB — catches a committed HTML error page or an LFS
    pointer masquerading as the real binary (design's Threat Matrix)."""
    ruta = finders.find("fonts/IBMPlexMono-Regular.woff2")
    with open(ruta, "rb") as archivo:
        contenido = archivo.read()

    assert contenido[:4] == b"wOF2"
    assert len(contenido) > 10 * 1024


def test_woff2_medium_firma_wof2_y_mayor_a_10kb():
    """`IBMPlexMono-Medium.woff2` starts with the `wOF2` magic bytes and
    weighs more than 10KB (same rationale as the Regular weight above)."""
    ruta = finders.find("fonts/IBMPlexMono-Medium.woff2")
    with open(ruta, "rb") as archivo:
        contenido = archivo.read()

    assert contenido[:4] == b"wOF2"
    assert len(contenido) > 10 * 1024


def test_tokens_css_contiene_cada_hex_design2_seccion1():
    """`tokens.css` text contains every DESIGN2 §1 hex/color value (spec
    scenario 'Tokens file defines the full palette')."""
    ruta = finders.find("css/tokens.css")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read().lower()

    faltantes = [
        color for color in COLORES_DESIGN2_SECCION1 if color.lower() not in contenido
    ]

    assert faltantes == [], f"Faltan colores DESIGN2 §1 en tokens.css: {faltantes}"


def test_tokens_css_no_contiene_color_rojo():
    """No CSS custom property in `tokens.css` defines a red/danger color —
    ámbar is the only warning color (spec: 'no CSS custom property in the
    file defines a red/danger color')."""
    ruta = finders.find("css/tokens.css")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read().lower()

    # Named CSS red keywords and common red hex prefixes (`#f00`, `#ff0000`,
    # `#e0` reds like crimson/firebrick are out of DESIGN2's palette
    # entirely, so a plain substring check on the CSS keyword and the two
    # canonical red hex spellings is sufficient and avoids false positives
    # against `--color-ambar-*`/`--color-bloqueado-*`, none of which contain
    # these substrings).
    assert "red" not in contenido
    assert "#f00" not in contenido
    assert "#ff0000" not in contenido
    assert not re.search(r"rgba?\(\s*2[0-5][0-9]\s*,\s*0\s*,\s*0", contenido)


def test_paso_campo_error_aria_invalid_usa_borde_2px_sin_color_rojo():
    """Change `retrofit-visual-design2` PR2 (design D6, task 3.3): re-verifies
    the `.campo` error rule against the retrofitted `paso.html` context — the
    `[aria-invalid="true"]` selector resolves to a 2px ink border, never a
    red/danger color (spec `visual-design-system`, scenario 'Field error
    state uses border weight, not color'). `paso.js:95` is the only place
    that sets `aria-invalid="true"` at runtime in `paso.html` (no
    `{{ campo.errors }}` is rendered server-side there, per design D6), so
    this is a static CSS check, mirroring `test_tokens_css_no_contiene_color_rojo`."""
    ruta = finders.find("css/components.css")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read().lower()

    assert '[aria-invalid="true"]' in contenido
    assert "var(--borde-error)" in contenido
    assert "var(--color-tinta)" in contenido
    # Word-boundary match, not a bare substring check: legitimate CSS text
    # like `prefers-reduced-motion` contains "red" as a substring without
    # being a red/danger color anywhere.
    assert re.search(r"\bred\b", contenido) is None
    assert "#f00" not in contenido
    assert "#ff0000" not in contenido


def test_finders_resuelve_conexion_chip_js():
    """Change `chip-conexion-en-vivo` (tasks.md 1.1; design File Changes):
    `finders.find()` resolves `js/conexion-chip.js` once the file exists
    under the repo-root `static/` directory `STATICFILES_DIRS` exposes
    (same finder contract `test_finders_resuelve_tokens_css` already
    proves for `css/tokens.css`)."""
    ruta = finders.find("js/conexion-chip.js")

    assert ruta is not None
    assert ruta.replace("\\", "/").endswith("static/js/conexion-chip.js")


def test_conexion_chip_js_contiene_navigator_online_y_listeners():
    """Change `chip-conexion-en-vivo` (tasks.md 1.3; design "Strict
    isolation from paso-offline.js", Interfaces/Contracts): the module's
    source must read `navigator.onLine`, register both `online`/`offline`
    listeners, repaint text via `textContent` only, and never reference
    `paso-offline.js`'s `[data-borrador-*]` DOM contract — proving the two
    scripts share no DOM surface."""
    ruta = finders.find("js/conexion-chip.js")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    assert "navigator.onLine" in contenido
    assert 'addEventListener("online"' in contenido
    assert 'addEventListener("offline"' in contenido
    assert "textContent" in contenido
    assert "data-borrador-" not in contenido


def test_components_css_define_barra_pantalla_conexion_flex_shrink():
    """Change `chip-conexion-en-vivo` (tasks.md 3.1/3.3; design's Decision
    "Reuse `.chip--borde`/`.chip--borde-gris`, no new class"): the only new
    CSS rule is a layout-only `flex-shrink` for `.barra-pantalla__conexion`
    — no new visual language is introduced."""
    ruta = finders.find("css/components.css")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    assert ".barra-pantalla__conexion" in contenido
    assert "flex-shrink" in contenido


def test_borrador_banner_aplica_aviso_class_via_data_atributo():
    """Change `retrofit-visual-design2` PR3 (design D3/D7, task 4.5):
    `paso-offline.js` injects `[data-borrador-banner]`/`[data-borrador-prompt]`
    containers at runtime with no `class` attribute (`paso-offline.js:223,
    295`) — no `.js` file is edited (D7), so `components.css` must style
    both attributes directly with the same visual language as `.aviso`
    (spec `visual-design-system`, Requirement 'Eight DESIGN2 Component
    Classes')."""
    ruta = finders.find("css/components.css")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    assert "[data-borrador-banner]" in contenido
    assert "[data-borrador-prompt]" in contenido
    assert "var(--color-ambar-fondo)" in contenido


def test_sw_js_cachea_sincronizacion_y_bumpea_v7(client):
    """Change `vista-sincronizacion-pendientes`, task 6.1/6.2 (design D7):
    the S-15 shell route must be added to the SW's network-first navigation
    branch — otherwise it 503s offline — and `CACHE` must bump to `v7` so a
    returning user's stale cache never wins over this change's assets
    (spec `sincronizacion-pendientes`, mirrors the `retrofit-visual-
    design2` `v6` precedent in `test_views.py::test_sw_js_contiene_cache_v6`)."""
    response = client.get("/sw.js")
    contenido = response.content.decode()

    assert "reportes-offline-v23" in contenido
    assert "/reportes/sincronizacion/" in contenido


def test_envio_paso_js_preserva_campos_no_gestionados_del_borrador():
    """Spec `sincronizacion-pendientes` — "Per-Row Display Metadata" y "Draft
    Write Captures Display Metadata".

    `envio-paso.js` reescribe la fila de `borradores` en dos puntos
    (`reconciliarEnEnvio` y `reconciliarResultado`). Dexie `put()` REEMPLAZA el
    registro completo, de modo que un objeto literal borra todo campo que el
    helper no conozca: `paso-offline.js` escribe `tipoNombre`/`fechaReporte` al
    crear el borrador, y un reintento fallido los eliminaba, dejando la fila de
    S-15 como "Reporte · <seccion>" sin tipo ni fecha.

    Tripwire de fuente, no de comportamiento: este proyecto no tiene runner de
    JS (Out of Scope de la spec `capa-offline`), así que se verifica que ambas
    escrituras lean la fila previa y la fusionen en vez de reemplazarla."""
    ruta = finders.find("reportes/envio-paso.js")
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    # Lee la fila existente antes de escribir, en vez de asumir sus campos.
    assert "borradores.get(" in contenido
    # Fusiona sobre lo previo: los campos no gestionados sobreviven.
    assert "Object.assign(" in contenido
    # Ninguna de las dos escrituras pasa un literal directo a put().
    assert "put({" not in contenido



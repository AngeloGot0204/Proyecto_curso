"""Form + shared-helper tests for the tipos-de-reporte administration screen
(backlog #13, S-14, PR 2 of a stacked-to-main chain; spec
`administracion-tipos-reporte`; design D2, D4, D5). Focused command:
`pytest tipos_reporte/tests/test_formularios.py -q`.

Phase 5 covers `tipos_reporte.validacion.analizar_definicion_subida`, the
shared YAML-parsing/validation helper extracted verbatim from
`admin.py::DefinicionDeTipoForm.clean()` (design D2). Phase 6 covers
`tipos_reporte/forms.py`'s `TipoDeReporteForm`/`DefinicionDeTipoForm`
(design D4, D5).
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
import pytest


# ---------------------------------------------------------------------------
# Phase 5: validacion.analizar_definicion_subida
# ---------------------------------------------------------------------------


def test_analizar_definicion_subida_mapping_valido_retorna_texto_y_dict():
    """5.1 RED: a valid mapping YAML must return `(texto, dict)` (design D2)."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml", b"secciones: []", content_type="application/x-yaml"
    )

    texto, estructura = analizar_definicion_subida(archivo)

    assert texto == "secciones: []"
    assert estructura == {"secciones": []}


def test_analizar_definicion_subida_no_utf8_lanza_validation_error_archivo_yaml():
    """5.2 RED: non-UTF-8 bytes must raise `ValidationError` keyed
    `archivo_yaml`, never an uncaught `UnicodeDecodeError`."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml", b"\xff\xfe\x00\x01no-es-utf8", content_type="application/x-yaml"
    )

    with pytest.raises(ValidationError) as info:
        analizar_definicion_subida(archivo)

    assert "archivo_yaml" in info.value.message_dict


def test_analizar_definicion_subida_yaml_inseguro_python_object_apply_rechazado():
    """5.3 RED: unsafe YAML constructs (`!!python/object/apply`) must be
    rejected — Threat Matrix "Untrusted deserialization"."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml",
        b"!!python/object/apply:os.system ['echo pwned']",
        content_type="application/x-yaml",
    )

    with pytest.raises(ValidationError) as info:
        analizar_definicion_subida(archivo)

    assert "archivo_yaml" in info.value.message_dict


def test_analizar_definicion_subida_raiz_lista_rechazada():
    """5.4 RED: a YAML list root must be rejected (must be a mapping)."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml", b"- uno\n- dos\n", content_type="application/x-yaml"
    )

    with pytest.raises(ValidationError) as info:
        analizar_definicion_subida(archivo)

    assert "archivo_yaml" in info.value.message_dict


def test_analizar_definicion_subida_raiz_escalar_rechazada():
    """5.5 RED: a YAML scalar root must be rejected (must be a mapping)."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml", b"solo-un-string", content_type="application/x-yaml"
    )

    with pytest.raises(ValidationError) as info:
        analizar_definicion_subida(archivo)

    assert "archivo_yaml" in info.value.message_dict


def test_analizar_definicion_subida_no_representable_como_json_fecha_nativa_rechazada():
    """5.6 RED: a YAML-native date (parsed to a `datetime.date`, not
    JSON-representable) must be rejected."""
    from tipos_reporte.validacion import analizar_definicion_subida

    archivo = SimpleUploadedFile(
        "d.yaml", b"fecha: 2024-01-01", content_type="application/x-yaml"
    )

    with pytest.raises(ValidationError) as info:
        analizar_definicion_subida(archivo)

    assert "archivo_yaml" in info.value.message_dict


# ---------------------------------------------------------------------------
# Phase 6: forms.py — TipoDeReporteForm (design D4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tipo_de_reporte_form_plantilla_disabled_true_con_definicion_activa(
    tipo_de_reporte_factory, definicion_factory
):
    """6.1 RED: `plantilla.disabled` is True once `definicion_activa_id` is
    set (design D4)."""
    from tipos_reporte.forms import TipoDeReporteForm
    from tipos_reporte.models import Estado

    from django.utils import timezone

    from tipos_reporte.models import TipoDeReporte

    tipo = tipo_de_reporte_factory()
    activa = definicion_factory(
        tipo=tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )
    TipoDeReporte.objects.filter(pk=tipo.pk).update(definicion_activa=activa)
    tipo.refresh_from_db()

    form = TipoDeReporteForm(instance=tipo)

    assert form.fields["plantilla"].disabled is True


@pytest.mark.django_db
def test_tipo_de_reporte_form_plantilla_editable_sin_definicion_activa(
    tipo_de_reporte_factory,
):
    """6.2 RED: `plantilla` stays editable when the tipo has no active
    definición (spec "Plantilla is editable when no definition is active")."""
    from tipos_reporte.forms import TipoDeReporteForm

    tipo = tipo_de_reporte_factory()

    form = TipoDeReporteForm(instance=tipo)

    assert form.fields["plantilla"].disabled is False


@pytest.mark.django_db
def test_tipo_de_reporte_form_plantilla_posteada_en_tipo_activo_no_persiste(
    tipo_de_reporte_factory, definicion_factory
):
    """6.3 RED: a hand-crafted POST changing `plantilla` on an active tipo
    must not persist — Django substitutes the initial value for a disabled
    field (design D4, spec "Plantilla is read-only when a definition is
    active")."""
    from tipos_reporte.forms import TipoDeReporteForm
    from tipos_reporte.models import Estado, TipoDeReporte

    from django.utils import timezone

    tipo = tipo_de_reporte_factory()
    activa = definicion_factory(
        tipo=tipo, estado=Estado.ACTIVA, version=1, activada_en=timezone.now()
    )
    TipoDeReporte.objects.filter(pk=tipo.pk).update(definicion_activa=activa)
    tipo.refresh_from_db()
    plantilla_original = tipo.plantilla.name

    form = TipoDeReporteForm(
        data={
            "nombre": tipo.nombre,
            "codigo": tipo.codigo,
            "version_formato": tipo.version_formato,
        },
        files={"plantilla": SimpleUploadedFile("nueva.xlsx", b"contenido-nuevo")},
        instance=tipo,
    )

    assert form.is_valid(), form.errors
    guardado = form.save()

    assert guardado.plantilla.name == plantilla_original


# ---------------------------------------------------------------------------
# Phase 6: forms.py — DefinicionDeTipoForm (design D5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_definicion_de_tipo_form_yaml_valido_crea_borrador_con_yaml_fuente_y_estructura_derivados(
    tipo_de_reporte_factory,
):
    """6.4 RED: valid uploaded YAML -> `borrador` with `yaml_fuente`/
    `estructura` derived by the shared helper (spec "Administrator uploads a
    new definición draft")."""
    from tipos_reporte.forms import DefinicionDeTipoForm
    from tipos_reporte.models import Estado

    tipo = tipo_de_reporte_factory()
    archivo = SimpleUploadedFile(
        "d.yaml", b"secciones: []", content_type="application/x-yaml"
    )

    form = DefinicionDeTipoForm(data={}, files={"archivo_yaml": archivo})
    form.instance.tipo = tipo

    assert form.is_valid(), form.errors
    guardado = form.save()

    assert guardado.estado == Estado.BORRADOR
    assert guardado.yaml_fuente == "secciones: []"
    assert guardado.estructura == {"secciones": []}


@pytest.mark.django_db
def test_definicion_de_tipo_form_campos_estado_version_activada_en_ausentes_de_form_fields():
    """6.5 RED: `estado`/`version`/`activada_en` are absent from the form's
    fields entirely — not administrator-editable (design D5)."""
    from tipos_reporte.forms import DefinicionDeTipoForm

    form = DefinicionDeTipoForm()

    assert "estado" not in form.fields
    assert "version" not in form.fields
    assert "activada_en" not in form.fields
    assert "tipo" not in form.fields

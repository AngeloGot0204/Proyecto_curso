"""Create/edit forms for the tipos-de-reporte administration screen
(backlog #13, S-14, PR 2; spec `administracion-tipos-reporte`; design D4,
D5).

`TipoDeReporteForm` replicates `admin.py::TipoDeReporteAdmin.get_readonly_
fields`'s `plantilla`-readonly-once-active guard by EXCLUDING the field
from the form entirely once active (design D4, revised during manual
verification 2026-08-30) rather than `disabled=True`: a disabled
`FileField` still re-runs `clean()` on its bound initial value on every
submit, which calls `storage.size(name)` on the CURRENT default storage —
in `DEBUG` (`FileSystemStorage`), this crashes on a Blob URL persisted
under production's `VercelBlobStorage`. Excluding the field means
`ModelForm` never touches `instance.plantilla` on save, achieving the same
"locked" guarantee without ever re-validating it; the template renders the
current file as a plain link when `form.plantilla_bloqueada` is set.
`DefinicionDeTipoForm` narrows `fields` to `("archivo_yaml",)` and derives
`yaml_fuente`/`estructura` via the single shared `tipos_reporte.validacion.
analizar_definicion_subida` helper (design D5) — the same function
`admin.py::DefinicionDeTipoForm.clean()` calls until PR2's deregistration.
"""

from django import forms

from tipos_reporte.models import DefinicionDeTipo, TipoDeReporte
from tipos_reporte.validacion import analizar_definicion_subida


class TipoDeReporteForm(forms.ModelForm):
    """`nombre`, `codigo`, `version_formato`, `logo`, `plantilla` (spec
    "Create and Edit Forms for TipoDeReporte"). Logo-keep-on-no-reupload
    needs no code: the plain `ModelForm` + `ClearableFileInput` default
    already leaves `instance.logo` untouched when no file is posted
    (design D8). `plantilla` is removed from `self.fields` once the
    instance has an active definición (see module docstring for why
    `disabled=True` is unsafe here) — a hand-crafted POST cannot persist a
    change since `ModelForm.save()` only ever touches fields present in
    `self.fields` (design D4, direct port of `TipoDeReporteAdmin.
    get_readonly_fields`'s `obj.definicion_activa_id is not None`
    condition)."""

    class Meta:
        model = TipoDeReporte
        fields = ("nombre", "codigo", "version_formato", "logo", "plantilla")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plantilla_bloqueada = bool(
            self.instance.pk and self.instance.definicion_activa_id is not None
        )
        if self.plantilla_bloqueada:
            # Excluded, not merely `disabled=True`: a disabled FileField
            # still re-validates its bound initial value on every clean(),
            # calling `storage.size(name)` on the CURRENT default storage —
            # which in DEBUG (FileSystemStorage) chokes on a Blob URL
            # persisted under production's VercelBlobStorage. Excluding the
            # field from the form entirely means ModelForm never touches
            # `instance.plantilla` on save, achieving the same "locked"
            # guarantee without ever re-running FileField validation on it.
            del self.fields["plantilla"]


class DefinicionDeTipoForm(forms.ModelForm):
    """`archivo_yaml` only (design D5) — `tipo` is fixed by the URL
    (`form.instance.tipo = tipo` before `is_valid()`), and `estado`/
    `version`/`activada_en` are absent from the form entirely; they change
    only through `servicios.activar_definicion`/`desactivar_tipo` (spec
    "not administrator-editable"). `yaml_fuente`/`estructura` are derived
    on the instance in `clean()`, via the same shared helper `admin.py`
    calls (design D2, D5) — no reimplementation."""

    class Meta:
        model = DefinicionDeTipo
        fields = ("archivo_yaml",)

    def clean(self):
        cleaned = super().clean()
        archivo = cleaned.get("archivo_yaml")
        if archivo is not None:
            self.instance.yaml_fuente, self.instance.estructura = (
                analizar_definicion_subida(archivo)
            )
        return cleaned

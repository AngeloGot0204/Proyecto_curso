"""Django admin for `tipos_reporte` (design D4, D8, D9).

`DefinicionDeTipoAdmin` exposes an explicit "Activar definición" action
that calls `servicios.activar_definicion` — activation is never a side
effect of a plain save (design D8). `estado`/`version`/`activada_en` are
readonly: they change only through the service.

Delete guards are layered on top of the model-level guard that already
blocks `Model.delete()`/`QuerySet.delete()` (design D9, `models.py`).
Django calls `has_delete_permission(request, obj=None)` WITHOUT an object
when deciding whether to offer the changelist's bulk `delete_selected`
action, so an object-sensitive override alone would let that bulk action
slip past a protected row — `delete_selected` is removed from `actions`
entirely rather than trusted to the object-level check.
"""

import json

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from yaml import YAMLError

from tipos_reporte.models import DefinicionDeTipo, TipoDeReporte
from tipos_reporte.servicios import activar_definicion, desactivar_tipo
from tipos_reporte.validacion import analizar_yaml_seguro

DEFINICION_CAMPOS_DE_SOLO_LECTURA = ("estado", "version", "activada_en")
TIPO_CAMPOS_DE_SOLO_LECTURA = ("definicion_activa",)


class DefinicionDeTipoForm(forms.ModelForm):
    """Parses `archivo_yaml` at save time (design D4: "can this become a
    JSON document?", not "is this a valid definition?" — that gate is
    activation, not save). Only `yaml.safe_load` is used (Threat Matrix:
    untrusted deserialization).

    `yaml_fuente`/`estructura` are model-required fields, but they are
    DERIVED from `archivo_yaml` here in `clean()`, not entered by hand.
    Django's `_clean_fields()` runs its per-field "this field is required"
    check BEFORE `clean()` ever gets a chance to populate them, so they must
    be `required=False` at the form-field level — `clean()` is the single
    place that both derives and validates them, including raising when
    `archivo_yaml` itself is missing.
    """

    class Meta:
        model = DefinicionDeTipo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["yaml_fuente"].required = False
        self.fields["estructura"].required = False

    def clean(self):
        cleaned = super().clean()
        archivo = cleaned.get("archivo_yaml")
        if archivo is None:
            raise ValidationError(
                {"archivo_yaml": "Este campo es obligatorio."}
            )

        archivo.seek(0)
        try:
            texto = archivo.read().decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationError(
                {"archivo_yaml": f"El archivo no es texto UTF-8 válido: {error}"}
            )
        archivo.seek(0)

        try:
            estructura = analizar_yaml_seguro(texto)
        except YAMLError as error:
            raise ValidationError({"archivo_yaml": f"YAML inválido: {error}"})

        if not isinstance(estructura, dict):
            raise ValidationError(
                {"archivo_yaml": "El documento debe ser un mapeo en su raíz."}
            )
        try:
            json.dumps(estructura)
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "archivo_yaml": (
                        "El documento no es representable como JSON "
                        "(por ejemplo, contiene una fecha nativa de YAML)."
                    )
                }
            )

        cleaned["yaml_fuente"] = texto
        cleaned["estructura"] = estructura
        return cleaned


@admin.register(DefinicionDeTipo)
class DefinicionDeTipoAdmin(admin.ModelAdmin):
    form = DefinicionDeTipoForm
    list_display = ("tipo", "version", "estado", "activada_en")
    list_filter = ("estado", "tipo")
    readonly_fields = DEFINICION_CAMPOS_DE_SOLO_LECTURA
    actions = ("activar",)

    def get_actions(self, request):
        acciones = super().get_actions(request)
        acciones.pop("delete_selected", None)
        return acciones

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.activada_en is not None:
            return False
        return super().has_delete_permission(request, obj)

    @admin.action(description="Activar definición")
    def activar(self, request, queryset):
        for definicion in queryset:
            resultado = activar_definicion(definicion)
            if resultado.es_valida:
                self.message_user(
                    request,
                    f"{definicion}: activada correctamente.",
                    level=messages.SUCCESS,
                )
            else:
                for problema in resultado.problemas:
                    self.message_user(
                        request,
                        f"{definicion} — {problema.ubicacion}: {problema.mensaje}",
                        level=messages.ERROR,
                    )


@admin.register(TipoDeReporte)
class TipoDeReporteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activo", "definicion_activa")
    readonly_fields = TIPO_CAMPOS_DE_SOLO_LECTURA
    actions = ("desactivar",)

    def get_readonly_fields(self, request, obj=None):
        # Code-review fix: once `obj` has an active definition, `plantilla`
        # must become readonly too — changing it behind an active
        # definition's back would leave that definition pointing at cells
        # that no longer correspond to the new file, with no re-validation
        # or warning (design D1: real changes go through desactivar first).
        campos = super().get_readonly_fields(request, obj)
        if obj is not None and obj.definicion_activa_id is not None:
            return (*campos, "plantilla")
        return campos

    def get_actions(self, request):
        acciones = super().get_actions(request)
        acciones.pop("delete_selected", None)
        return acciones

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.definiciones.filter(
            activada_en__isnull=False
        ).exists():
            return False
        return super().has_delete_permission(request, obj)

    @admin.action(description="Desactivar tipo de reporte")
    def desactivar(self, request, queryset):
        for tipo in queryset:
            desactivar_tipo(tipo)
        self.message_user(request, "Tipo(s) desactivado(s).", level=messages.SUCCESS)

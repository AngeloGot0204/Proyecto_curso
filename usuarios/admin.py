from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """is_staff is derived by Usuario.save() from rol, so it is shown as
    read-only here — editing it directly would be silently overwritten
    on the next save."""

    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("rol",)}),)
    readonly_fields = UserAdmin.readonly_fields + ("is_staff",)
    list_display = ("username", "email", "rol", "is_staff", "is_active")

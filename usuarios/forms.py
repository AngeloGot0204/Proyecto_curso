"""Forms for the users administration screen (BACKLOG.md #1, S-13: "admin de
usuarios: buscador, crear, editar rol/organización, resetear contraseña,
suspender"). Mirrors `tipos_reporte/forms.py`'s plain `ModelForm` convention
— no DRF, no custom widgets beyond what Django provides.

`organización` has no backing model anywhere in this codebase (confirmed by
grep) — only `rol` is editable here, per the task's explicit "if it doesn't
exist, don't invent it" instruction.
"""

from django import forms
from django.contrib.auth import password_validation

from usuarios.models import Usuario


class UsuarioCrearForm(forms.ModelForm):
    """Admin-creates-account form (this app has no self-registration —
    BACKLOG.md #1's "admin crea cuentas" is this feature). `password` is a
    plain `CharField` validated with Django's `password_validation` and
    hashed via `set_password` in the view/`save()`, never stored in plain
    text."""

    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput, strip=False
    )

    class Meta:
        model = Usuario
        fields = ("username", "rol")
        # `username` keeps the model field's `UnicodeUsernameValidator`/
        # `max_length` — only the label/help text (Django's untranslated
        # English defaults) are overridden here, not the field itself.
        labels = {"username": "Nombre de usuario"}
        help_texts = {
            "username": "150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente."
        }

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password)
        return password

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    """`rol` only (spec: "editar rol/organización" — organización has no
    model to edit)."""

    class Meta:
        model = Usuario
        fields = ("rol",)


class ResetearPasswordForm(forms.Form):
    """Admin sets a new password without knowing the old one — a plain
    unbound `Form`, not a `ModelForm`, since it never touches any field but
    the hashed password."""

    nueva_password = forms.CharField(
        label="Nueva contraseña", widget=forms.PasswordInput, strip=False
    )

    def clean_nueva_password(self):
        password = self.cleaned_data["nueva_password"]
        password_validation.validate_password(password)
        return password

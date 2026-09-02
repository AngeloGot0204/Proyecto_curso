"""Vacía la base y deja un único administrador: estado de demostración.

## Por qué `flush` y no borrados por modelo

La primera versión de este script borraba con el ORM. No funciona, y la razón
es una decisión deliberada del proyecto: `DefinicionDeTipoQuerySet.delete()` y
`TipoDeReporteQuerySet.delete()` rechazan borrar cualquier definición o tipo que
haya sido activado alguna vez (diseño D9). Una definición activada es parte del
rastro de auditoría de los reportes que la usaron.

Esa guarda está bien y no se saltea con SQL crudo desde acá. `manage.py flush`
es la herramienta que Django trae exactamente para esto: trunca las tablas a
nivel de base, sin pasar por la lógica de modelos, y vuelve a disparar
`post_migrate` para recrear content types y permisos.

La distinción importa: no estamos "esquivando" la guarda, estamos usando una
operación distinta. La guarda protege el borrado selectivo dentro de un sistema
vivo. Esto reinicia el sistema entero.

## Qué queda después

Base vacía, con el esquema intacto, y un solo `Usuario` administrador. **No
queda ningún tipo de reporte**: quien entre tendrá que cargar un YAML y su
plantilla `.xlsx` antes de poder crear el primer reporte. Para una demo eso es
una ventaja — el recorrido completo muestra el motor de definiciones, que es lo
que distingue a este producto de un formulario cualquiera.

Los archivos ya subidos a Vercel Blob quedan huérfanos. No se borran acá: son
inalcanzables sin sus filas y su costo es despreciable.

## Uso

    python scripts/preparar_demo.py                    # simulacro
    python scripts/preparar_demo.py --aplicar
    python scripts/preparar_demo.py --aplicar --usuario admin --password X

Simulacro por defecto. Imprime siempre la base contra la que va a operar:
verificala antes de pasar `--aplicar`. Esto borra todo y no hay deshacer.
"""

import argparse
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402

from reportes.models import Adjunto, Reporte  # noqa: E402
from tipos_reporte.models import DefinicionDeTipo, TipoDeReporte  # noqa: E402
from usuarios.models import Rol, Usuario  # noqa: E402

_MODELOS = (Usuario, TipoDeReporte, DefinicionDeTipo, Reporte, Adjunto)


def _inventario():
    return {m.__name__: m.objects.count() for m in _MODELOS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()

    print(f"Base : {connection.settings_dict['HOST']}")
    print(f"Modo : {'APLICAR (BORRA TODO)' if args.aplicar else 'SIMULACRO'}")
    print()
    print("Estado actual:")
    for nombre, cantidad in _inventario().items():
        print(f"  {nombre:20} {cantidad}")

    if not args.aplicar:
        print()
        print("Quedaria: todo en 0, mas un administrador " + args.usuario)
        print("Simulacro. Volve a correrlo con --aplicar para ejecutar.")
        return

    call_command("flush", interactive=False, verbosity=0)

    admin = Usuario(username=args.usuario, rol=Rol.ADMINISTRADOR)
    admin.set_password(args.password)
    # `is_staff` lo deriva `Usuario.save()` desde `rol`. `is_superuser` queda en
    # False a propósito: el rol de administrador ya abre todo lo que la
    # aplicación gatea, y un superusuario sortearía permisos que una demo no
    # necesita sortear.
    admin.save()

    print()
    print("Estado final:")
    for nombre, cantidad in _inventario().items():
        print(f"  {nombre:20} {cantidad}")
    print()
    print(f"Listo. Administrador '{args.usuario}', rol {admin.rol}.")


if __name__ == "__main__":
    main()

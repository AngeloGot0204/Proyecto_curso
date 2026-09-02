"""Sube a Vercel Blob los archivos cuya referencia quedó como ruta local.

## Por qué existe

`VercelBlobStorage` guarda la URL pública completa del blob como "nombre" del
archivo. `FileSystemStorage` guarda una ruta relativa a `MEDIA_ROOT`. Los dos
escriben en la misma columna, y cuál se usa depende de `DEBUG`.

El desarrollo local corrió con `DEBUG=True` (FileSystemStorage) apuntando a la
base de PRODUCCIÓN. Resultado: el archivo quedó en el disco del desarrollador y
la ruta relativa quedó escrita en la base compartida. En producción, con
`DEBUG=False`, `VercelBlobStorage._open()` hace `requests.get(nombre)` sobre esa
ruta relativa, falla, y la generación del documento muere con
`PlantillaIlegible` — que el usuario ve como "No se pudo generar el documento".

Este script repara los datos. No repara la causa: mientras el entorno local
apunte a la base de producción, el problema se reproduce en la siguiente subida.

## Qué hace

Para cada referencia que NO empiece con `http`, lee el archivo desde
`MEDIA_ROOT`, lo sube a Blob y reemplaza el nombre en la base por la URL
resultante.

Es idempotente: una referencia que ya es una URL se ignora, así que volver a
correrlo no duplica nada. Un archivo ausente del disco se reporta y se salta,
nunca aborta el resto.

## Uso

    python scripts/reparar_referencias_de_archivo.py            # simulacro
    python scripts/reparar_referencias_de_archivo.py --aplicar  # escribe

Simulacro por defecto, a propósito: este script toca datos y hay que poder ver
qué haría antes de que lo haga.

Imprime siempre el host de la base contra la que va a operar. Verificalo antes
de pasar `--aplicar`: la razón de este arreglo es justamente haber escrito en la
base equivocada.
"""

import argparse
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402

import vercel_blob.blob_store as blob_store  # noqa: E402

from reportes.models import Adjunto  # noqa: E402
from tipos_reporte.models import DefinicionDeTipo, TipoDeReporte  # noqa: E402


def _objetivos():
    """(objeto, nombre_del_campo) por cada FileField del proyecto."""
    for tipo in TipoDeReporte.objects.all():
        yield tipo, "plantilla"
        yield tipo, "logo"
    for definicion in DefinicionDeTipo.objects.all():
        yield definicion, "archivo_yaml"
    for adjunto in Adjunto.objects.all():
        yield adjunto, "archivo"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Escribe los cambios. Sin este flag solo simula.",
    )
    args = parser.parse_args()

    print(f"Base : {connection.settings_dict['HOST']}")
    print(f"Media: {settings.MEDIA_ROOT}")
    print(f"Modo : {'APLICAR (escribe)' if args.aplicar else 'SIMULACRO'}")
    print()

    if args.aplicar and not os.environ.get("BLOB_READ_WRITE_TOKEN"):
        sys.exit("Falta BLOB_READ_WRITE_TOKEN en el entorno.")

    reparados = ya_ok = vacios = ausentes = 0

    for objeto, campo in _objetivos():
        archivo = getattr(objeto, campo)
        nombre = archivo.name
        etiqueta = f"{type(objeto).__name__}#{objeto.pk}.{campo}"

        if not nombre:
            vacios += 1
            continue
        if nombre.startswith("http"):
            ya_ok += 1
            continue

        origen = Path(settings.MEDIA_ROOT) / nombre
        if not origen.exists():
            ausentes += 1
            print(f"  AUSENTE   {etiqueta}: {nombre}")
            continue

        if not args.aplicar:
            reparados += 1
            print(f"  subiria   {etiqueta}: {nombre}")
            continue

        resultado = blob_store.put(
            nombre, origen.read_bytes(), {"addRandomSuffix": "true"}
        )
        setattr(objeto, campo, resultado["url"])
        objeto.save(update_fields=[campo])
        reparados += 1
        print(f"  reparado  {etiqueta}: {resultado['url'][:70]}...")

    print()
    print(
        f"reparados={reparados}  ya_en_blob={ya_ok}  "
        f"vacios={vacios}  ausentes_del_disco={ausentes}"
    )
    if not args.aplicar and reparados:
        print("\nSimulacro. Volvé a correrlo con --aplicar para escribir.")


if __name__ == "__main__":
    main()

"""Custom Django storage backend for Vercel Blob.

Vercel's serverless functions run on a read-only filesystem (except /tmp),
so Django's default FileSystemStorage cannot persist uploaded files
(TipoDeReporte.plantilla/logo, DefinicionDeTipo.archivo_yaml) in production.
This backend stores files in Vercel Blob instead, using the full public
blob URL as the stored "name" — url() then returns it as-is.
"""

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

import vercel_blob.blob_store as blob_store


@deconstructible
class VercelBlobStorage(Storage):
    def _save(self, name, content):
        data = content.read()
        resultado = blob_store.put(name, data, {"addRandomSuffix": "true"})
        return resultado["url"]

    def _open(self, name, mode="rb"):
        respuesta = requests.get(name, timeout=30)
        respuesta.raise_for_status()
        return ContentFile(respuesta.content, name=name)

    def exists(self, name):
        # Blob URLs are content-addressed with addRandomSuffix, so every
        # upload gets a fresh name — never treat one as already existing.
        return False

    def url(self, name):
        return name

    def delete(self, name):
        blob_store.delete(name)

    def size(self, name):
        info = blob_store.head(name)
        return info["size"]

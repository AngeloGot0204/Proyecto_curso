"""Tests de `tipos_reporte.plantilla_base` (defecto del 2026-09-01).

La plantilla original del cliente traía 67 partes, imágenes WMF que openpyxl
descarta y `customXml` heredado. Al guardarla, openpyxl reserializaba el
paquete completo y producía un `.xlsx` que Excel abría con el diálogo
"Parte quitada: /xl/drawings/drawing1.xml (Forma de dibujo)".

La plantilla base se autora desde código para que el archivo que openpyxl
escribe sea exactamente el que openpyxl vuelve a leer. Estos tests fijan esa
propiedad y la estructura del formato oficial.
"""

import io
import zipfile

import openpyxl

from tipos_reporte.plantilla_base import HOJA, construir


def _guardar(libro):
    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer


def test_plantilla_base_es_estable_ante_round_trip_de_openpyxl():
    """La propiedad que resuelve el defecto: abrir y volver a guardar no
    cambia el conjunto de partes del paquete. Con la plantilla original esto
    era falso — se perdían `customXml`, `printerSettings` y `sharedStrings`, y
    los dibujos se reserializaban con el namespace equivocado."""
    primero = _guardar(construir())
    partes_iniciales = sorted(zipfile.ZipFile(primero).namelist())

    primero.seek(0)
    segundo = _guardar(openpyxl.load_workbook(primero))

    assert sorted(zipfile.ZipFile(segundo).namelist()) == partes_iniciales


def test_plantilla_base_no_arrastra_partes_heredadas():
    """Sin `customXml`, sin `printerSettings` binarios y sin dibujos: son
    justamente las partes que openpyxl no sabía reserializar."""
    partes = zipfile.ZipFile(_guardar(construir())).namelist()

    assert not [p for p in partes if "customXml" in p]
    assert not [p for p in partes if "printerSettings" in p]
    assert not [p for p in partes if "drawing" in p]


def test_plantilla_base_conserva_la_identidad_del_formato_oficial():
    """El PRD exige reproducir el formato de referencia: mismo nombre de
    hoja, mismo código de registro y misma área de impresión."""
    hoja = construir()[HOJA]

    assert hoja["R2"].value == "JME.SGC.18138.PC-0001-F1"
    assert hoja.print_area == f"'{HOJA}'!$B$2:$V$65"
    assert hoja.page_setup.orientation == "portrait"
    assert hoja.sheet_properties.pageSetUpPr.fitToPage is True


def test_plantilla_base_no_declara_rangos_combinados_de_una_celda():
    """Un rango `B25:B25` no aporta nada y hacía crashear al validador
    (ver `test_mapa_de_celdas_no_ancla_soporta_rango_combinado_de_una_celda`).
    La plantilla no debe generar ninguno."""
    hoja = construir()[HOJA]

    de_una_celda = [
        rango.coord
        for rango in hoja.merged_cells.ranges
        if rango.min_row == rango.max_row and rango.min_col == rango.max_col
    ]

    assert de_una_celda == []

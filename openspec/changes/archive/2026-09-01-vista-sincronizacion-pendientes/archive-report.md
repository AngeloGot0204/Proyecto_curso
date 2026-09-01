# Cierre: Aggregated Synchronization Screen (S-15)

**Estado: cerrado y archivado — 2026-09-01.**

## Qué se entregó

Todo el alcance de código está implementado y verificado en disco:

| Pieza | Archivo |
|---|---|
| Helper de envío extraído | `reportes/static/reportes/envio-paso.js` |
| Metadatos de borrador (`tipoNombre`/`fechaReporte`) | `reportes/static/reportes/paso-offline.js`, `paso.html` |
| Ruta y vista S-15 | `reportes/urls.py`, `reportes/views.py::sincronizacion` |
| Pantalla | `reportes/templates/reportes/sincronizacion.html` |
| Lista agregada + reintento por fila | `reportes/static/reportes/sincronizacion.js` |
| Badge de entrada en Mis reportes | `reportes/static/reportes/pendientes-badge.js`, `mis_reportes.html` |
| Service worker | `sw.js` (`CACHE = "reportes-offline-v20"`, ruta S-15 cacheada) |

La spec pasó a `openspec/specs/sincronizacion-pendientes/spec.md`.

## Evidencia automatizada

Suite completa en verde: 366 tests (repo completo excluyendo `test_views.py`)
más 112 en `test_views.py`. Ninguna regresión atribuible a este cambio.

## Verificación manual pendiente — NO cerrada

Cinco chequeos de este change requieren un navegador real con throttling de red
en DevTools. Este proyecto no tiene runner de JS (está declarado en el Out of
Scope de la spec) y no se pueden simular desde la suite de Python, así que
**quedan sin verificar y necesitan una pasada humana**:

| Task | Qué falta comprobar |
|---|---|
| 1.4 | Enviar un paso online / offline / con sesión expirada y confirmar que el comportamiento es idéntico al previo a extraer `envio-paso.js` |
| 2.4 | Inspeccionar una fila escrita en `borradores` y confirmar que lleva `tipoNombre` y `fechaReporte`, y que las filas legacy siguen siendo válidas |
| 4.3 | Con 2+ reportes con filas pendientes/fallidas: lista completa, una sola acción por fila, y los caminos de reintento exitoso / fallido / sesión expirada sin duplicar `Reporte` |
| 5.4 | 3 filas pendientes muestran badge "3"; 0 filas lo ocultan; el click navega a S-15 |
| 6.3 | Cargar S-15 online una vez, pasar a offline y recargar: la pantalla se sirve desde cache |

Se archiva igual porque el contrato de código está implementado y cubierto por
la parte automatizable. Estos cinco puntos son verificación de comportamiento en
navegador, no trabajo pendiente de implementación.

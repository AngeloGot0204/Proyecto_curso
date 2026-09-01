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

## Verificación manual — completada 2026-09-01

Los cinco chequeos que requerían un navegador real fueron ejecutados y **pasan**:

| Task | Resultado |
|---|---|
| 1.4 | Online guarda y navega; offline encola con banner "Sin conexión — pendiente de subir"; sesión expirada navega al login conservando el borrador |
| 2.4 | La fila en `borradores` lleva `tipoNombre` y `fechaReporte` con valor real |
| 4.3 | Lista con filas de 2 reportes distintos, una sola acción por fila; reintento exitoso borra la fila y el servidor confirma 20 valores guardados sin duplicar `Reporte`; reintento fallido conserva las filas |
| 5.4 | Badge muestra "1" con una fila pendiente, desaparece al vaciarse la cola, y navega a S-15 |
| 6.3 | Con S-15 ya visitada, offline + recarga sirve la pantalla desde cache |

Sub-caso no cubierto: 2.4 pide además confirmar que las filas **legacy**
(escritas antes de este cambio) siguen siendo válidas. No había ninguna en la
base local, así que ese punto queda sin comprobar.

---

## Defecto encontrado: metadatos perdidos al reintentar

**Severidad: rompe dos requirements de la spec viva.**

Al reintentar un envío que falla, la fila pierde `tipoNombre` y `fechaReporte`:

```
antes del reintento:  Reporte de Verificación de Instalación de Pernos con Resina
                      Sept. 1, 2026, 5:40 p.m. · resultados

después:              Reporte
                      · resultados
```

**Causa.** `envio-paso.js` reescribe la fila con `db.borradores.put()` pasando
un objeto literal que solo contiene los campos que ese helper conoce
(`reporteId`, `seccionId`, `valores`, `actualizadoEn`, `estado`, `intentos`,
`ultimoError`). Dexie reemplaza el registro completo, así que todo campo ausente
del literal se borra. Ocurre en los dos puntos de escritura del helper:
`reconciliarEnEnvio` y `reconciliarResultado`.

**Por qué no se detectó antes.** `paso-offline.js` sí escribe los metadatos al
crear el borrador, así que la primera vez la fila se ve bien. `envio-paso.js` se
extrajo como helper compartido en la fase 1 de este cambio, y los metadatos se
agregaron en la fase 2 — el helper nunca se enteró de esos dos campos. Además el
camino feliz lo esconde: si el envío sale `ok` la fila se borra y la degradación
nunca se ve. Solo aparece cuando falla, que es justo cuando el usuario necesita
leer de qué reporte se trata.

**Requirements violados** (`openspec/specs/sincronizacion-pendientes/spec.md`):
"Per-Row Display Metadata" y "Draft Write Captures Display Metadata".

**Arreglado el 2026-09-01.** Se agrega `fusionarEnBorrador()` en
`envio-paso.js`: lee la fila previa y fusiona los campos gestionados sobre
ella (`Object.assign`), en vez de reemplazar el registro. Los dos puntos de
escritura pasan por ahí. La fusión deja el contrato abierto: un campo que
agregue cualquier otro escritor en el futuro sobrevive sin que este helper
tenga que enterarse.

Cubierto por `test_envio_paso_js_preserva_campos_no_gestionados_del_borrador`
(tripwire de fuente, porque el proyecto no tiene runner de JS) y verificado en
navegador: tras un reintento fallido la fila conserva tipo y fecha.

Se subió el cache del service worker a `v21` para que los clientes tomen el JS
corregido en vez del cacheado.

---

## Hueco de navegación: S-15 es inalcanzable offline

Técnicamente el service worker cachea tanto las páginas de paso como
`/reportes/sincronizacion/`, así que la pantalla **carga** sin conexión. El
problema es llegar a ella.

El único enlace a S-15 en toda la aplicación es el badge de
`mis_reportes.html`, y "Mis reportes" **no está cacheada**: offline devuelve el
error de red. El resultado es que el escenario para el que S-15 fue construida
es exactamente el que no puede alcanzarla:

```
Estás en el formulario, sin señal, con pasos pendientes
  → querés ver la cola
  → el único enlace vive en Mis reportes
  → Mis reportes no carga offline
  → sin salida, salvo saber la URL de memoria
```

El banner de pendientes que aparece en el paso avisa del problema pero no
enlaza a la pantalla que lo resuelve.

Ninguna spec cubre este caso, así que no es un incumplimiento: es un hueco de
diseño. El arreglo más directo es enlazar S-15 desde ese banner, donde el
usuario ya está mirando cuando le ocurre.

---

## Nota metodológica: cómo probar la sesión expirada

Borrar `sessionid` desde DevTools **no reproduce** una expiración de sesión: la
herramienta se lleva también la cookie `csrftoken`, y sin ella Django rechaza el
POST con `403 CSRF cookie not set` **antes** de que la petición llegue a la
vista. Nunca se ejecuta el `login_required` que produce el 302 al login, así que
el código clasifica el resultado como `fallo` en vez de `sesion_expirada`.

Una expiración real no se comporta así: `sessionid` dura 7 días y `csrftoken`
un año, de modo que la sesión muere con la cookie de CSRF todavía presente.

**Para probarlo hay que borrar únicamente `sessionid`, dejando `csrftoken`
intacta.** Hecho así, el flujo funciona: navega al login y conserva el borrador.

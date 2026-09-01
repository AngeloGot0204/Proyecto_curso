# ADR 0004: Offline con IndexedDB, service worker y sincronización por sección de rol

## Estado

Aceptado

## Contexto

El PRD incluye en el alcance la "captura de datos en campo sin conexión (modo offline): el
formulario debe poder completarse sin internet y sincronizarse/subirse cuando el dispositivo
recupere conexión", y fija el mecanismo de sincronización a nivel de producto: mientras el reporte
está sin conexión sólo tiene un ID local generado en el dispositivo; el número de registro oficial
lo asigna el servidor al sincronizar, en orden de llegada; ese mismo ID local evita duplicados
ante reintentos.

El DESIGN eleva el offline a principio de diseño ("Offline es el caso normal, no la excepción") y
lo materializa en varias pantallas: S-01 permite entrar en modo offline con sesión previa y datos
cacheados, S-02 muestra un banner de pendientes de subir, S-04 muestra "guardado local ✓" en el
encabezado, S-15 lista la cola con estados (`local`, `falló 2v`) y reintento manual, y el estado
`borrador local` encabeza el ciclo de vida del reporte.

Dos restricciones acotan las opciones técnicas:

1. La ADR-0001 fijó una capa offline propia en JavaScript vanilla, sin frameworks de frontend.
2. La pantalla S-08 permite adjuntar una imagen de croquis o evidencia, de modo que el
   almacenamiento local debe soportar datos binarios, no sólo texto.

## Decisión

Implementar el modo offline con tres piezas:

1. **Borrador local en IndexedDB**, con **Dexie.js** como capa sobre IndexedDB (decisión #6 de
   RESOLUCION-ADVERSARIAL.md). Cada cambio de campo persiste en el dispositivo, de forma que
   "Atrás" nunca pierde datos y el trabajo sobrevive al cierre de la aplicación.
2. **Service worker** **(corrección 2026-09-01: escrito a mano, sin dependencias — no Workbox;
   ver `reportes/templates/reportes/sw.js`)**, que cachea el app shell y los
   recursos estáticos, permitiendo abrir y operar la aplicación sin señal cuando ya existe una
   sesión previa. Lo que se cachea para cada tipo de reporte es la **página del wizard ya
   renderizada en HTML por Django** (ADR-0001) — no una definición JSON/YAML que el navegador
   tenga que interpretar para armar el formulario.
3. **Cola de subida con envío por sección de rol.** La sincronización se dispara cuando el usuario
   **termina la parte que le corresponde**, enviando ese bloque completo en una sola operación,
   identificada por el ID local del reporte como clave de idempotencia. La **validación fuerte de
   los campos ocurre en este paso, en el servidor**; el navegador no valida contra la definición
   mientras está offline, sólo guarda lo que el usuario escribe.

**Dexie.js y Workbox no violan la restricción de la ADR-0001** ("sin frameworks de frontend ni
build pipeline"): son bibliotecas que se cargan por `<script>` tag, sin build pipeline propio, no
frameworks de UI ni de aplicación — cubren únicamente IndexedDB y el ciclo de vida del service
worker, que es exactamente el problema para el que se eligieron.

El contrato entre la capa JavaScript y Django se limita a un conjunto reducido de endpoints JSON
(sincronizar sección de rol, consultar estado del reporte, solicitar generación). Al tratarse de
un único despliegue (ADR-0001), este contrato es interno y no requiere versionado público.

**Colaboración offline sobre un reporte ajeno: no soportada (decisión #3 de
RESOLUCION-ADVERSARIAL.md).** El modo offline cubre la captura de datos propios sin señal; no
cubre trabajar sin conexión sobre un reporte compartido mientras otro participante podría estar
editándolo al mismo tiempo. Esa colaboración simultánea es **estrictamente online**: requiere
conexión para conocer y respetar el bloqueo de edición descrito en la ADR-0006 **(nota 2026-09-01:
ese bloqueo no está implementado — ver la corrección en ADR-0006)**.

**Correlativo del reporte: generado por secuencia de base de datos (decisión #9 de
RESOLUCION-ADVERSARIAL.md).** El número de registro oficial (`numero_registro`) que el servidor
asigna al sincronizar se genera con una **secuencia de base de datos** (`nextval`, no un `max() +
1` calculado en código Python), para eliminar la ventana de condición de carrera entre sincronizaciones
concurrentes. Adicionalmente, `Reporte.id_local` lleva una restricción `unique` en la base de
datos, de modo que la idempotencia del ID local no depende sólo de la lógica de la vista, sino que
la propia base de datos la garantiza.

**Adjuntos: compresión, límite y almacenamiento (decisión #13 de RESOLUCION-ADVERSARIAL.md).** Las
imágenes adjuntas (croquis, evidencia) se comprimen **automáticamente en el dispositivo antes de
subir**, sin acción del usuario. No se fija un límite de tamaño explícito: la compresión ya lo
acota indirectamente a un rango manejable para la cola de subida. Los adjuntos sincronizados se
almacenan en **Vercel Blob** (ADR-0009), consistente con el resto de archivos generados por la
aplicación.

**Versión de la plantilla en el borrador local (decisión #18 de RESOLUCION-ADVERSARIAL.md).** El
borrador local guarda, junto a sus valores, la **versión de la definición del tipo de reporte**
(ADR-0003) vigente en el momento de crearse. Si esa versión cambió en el servidor antes de que el
borrador sincronice, la sincronización **no** guarda los datos silenciosamente contra celdas que
pueden haberse movido: se avisa al usuario para que decida, en vez de arriesgar un mapeo
campo→celda desactualizado.

## Alternativas consideradas

- **`localStorage` como almacén local en lugar de IndexedDB** — su API es notablemente más simple
  y habría reducido la dificultad de la parte más costosa del proyecto. Se descartó porque sólo
  almacena texto y su cupo ronda los 5 MB, insuficiente para la imagen de croquis o evidencia que
  el DESIGN exige en S-08. Mantener dos almacenes distintos (texto en `localStorage`, imágenes en
  IndexedDB) se consideró peor que usar IndexedDB para todo.

- **Sincronización campo por campo (o paso por paso) del wizard** — resulta más robusta ante
  cortes de conexión a mitad de una sección y acortaría la ventana de datos no sincronizados. Se
  descartó por complejidad desproporcionada: obliga a gestionar orden de llegada, secciones
  parcialmente sincronizadas y estados intermedios que el DESIGN no contempla. El borrador local
  ya protege el trabajo desde el primer campo, de modo que sincronizar con mayor frecuencia no
  evita ninguna pérdida real de datos.

- **Sincronización automática en segundo plano mediante Background Sync API** — habría eliminado
  la necesidad de reintento manual. Se descartó porque su soporte entre navegadores es desigual,
  contradice el principio del DESIGN de que la sincronización sea visible y reintentable por el
  usuario (S-15), y añade un mecanismo difícil de depurar para un desarrollador en solitario.

## Consecuencias

- El trabajo del usuario queda a salvo en el dispositivo desde el primer campo completado, con
  independencia de la conectividad.
- El envío en una sola operación por sección de rol simplifica el manejo de fallos: si falla, se
  reintenta el bloque entero, sin estados intermedios que reconciliar.
- La clave de idempotencia basada en el ID local hace que los reintentos sean seguros por diseño,
  cumpliendo la regla de "sin duplicar por reintento" que el DESIGN anuncia en S-15.
- El almacenamiento en IndexedDB soporta los adjuntos de imagen sin necesidad de un segundo
  mecanismo.
- **Costo real:** el envío único crece con el peso de los adjuntos. Con fotos pesadas y
  conectividad pobre, la subida tarda más y tiene mayor probabilidad de fallar completa, lo que
  vuelve más visible el reintento manual de S-15. Se mitiga comprimiendo las imágenes en el
  dispositivo antes de encolarlas (ver decisión sobre adjuntos más arriba), aunque no elimina el
  costo por completo con conexiones muy pobres.
- **Costo real:** IndexedDB tiene una API asíncrona y verbosa, claramente más difícil que
  `localStorage` para quien no domina JavaScript. Es la materialización concreta del costo ya
  asumido en la ADR-0001.
- **Costo real:** el almacenamiento del navegador no es permanente — el sistema operativo puede
  purgarlo bajo presión de espacio y el usuario puede borrar los datos del sitio. Un reporte que
  vive únicamente como borrador local y nunca se sincroniza es un reporte en riesgo, algo que la
  interfaz debe comunicar con claridad en la cola de pendientes.
- **Costo real:** existe una ventana entre "termino mi parte" y "sincronizo" durante la cual el
  rol siguiente no puede ver ni continuar el reporte, consecuencia directa de la regla de handoff
  establecida en el PRD y detallada en la ADR siguiente.

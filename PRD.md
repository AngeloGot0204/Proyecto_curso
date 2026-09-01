---
title: "Generador de Reportes de Campo (a partir de plantillas)"
---

# PRD: Generador de Reportes de Campo (a partir de plantillas)

## Problema

Existen reportes operativos con estructura fija y repetitiva (control de calidad, inspección,
instalación de materiales, etc.) que hoy se elaboran manualmente en Excel: la persona abre una
plantilla, completa decenas de campos a mano, copia datos de otras fuentes, hace cálculos
puntuales (tiempos transcurridos, conteos, promedios) y arma el documento final respetando un
formato exigido por control de calidad / cliente.

Este proceso es lento, propenso a errores (campos olvidados, fórmulas rotas, formato roto al
copiar/pegar) y depende de que cada persona sepa manejar bien esa plantilla de Excel específica.
No hay validación de datos antes de "cerrar" el reporte, ni un flujo claro de revisión antes de
entregarlo.

Caso de referencia analizado: `REPORTE DE INSTALACION DE RESINAS (1).xlsx`, un reporte real de
Consorcio JME / Compañía Minera Antamina, formato `JME.SGC.18138.PC-0001-F1`
("Reporte de Verificación de Instalación de Pernos de Anclajes con Resina"). Contiene:

- Encabezado institucional (proyecto, compañía, N° contrato, plano ref., área, frente, sistema,
  turno, tipo de roca, etc.) — ~18 campos de identificación.
- Checklist de "Parámetros preliminares" (7 ítems Sí/No con columnas de verificación por rol:
  Consorcio JME / QA Subterra, + observación).
- Checklist de "Proceso de instalación de resinas" (11 ítems, con hora inicio/hora término y
  observación por rol).
- Checklist de "Ensayo de Pull Test" (4 ítems: fuerza de tracción aplicada, tiempo transcurrido,
  desplazamiento del perno, con hora inicio/término).
- "Resultados de la prueba" (3 verificaciones finales con roles: QC JME / QA Antamina).
- Espacio de croquis (dibujo libre de la zona de trabajo) y observaciones generales.
- Bloque de firmas (4 roles: Construcción JME, QC JME, QA Subterra, Construcción Antamina — cada
  uno con firma, nombre, fecha).

Además, el mismo archivo Excel contiene otras hojas ocultas con **otro tipo de reporte distinto**
(un "Plan de Puntos de Inspección y Ensayos" para Shotcrete/concreto lanzado, con su propia
estructura de columnas: actividad, punto de inspección, criterio de aceptación, estándar de
registro, responsabilidades por rol). Esto confirma que el problema no es "un solo formato de
Excel": en la práctica ya conviven varios formatos de reporte con estructura similar pero
contenido distinto dentro de la misma operación.

Por ahora se trabajará solo con estos dos formatos identificados; se agregarán más tipos de
reporte más adelante si la operación lo requiere.

## Usuario objetivo

Personal de campo / control de calidad (QA/QC) en proyectos de construcción o minería
(supervisores, inspectores de calidad, personal de construcción) que completa estos reportes
directamente en campo, durante o inmediatamente después de la actividad (instalación de pernos,
aplicación de shotcrete, etc.), típicamente desde celular o tablet, con conectividad limitada o
intermitente en el sitio.

La app tiene dos roles: **administrador** (crea y gestiona usuarios, gestiona tipos de reporte
disponibles) y **usuario** (completa y genera reportes). No hay auto-registro: las cuentas de
usuario las crea el administrador.

## Objetivo / resultado esperado

Que la persona complete un formulario guiado (en vez de editar un Excel) y obtenga
automáticamente el reporte final ya armado, con la estructura, cálculos y formato correctos,
listo para revisar y descargar — reduciendo tiempo de elaboración y errores de formato/cálculo
respecto al llenado manual en Excel.

## Alcance (qué sí incluye esta versión)

- Selección de tipo de reporte a generar (aunque el MVP soporte inicialmente un solo tipo real:
  "Reporte de Verificación de Instalación de Pernos de Anclajes con Resina").
- Formulario de captura de datos organizado por secciones equivalentes a las del Excel:
  datos generales del proyecto, checklist de parámetros preliminares, checklist del proceso de
  instalación (con horas), checklist de pull test, resultados finales, observaciones.
- Validación de datos antes de permitir generar el reporte (campos obligatorios, formato de
  hora/fecha, rangos numéricos básicos donde aplique).
- Cálculos automáticos que hoy se hacen a mano o por fórmula en Excel (p. ej. tiempo transcurrido
  entre hora inicio y hora término de cada bloque).
- Generación automática del documento final en formato Excel, replicando de forma exacta la
  estructura, celdas combinadas, y formato visual del archivo de referencia (encabezado
  institucional, checklists, resultados, firmas). El logo institucional es configurable: el
  administrador puede subir una imagen de logo por tipo de reporte/cliente, en vez de estar
  hardcodeado.
- Pantalla de validación al cerrar el reporte: lista los errores que bloquean la generación y las
  advertencias que no, con enlace al campo exacto. **No hay vista previa del documento dentro de
  la app** (ver ADR-0007): el usuario revisa sus datos volviendo por los pasos del formulario y
  ve el resultado final al abrir el `.xlsx` descargado.
- Descarga del reporte generado en formato Excel (`.xlsx`), idéntico en formato al archivo de
  referencia.
- App web responsiva, usable tanto desde escritorio como desde celular/tablet.
- Captura de datos en campo sin conexión (modo offline): el formulario debe poder completarse
  sin internet y sincronizarse/subirse cuando el dispositivo recupere conexión.
- Login de usuarios (administrador crea las cuentas; no hay auto-registro). Rol administrador
  gestiona usuarios y tipos de reporte; rol usuario completa y genera reportes.
- Diseño de datos basado en **plantillas/configuración por tipo de reporte** (no hardcodeado a
  un único Excel), para que agregar un segundo tipo de reporte (p. ej. el de Shotcrete visto en
  el mismo archivo) sea una tarea de configuración, no de reescribir la aplicación.

El detalle técnico de cómo se modela cada plantilla está resuelto en [ADR-0003](adrs/0003-modelo-de-datos-y-plantillas.md):
definición declarativa por tipo de reporte y almacenamiento genérico de valores.

## No alcance (qué explícitamente no incluye esta versión)

- No incluye el módulo de croquis/dibujo libre de la zona de trabajo (se deja como campo de
  adjunto de imagen o pendiente para una versión futura, no como editor de dibujo).
- No incluye firma digital / firma manuscrita capturada en pantalla; el bloque de firmas se
  genera como espacio en blanco para firmar en el documento descargado, igual que hoy.
- No incluye edición del reporte una vez generado y descargado (para corregir habría que volver
  a completar el formulario o editar el archivo descargado fuera de la app).
- Sí existe una pantalla de historial y búsqueda de reportes pasados propios: "Mis reportes" (S-02 del DESIGN) agrupa los reportes por
  estado (en progreso, listos para generar, terminados) con buscador y filtros. Lo
  que **no** incluye esta versión son reportes de gestión ni analítica agregada sobre reportes
  pasados (comparativas, estadísticas entre reportes, exportables de gestión).
- No incluye soporte multi-tenant / multi-empresa con branding distinto por cliente.
- La creación de nuevos tipos de reporte se hace desde la interfaz web, en la pantalla de
  administración (S-14): un administrador carga el tipo, su plantilla `.xlsx` y su definición sin
  tocar código. No incluye self-service para usuarios no administradores.
- No incluye integración automática con otros sistemas (ERP, sistemas de gestión de calidad,
  firma electrónica) para traer o enviar datos.
- No incluye auto-registro de usuarios (las cuentas las crea únicamente el administrador).
- No incluye vista previa del reporte dentro de la app (decisión ADR-0007): se descarga el `.xlsx`
  y se revisa en Excel.
- No incluye correlativo/número de registro provisto por un sistema documental externo: en esta
  versión el número de registro lo gestiona la propia app.

## Criterios de éxito

- Un usuario puede completar el formulario y obtener el reporte final descargable sin necesidad
  de abrir Excel ni ajustar manualmente formato o fórmulas.
- El reporte generado reproduce de forma exacta la estructura y campos del formato de
  referencia (mismos encabezados, mismos ítems de checklist, mismos bloques de firma, mismo
  formato Excel) — verificable comparando campo a campo contra
  `REPORTE DE INSTALACION DE RESINAS (1).xlsx`. El logo es el único elemento configurable.
- El tiempo de elaboración de un reporte con la app es al menos 45% menor que el tiempo actual
  de elaboración manual en Excel (medido con el mismo reporte de referencia, mismo caso de uso).
- Los cálculos automáticos (p. ej. tiempos transcurridos) coinciden con el cálculo manual
  esperado en el 100% de los casos de prueba.
- El sistema rechaza el envío del formulario si falta un campo obligatorio o el formato de un
  dato es inválido, mostrando qué corregir, en vez de generar un reporte incompleto.
- Agregar un segundo tipo de reporte (basado en una plantilla ya definida) no requiere cambios en
  el código de la lógica de generación de reportes ya existente, solo la nueva configuración.

## Casos borde a contemplar

- El usuario completa el formulario sin conexión y cierra la app antes de subirlo: el progreso
  debe quedar guardado localmente y sincronizarse solo cuando vuelva a haber internet, sin
  perder datos ni duplicar el reporte al sincronizar.
- Falla de sincronización o reintento duplicado al crear el reporte — resuelto vía ID local
  idempotente (ver "Supuestos y riesgos abiertos"): el reporte se crea online y el número de
  registro se asigna en ese momento; el ID local solo evita que un reintento del mismo POST
  duplique el `Reporte`.
- Un checklist tiene un ítem marcado "No cumple" (falla): el sistema solo advierte al usuario,
  no bloquea la generación del reporte (queda registrado con su observación).
- Dos horas ingresadas (inicio/término) son inconsistentes (término antes que inicio, o fuera de
  un rango razonable) — el sistema debe validarlo, no calcular un tiempo negativo.
- El usuario necesita adjuntar una imagen (croquis o evidencia) más pesada de lo soportado, o en
  un formato no soportado.
- Se genera un reporte y luego se detecta un error después de descargado — no hay flujo de
  edición definido (ver "No alcance"), así que hay que decidir qué mensaje/guía darle al usuario.
- Un reporte queda completo pero nadie da el visto bueno: la app debe hacer visible ese estado
  para que no se acumulen reportes listos y no emitidos.
- El creador olvida compartir el reporte y nadie más puede acceder: debe preverse que un
  administrador pueda intervenir.

## Supuestos y riesgos abiertos

- Se asume que el "tipo de reporte" inicial del MVP es únicamente el de instalación de resinas.
  El usuario confirmó que por ahora solo se soportará este tipo, y que se agregarán más tipos de
  reporte (como el PPI Shotcrete visto en el mismo Excel) más adelante si es necesario — el
  diseño debe quedar preparado para eso, pero no es parte del alcance funcional del MVP.
- Varios usuarios pueden llenar el mismo reporte mediante **invitación explícita**: quien crea el
  reporte lo comparte con los usuarios que necesite, y esos invitados pueden **editar cualquier
  sección**, no solo la columna de su rol (decisión tomada en ADR-0006, eligiendo flexibilidad
  operativa por sobre la restricción por rol). Como contrapartida, toda edición queda registrada
  con autor, campo, valor anterior y fecha.
- El reporte **no se cierra automáticamente** al completarse los campos: la persona encargada de
  revisarlo da el visto bueno y lo marca como terminado. Ese acto habilita la generación del
  documento final.
- El `Reporte` se crea **online**: el POST a "Nuevo reporte"
  necesita conexión, y el número de registro oficial lo asigna el servidor en ese mismo momento
  (secuencia de BD sobre `numero_registro`), no "al sincronizar". No existe un estado
  `borrador local` previo a la creación del `Reporte` en el servidor.
  El `id_local` que viaja en ese POST no es para crear offline-first: es la llave de idempotencia
  que evita duplicar el `Reporte` si el dispositivo reintenta el mismo POST (doble click, reintento
  de red) — ver `reporte-idempotent-creation`.
  Donde sí aplica el modo offline es **después** de creado el `Reporte`: cada paso del formulario
  (`paso-offline.js` + IndexedDB) puede completarse sin señal y queda en cola local hasta
  sincronizar; recién ahí ese paso queda visible para los demás participantes. La pantalla de
  sincronización agregada (S-15) lista esos pasos pendientes/fallidos entre reportes, con
  reintento por fila.
- **Un paso sin sincronizar vive solo en el dispositivo donde se capturó** (el navegador de ese
  equipo, vía IndexedDB). No aparece en los otros dispositivos del mismo usuario hasta que
  sincroniza. La app debe comunicarlo de forma explícita para que el usuario no crea que perdió
  su avance.
- La meta de reducción de tiempo (45%) se toma como dada por el usuario, sin línea base medida
  formalmente. Se recomienda validarla informalmente comparando el tiempo real de un caso de uso
  antes de anunciarla como métrica de éxito hacia terceros.
- Riesgo: replicar el formato Excel de forma exacta (celdas combinadas, estilos, checklist por
  rol) desde datos de formulario es más costoso técnicamente que generar un documento simple; se
  recomienda validarlo temprano en diseño técnico con un caso real antes de comprometer fechas.
- Riesgo: el modo offline con sincronización posterior añade complejidad real (conflictos,
  reintentos, estado "pendiente de subir" visible al usuario) — vale la pena acotar bien su
  alcance en el diseño técnico para que no infle el MVP.

# Technical Design Document: Generador de Reportes de Campo

**Tipo de proyecto:** Greenfield. No existe código previo: el directorio del proyecto contenía
únicamente `PRD.md` y `DESIGN.md`, y no es un repositorio git.
**Design.md disponible:** Sí. El modelo de datos y las decisiones de colaboración se derivaron del
PRD y del DESIGN de forma conjunta.

## Resumen

Aplicación web que reemplaza el llenado manual de reportes de control de calidad en Excel por un
formulario guiado, y genera automáticamente el documento `.xlsx` final con el formato exacto que
exige el cliente. Está dirigida a personal de campo y control de calidad en proyectos de minería y
construcción, que trabaja desde celular o tablet con conectividad intermitente, y también desde PC
en oficina.

El caso de referencia es el formato `JME.SGC.18138.PC-0001-F1` (Reporte de Verificación de
Instalación de Pernos de Anclajes con Resina) de Consorcio JME / Compañía Minera Antamina. El
sistema se diseña para admitir tipos de reporte adicionales mediante configuración, sin modificar
la lógica de generación, según exige el PRD.

Restricción determinante del proyecto: lo desarrolla **una sola persona con experiencia
principalmente en Python**. Esta restricción condicionó casi todas las decisiones que siguen.

## Arquitectura de componentes

Un único proyecto Django que sirve las pantallas, gestiona datos y genera los documentos, más una
capa offline propia en el navegador (ADR-0001).

```
┌───────────────────────────────────────────────┐
│ NAVEGADOR (celular · tablet · PC)             │
│                                               │
│  Pantallas servidas por Django                │
│  Capa offline propia (JavaScript vanilla):    │
│    · service worker → cachea la app           │
│    · IndexedDB      → borrador + adjuntos     │
│    · cola de subida → reintento manual        │
└───────────────────────┬───────────────────────┘
                        │ HTTPS · JSON (contrato interno)
┌───────────────────────▼───────────────────────┐
│ DJANGO (Python) — despliegue único            │
│                                               │
│  · Autenticación y sesiones (contrib.auth)    │
│  · Admin de usuarios y tipos de reporte       │
│  · Reportes, permisos e historial de cambios  │
│  · Lector de definiciones de tipo de reporte  │
│  · Generador .xlsx (openpyxl + plantilla)     │
└───────────┬───────────────────────┬───────────┘
            │                       │
   ┌────────▼────────┐   ┌──────────▼──────────┐
   │ Base de datos   │   │ Almacén de archivos │
   │ PostgreSQL      │   │ Vercel Blob         │
   │ (Neon)          │   │ · plantillas .xlsx  │
   │                 │   │ · logos             │
   │                 │   │ · adjuntos          │
   └─────────────────┘   └─────────────────────┘

Hosting → Vercel, HTTPS automático (ADR-0009)
Observabilidad → Sentry (ADR-0008)
```

Reparto aproximado del esfuerzo: ~85% Python, ~15% JavaScript.

**Sobre el contrato de API:** al tratarse de un despliegue único, no existe una frontera pública
entre componentes. El contrato se reduce a un conjunto reducido de endpoints JSON internos
(sincronizar aporte, consultar estado, solicitar generación) y se documenta dentro de la ADR-0004,
sin ADR propia por no constituir una decisión con alternativas reales.

## Decisiones de arquitectura

| # | Decisión | Estado |
|---|---|---|
| [ADR-0001](adrs/0001-arquitectura-de-componentes.md) | Aplicación Django monolítica con capa offline mínima en JavaScript | Aceptado |
| [ADR-0002](adrs/0002-motor-de-generacion-de-excel.md) | Generar el `.xlsx` rellenando la plantilla original con openpyxl | Aceptado |
| [ADR-0003](adrs/0003-modelo-de-datos-y-plantillas.md) | Tipos de reporte definidos por configuración declarativa y valores en almacenamiento genérico | Aceptado |
| [ADR-0004](adrs/0004-estrategia-offline-y-sincronizacion.md) | Offline con IndexedDB, service worker y sincronización por sección de rol | Aceptado, con salvedades |
| [ADR-0005](adrs/0005-autenticacion-y-sesion.md) | Autenticación con sesiones de Django y sesión tolerante al modo offline | Aceptado, sin la mitad offline |
| [ADR-0006](adrs/0006-colaboracion-permisos-y-cierre-del-reporte.md) | Colaboración por invitación explícita, edición abierta con registro de cambios y cierre manual | Aceptado, sin el bloqueo de edición |
| [ADR-0007](adrs/0007-sin-vista-previa-en-la-aplicacion.md) | Sin vista previa del reporte dentro de la aplicación | Aceptado |
| [ADR-0008](adrs/0008-resiliencia-y-observabilidad.md) | Fallo limpio en generación, validación anticipada de configuración y observabilidad con Sentry | Aceptado |
| [ADR-0009](adrs/0009-despliegue-e-infraestructura.md) | Despliegue en Vercel, base de datos en Neon y almacenamiento en Vercel Blob | Aceptado |

### Validación empírica realizada durante el diseño

El PRD señalaba como riesgo abierto que replicar el formato Excel de forma exacta podía resultar
más costoso de lo previsto. **Ese riesgo se midió antes de decidir**, no se estimó: se abrió el
archivo de referencia con openpyxl y se volvió a guardar, comparando el resultado.

| Elemento de la hoja del reporte | Original | Tras round-trip |
|---|---|---|
| Área de impresión | `$B$2:$V$65` | idéntica |
| Orientación / escala / ajuste a página | vertical · 50% · fitToPage | idénticos |
| Márgenes | idénticos | idénticos |
| Celdas combinadas | 64 | 64 |
| Imagen (logo) | 1 | 1 |

Las pérdidas detectadas (una imagen `.wmf` y un dibujo de hojas ocultas, los `printerSettings.bin`
y metadatos `customXml`) quedan fuera del documento entregable. **El riesgo del PRD queda
acotado** siempre que se use la plantilla original como base, tal como fija la ADR-0002.

Además del round-trip de formato, se validó **escribir** valores y **exportar** el resultado sobre
la misma plantilla (64 rangos combinados en la hoja del reporte): escritura en celda ancla de un
rango combinado, 20/20 casos OK; escritura en celda no-ancla falla como se predecía
(`AttributeError` de `MergedCell`, confirma el riesgo); la hoja del reporte no usa fórmulas, así
que el riesgo de fórmula descartada no aplica; exportar sólo la hoja + guardar no corrompe el
archivo y el logo sobrevive. Detalle completo en la ADR-0002.

## Modelo de datos

Entidades principales. La estructura de cada tipo de reporte **no** vive en el esquema, sino en su
definición declarativa (ADR-0003).

| Entidad | Responsabilidad |
|---|---|
| `Usuario` | Cuenta creada por el administrador. Rol: administrador o usuario (ADR-0005). |
| `TipoDeReporte` | Metadatos del formato: nombre, código, versión, logo, plantilla `.xlsx` asociada y estado activo/inactivo. Su estructura interna proviene del archivo de definición. |
| `DefinicionDeTipo` | Archivo declarativo con secciones, campos, ítems, tipos de dato, roles y mapeo campo → celda. Validado al activar el tipo (ADR-0008). |
| `Reporte` | Instancia concreta, creada online. Guarda `id_local` (clave de idempotencia contra reintento de creación, `unique` en base de datos — ver `reporte-idempotent-creation`), número de registro oficial asignado en el momento de la creación mediante secuencia de base de datos (no `max()+1`), tipo, creador (`creado_por`), fecha, `estado` (`en_progreso`/`terminado`, ver "Ciclo de vida del reporte" abajo) y la **versión de la definición del tipo de reporte** vigente cuando el reporte se creó (decisión #18). Los pasos posteriores del formulario sí pueden completarse offline (ADR-0004) y sincronizan por separado. |
| `ParticipacionEnReporte` | Invitación explícita: qué usuario tiene acceso a qué reporte (ADR-0006). No lleva un campo de "responsable de cierre": marcar como terminado se decide comparando contra `Reporte.creado_por` (ver ADR-0006). |
| `ValorDeReporte` | Almacenamiento genérico: reporte, identificador de campo, valor, autor y fecha. Una fila por valor capturado. **No lleva un campo de rol**: no hay roles de usuario ni permisos por sección, cualquier usuario con acceso edita cualquier campo, como una hoja de cálculo compartida (ADR-0003). |
| `CambioDeValor` | Historial de auditoría: quién editó qué campo, valor anterior y cuándo. Contrapartida obligatoria de la edición abierta (ADR-0006). Retención: cola FIFO de los **últimos 30 cambios por reporte completo** (no por campo individual); al registrarse el cambio 31 de un reporte, se elimina el más antiguo de ese mismo reporte. |
| `Adjunto` | Imagen de croquis o evidencia asociada a un reporte. Se comprime automáticamente en el dispositivo antes de subir y se almacena en Vercel Blob (ADR-0004, ADR-0009). |
| `VistoBueno` | Acto de cierre manual: usuario y fecha. Habilita la generación (ADR-0006). El usuario que puede registrarlo es siempre el creador del reporte (`reporte.creado_por == usuario_actual`); no hay intervención de administrador por ahora si el creador no cierra. |
| `Generacion` | Registro de emisión del `.xlsx`: cuándo, por quién y con qué versión de la plantilla. |

Elementos de la interfaz que obligaron a entidades concretas: el chip de estado y el número de
registro de S-02 exigen `Reporte.id_local` y `numero_registro`; el historial y la lista de
participantes de S-10 exigen `CambioDeValor` y `ParticipacionEnReporte`; el logo reemplazable de
S-14 exige que la imagen sea un dato de `TipoDeReporte` y no parte del código.

### Ciclo de vida del reporte

`Reporte.estado` solo persiste dos valores: `en_progreso` y
`terminado` (`EstadoDeReporte`). No existe un tercer valor de esquema para "completo" ni para
"generado" — no hay campo que registre si ya se descargó el `.xlsx` (eso lo audita `Generacion`,
una entidad aparte, no un estado del reporte).

Lo que sí existen son **tres grupos derivados** que se calculan en cada consulta a "Mis reportes"
(`bucket_de_reporte`, sin persistir), por prioridad:

```
terminado (tiene VistoBueno)
  > listo_para_generar (no faltan campos obligatorios, aún sin VistoBueno)
  > en_progreso (todo lo demás)
```

"Listo para generar" y "terminado" no bloquean edición: cualquier participante puede seguir
editando un reporte en cualquiera de los tres grupos; el visto bueno (`VistoBueno`, solo el
creador) es lo único que habilita la generación del documento.

Cada paso individual del formulario sí puede completarse offline (`paso-offline.js` + IndexedDB,
ADR-0004) y sincroniza por separado del reporte ya existente en el servidor.

## Criterios de aceptación por flujo

### Captura de un reporte sin conexión

- [ ] Con el dispositivo en modo avión y una sesión previa válida, la aplicación abre y permite
      completar el formulario completo.
- [ ] Cada cambio de campo persiste en IndexedDB: cerrar y reabrir el navegador conserva todos los
      valores ya cargados, incluidos los adjuntos.
- [ ] Navegar hacia atrás entre pasos del wizard no pierde ningún dato.
- [ ] Mientras el reporte no se sincroniza se muestra `solo en este dispositivo` y no se muestra
      número de registro.

### Sincronización

- [ ] Al recuperar conexión, el reporte pendiente aparece en la cola con acción de reintento
      manual.
- [ ] El servidor asigna el número de registro oficial en el momento de recibir el reporte, en
      orden de llegada.
- [ ] Dos dispositivos que sincronizan reportes creados sin conexión reciben números distintos y
      correlativos, sin colisión.
- [ ] Enviar dos veces el mismo reporte (mismo ID local) no crea un segundo reporte en el
      servidor.
- [ ] Si la sesión expiró durante el período sin conexión, se solicita iniciar sesión de nuevo y
      el borrador local **no** se descarta.

### Colaboración y cierre

- [ ] El creador puede invitar a otro usuario y ese usuario ve el reporte en su listado.
- [ ] Un usuario **no** invitado no puede acceder al reporte ni por enlace directo.
- [ ] Un usuario invitado puede editar cualquier sección, y cada edición queda registrada con
      autor, campo, valor anterior y fecha, consultable desde S-10.
- [ ] Un reporte con todos los campos completos pero sin visto bueno **no** permite generar el
      documento, y la interfaz indica que falta el visto bueno.
- [ ] Tras el visto bueno, la generación queda habilitada y el acto queda registrado con usuario y
      fecha.

### Validación de datos

- [ ] Un campo obligatorio vacío aparece listado en S-09 con enlace al campo y bloquea la
      generación.
- [ ] Una hora de término anterior a la de inicio marca la celda como inválida y el botón
      "Siguiente" queda deshabilitado hasta corregir.
- [ ] Un ítem marcado "No cumple" muestra advertencia, exige observación y **no** bloquea.
- [ ] Un adjunto sin formato soportado bloquea el adjunto, nunca el reporte; no hay un límite de
      tamaño explícito porque la compresión automática en el dispositivo ya lo acota (ADR-0004).
- [ ] El Δ (tiempo transcurrido) se ingresa **manualmente** por el usuario, como un campo más del
      formulario: no se calcula automáticamente ni en el cliente ni en el servidor por ahora. Esto
      puede revisarse más adelante si se decide automatizarlo.

### Generación del documento

- [ ] El `.xlsx` generado coincide campo a campo con el formato de referencia: se verifica contra
      `REPORTE DE INSTALACION DE RESINAS (1).xlsx` celda por celda.
- [ ] El documento conserva área de impresión `$B$2:$V$65`, orientación vertical, escala 50%,
      ajuste a página, márgenes, 64 celdas combinadas y el logo.
- [ ] Reemplazar el logo en el tipo de reporte (subido por el administrador desde S-14, con
      *fallback* al logo ya cargado si no sube uno nuevo) cambia el logo del documento generado.
      Esto se resuelve con código (reemplazo de `ws._images` en la plantilla vía openpyxl, ADR-0002),
      no es un simple cambio de archivo sin lógica asociada.
- [ ] Si la plantilla falta o el mapeo es inválido, **no** se entrega archivo: se muestra un error
      accionable, el reporte queda intacto y el fallo llega a Sentry.

### Extensibilidad a un nuevo tipo de reporte

- [ ] Incorporar el reporte PPI Shotcrete consiste en subir su plantilla `.xlsx` y escribir su
      archivo de definición, sin modificar la lógica de renderizado ni la de generación.
- [ ] Una definición con un tipo de campo desconocido, una celda mal formada o celdas en colisión
      es rechazada **al activar el tipo de reporte**, con un mensaje que identifica el problema.
- [ ] El wizard y el listado de secciones de S-14 se construyen **en el servidor**, leyendo la
      definición y renderizando el HTML completo del formulario (ADR-0001) — sin código específico
      por tipo de reporte y sin que el navegador reciba la definición YAML/JSON para interpretarla
      por su cuenta.

## Riesgos técnicos abiertos

- **La capa offline es la parte más difícil y la más alejada de la experiencia del desarrollador.**
  Es el riesgo principal de cronograma. Conviene construirla temprano sobre un solo paso del
  wizard, antes de tener el formulario completo, para descubrir los problemas cuando el costo de
  cambiar de enfoque todavía es bajo.

- **La trazabilidad del documento ya no está garantizada por el sistema.** Con la edición abierta
  (ADR-0006), el `.xlsx` no distingue quién completó cada columna, pese a que el formato tiene
  columnas y firmas separadas por rol. La información sólo vive en el historial de la aplicación.
  Debería confirmarse con el área de calidad del cliente que esto es aceptable para el documento
  que van a auditar.

- **Sin vista previa (ADR-0007), un error de mapeo llega hasta el archivo descargado.** La
  verificación campo a campo al activar cada tipo de reporte es el único control existente; si se
  omite, el fallo lo descubre el cliente.

- **El almacenamiento del navegador no es permanente.** Un reporte que vive sólo como borrador
  local puede perderse si el sistema operativo purga los datos del sitio o el usuario los borra.
  Falta definir cuánto insistir en la interfaz para que el usuario sincronice.

- **Peso de los adjuntos sobre la sincronización.** El envío único por aporte (ADR-0004) crece con
  las imágenes. Se decidió comprimirlas automáticamente en el dispositivo antes de encolarlas, sin
  límite de tamaño explícito (la compresión lo acota indirectamente — ADR-0004); falta definir el
  nivel de compresión concreto en la implementación.

- **La meta de reducción de tiempo del 45% no tiene línea base medida.** Se tomó como dada; sin
  medir el proceso manual actual no es verificable.

- **Ajustes de DESIGN pendientes** heredados de estas decisiones: mecanismo de aviso al invitar a
  otro usuario (notificación, correo o sólo en la lista), copy exacto del chip `solo en este
  dispositivo`, prellenado de campos repetidos y layout de escritorio del wizard.

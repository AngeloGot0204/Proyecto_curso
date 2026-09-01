---
title: "Design — Generador de Reportes de Campo"
version: "wireframes v1"
fuente: "uploads/PRD.md · Wireframes Reportes de Campo.dc.html"
---

# DESIGN — Generador de Reportes de Campo

Documento de diseño de interfaz aprobado sobre los wireframes de la vuelta 1
(`Wireframes Reportes de Campo.dc.html`). Cubre inventario de pantallas, navegación,
componentes, estados y reglas de validación. No cubre diseño técnico (modelo de datos,
API, motor de generación de Excel).

## 1. Principios de diseño

1. **Mobile-first, mano enguantada.** La captura ocurre en campo, en celular/tablet.
   Objetivos táctiles ≥ 44 px, una columna por defecto, dos columnas solo para pares
   naturales (hora inicio / hora término).
2. **Formulario guiado, no réplica del Excel.** El usuario ve secciones cortas y pasos;
   la fidelidad al formato vive en el documento generado, no en la pantalla.
3. **El estado nunca es implícito.** Conexión, guardado local, avance por rol y número de
   registro se muestran siempre de forma explícita.
4. **Bloquear solo lo que es error.** Datos inválidos bloquean; incumplimientos del
   checklist ("No cumple") solo advierten y quedan registrados.
5. **Offline es el caso normal, no la excepción.** Todo el formulario funciona sin señal;
   la sincronización es visible y reintentable.

## 2. Roles y permisos

| Rol | Puede |
|---|---|
| Administrador | Crear/suspender usuarios, asignar rol y organización, activar tipos de reporte, subir logo por tipo/cliente |
| Usuario (campo/QA/QC) | Crear reporte, **compartirlo con otros usuarios**, editar **cualquier sección** de un reporte propio o compartido con él, dar el visto bueno y descargar el Excel |

No existe auto-registro. La contraseña inicial la entrega el administrador.

## 3. Inventario de pantallas

| ID | Pantalla | Plataforma | Referencia wireframe |
|---|---|---|---|
| S-01 | Login | móvil + escritorio | 1a |
| S-02 | Inicio · mis reportes + cola de subida | móvil | 1b |
| S-03 | Nuevo reporte · selección de tipo/plantilla | móvil | 1c |
| S-04 | Paso 1 · Datos generales (~18 campos) | móvil | 1d |
| S-05 | Paso 2 · Parámetros preliminares (7 ítems, Sí/No por rol) | móvil | 1e |
| S-06 | Paso 3 · Proceso de instalación (11 ítems, horas + Δ manual) | móvil | 1f |
| S-07 | Paso 4 · Ensayo de Pull Test (4 ítems) | móvil | 1g |
| S-08 | Paso 5 · Resultados, observaciones y adjuntos | móvil | 1h |
| S-09 | Validación al cerrar (errores vs. advertencias) | móvil, hoja modal | 1i |
| S-10 | Estado del reporte · handoff entre roles | móvil | 1j |
| S-13 | Admin · usuarios | escritorio | 1m |
| S-14 | Admin · tipo de reporte + logo | escritorio | 1n |
| S-15 | Sincronización · cola, fallos y reintentos | móvil | 1o |

## 4. Navegación

```
S-01 Login
  └─ S-02 Inicio ──┬─ S-03 Nuevo reporte → S-04 → S-05 → S-06 → S-07 → S-08
                   │        └─ (al cerrar) S-09 validación
                   │                └─ ok → visto bueno → descarga .xlsx
                   │                └─ falta otro rol → S-10 estado
                   ├─ S-10 (reporte "pendiente de otra parte")
                   ├─ S-15 (banner "pendientes de subir")
                   └─ [admin] S-13 usuarios · S-14 tipos de reporte
```

- El wizard S-04→S-08 permite navegación libre entre pasos ya visitados; el indicador
  `1/5 … 5/5` es también un salto directo.
- "Atrás" nunca pierde datos: cada cambio de campo persiste en el borrador local.
- El escritorio (S-13/S-14) usa el mismo modelo de datos; el formulario en escritorio
  reusa el layout de dos columnas sin cambiar el orden de secciones.

## 5. Detalle por pantalla

### S-01 Login
Logo institucional configurable, usuario/correo, contraseña, botón primario, nota
"solicita tu cuenta al administrador". Con sesión previa y sin señal permite entrar en
modo offline con los datos cacheados.

### S-00 Inicio
**(Agregada 2026-09-01, faltaba del inventario)** Landing post-login (`usuarios/views.py::inicio`,
spec `listado-reportes` — "Replaces Placeholder Landing View"). Pantalla real de bienvenida/resumen,
no un redirect ciego a "Mis reportes": muestra un conteo por grupo (**En progreso**, **Listos
para generar**, **Terminados**) sobre los reportes accesibles del usuario, calculado con el mismo
pipeline que S-02 usa (`agrupar_por_bucket`) para que nunca desincronice con esa lista.

### S-02 Mis reportes
Orden: (1) banner de pendientes de subir si hay cola, (2) buscador + filtros,
(3) grupos **En progreso**, **Listos para generar**, **Terminados**.
Cada tarjeta: título (tipo — nivel/frente), etiqueta de estado, línea mono con
N° de registro o `local`, % de avance y fecha. Acción primaria fija: **+ Nuevo reporte**.

### S-03 Nuevo reporte
Lista de tipos activos con código de formato y número de secciones. Los tipos no activados
se muestran deshabilitados con etiqueta "próximamente" para comunicar la extensibilidad.

### S-04 Datos generales
~18 campos de identificación. Los 9 menos frecuentes van en un bloque colapsable
"Más datos". Campos que se repiten entre reportes se prellenan con el último valor del
usuario (proyecto, compañía, contrato). Indicador "guardado local ✓" en el encabezado.

### S-05 Parámetros preliminares
Tabla de 7 ítems × columnas por rol (Consorcio JME / QA Subterra) + observación.
Todas las columnas son editables por cualquier participante invitado (ver ADR-0006); cada
celda muestra quién la completó y cuándo. Sí/No como par de casillas; observación como campo
expandible por fila. Un "No cumple" muestra una tarjeta ámbar informativa, nunca bloquea.

### S-06 Proceso de instalación
11 ítems con hora inicio / hora término y **Δ ingresado manualmente** por el usuario, como un
campo más de la fila (decisión #12 de RESOLUCION-ADVERSARIAL.md: por ahora no se calcula
automático en cliente ni servidor; se revisa más adelante si conviene automatizarlo). Entrada de
hora con selector nativo + botón "ahora". Si término < inicio: la celda se marca como inválida y
el botón "Siguiente" queda deshabilitado hasta corregir.

### S-07 Pull Test
4 datos: fuerza de tracción aplicada (con rango esperado visible), hora inicio/término,
tiempo transcurrido calculado, desplazamiento del perno, observación.

### S-08 Resultados
3 verificaciones finales por rol (QC JME / QA Antamina), observaciones generales y
adjunto de croquis/evidencia como imagen (sin editor de dibujo en el MVP; límite y
formatos soportados visibles antes de adjuntar). Nota fija: las firmas se generan en
blanco en el Excel.

### S-09 Validación al cerrar
**(Corrección 2026-09-01: es pantalla completa, no modal — ver DESIGN2 L90-93.)** Dos listas
separadas:
- **Debes corregir** — cada ítem enlaza al campo exacto; el botón "Generar" queda deshabilitado.
- **Advertencias** — ítems "No cumple" y datos atípicos; no bloquean.

Es también, hoy, la pantalla dueña del cierre: incluye el botón **"Marcar como terminado"**
(visto bueno), reservado al creador del reporte (`reporte.creado_por`), deshabilitado mientras
"Debes corregir" tenga ítems. La generación del `.xlsx` se habilita recién después del visto
bueno, no por completitud automática.

### S-10 Estado del reporte · participantes
**(Corrección 2026-09-01: el cierre NO vive acá — vive en S-09. Este change,
`cierre-en-participantes`, se propuso para moverlo aquí pero quedó abandonado/revertido; ver su
`proposal.md`.)** Lista de **participantes invitados** (usuario · secciones que completó ·
última edición), acción **"Compartir con…"** para invitar a otro usuario, avance por sección y
acceso al **historial de cambios** (quién editó qué y cuándo).

> **S-11 y S-12 eliminadas.** No hay vista previa del documento dentro de la app (ADR-0007).
> La revisión ocurre en S-09 (validación) y volviendo por los pasos del wizard. Tras el visto
> bueno se descarga el `.xlsx` directamente. Se mantiene el aviso: una vez descargado, no se
> edita desde la app.

### S-13 Admin · usuarios
Buscador, "+ Crear usuario", tabla (nombre, usuario, rol/organización, estado, menú de
acciones: editar, resetear contraseña, suspender).

### S-14 Admin · tipo de reporte
Nombre, código de formato, versión, **logo del cliente** (reemplazable) y tabla de solo
lectura de secciones (nombre · ítems · roles). Activar/desactivar el tipo. La definición de
la plantilla es configuración, no self-service en el MVP.

### S-15 Sincronización
Lista de reportes pendientes con estado (`local`, `falló 2v`), reintento manual, última
sincronización y nota de que el N° de registro oficial se asigna al sincronizar, en orden
de llegada, sin duplicar por reintento.

## 6. Sistema de componentes

| Componente | Uso |
|---|---|
| Barra de pantalla | Volver, título, indicador de paso, chip de conexión, avatar |
| Indicador de pasos | 5 puntos con estado (activo / completado / pendiente) + "guardado local ✓" |
| Campo de texto / número / hora / fecha | Etiqueta arriba, ayuda mono debajo, estado de error inline |
| Tabla de checklist por rol | Columna de ítem + una columna por rol + observación; todas las columnas editables por cualquier participante invitado (ver ADR-0006) |
| Casilla Sí/No | Par de casillas con etiqueta; estado marcado en negro sólido |
| Chip de estado | `solo en este dispositivo`, `completo`, `pend. otra parte`, `mi turno`, `offline`, `falló 2v`, `inválido` |
| Tarjeta de aviso | Neutra (informativa) o ámbar (advertencia / no cumple) |
| Barra de acciones | Secundario a la izquierda, primario a la derecha; deshabilitado con razón visible |

## 7. Estados del reporte

`borrador local` → `en progreso (sincronizado)` → `completo` → `terminado (visto bueno)` → `generado`

Reglas de UI:
- Sin sincronizar no hay N° de registro: se muestra `solo en este dispositivo`.
  El borrador vive en el navegador de **ese** equipo (ver ADR-0004 y ADR-0005): un reporte no
  sincronizado no aparece en los otros dispositivos del mismo usuario. Sincronizado, sí.
- `completo` significa que no faltan campos, pero **no** habilita la generación por sí solo.
- `terminado (visto bueno)` es un acto manual del responsable y es lo que habilita la generación.
- Un reporte `completo` sin visto bueno debe destacarse en S-02 para que no quede olvidado.
- `generado` es terminal en el MVP: no hay flujo de edición; se ofrece "volver a completar" o
  editar el archivo descargado fuera de la app.

## 8. Validación

| Regla | Efecto |
|---|---|
| Campo obligatorio vacío | Bloquea generación · listado en S-09 con enlace al campo |
| Formato de hora/fecha inválido | Bloquea · error inline |
| Hora término ≤ hora inicio | Bloquea (el Δ es un campo manual, no se deriva de estas horas) |
| Valor numérico fuera de rango esperado | Bloquea si es imposible, advierte si es solo atípico |
| Ítem de checklist "No cumple" | Advierte · exige observación · no bloquea |
| Adjunto muy pesado o formato no soportado | Bloquea el adjunto (no el reporte) con límite y formatos visibles |

## 9. Copy y tono

Español neutro, imperativo corto, vocabulario del formato original ("frente", "turno",
"tipo de roca", "pull test"). Etiquetas idénticas a las del Excel de referencia para que el
usuario reconozca el campo. Sin emoji. Mensajes de error: qué pasó + qué hacer.

## 10. Pendientes de decisión

- Mecanismo exacto de aviso al rol siguiente (notificación push, correo o solo en la lista).
- Prellenado de campos repetidos: por usuario, por frente o por turno.
- Copy exacto del chip `solo en este dispositivo` en S-02/S-15 y dónde explicar al usuario
  que un borrador sin sincronizar no viaja entre PC y celular.
- Layout de escritorio para el wizard S-04→S-08 (aún solo definido en móvil).

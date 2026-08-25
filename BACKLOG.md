# Backlog: Generador de Reportes de Campo

| # | Item | Alcance | Depende de | Contexto extra requerido |
|---|---|---|---|---|
| 1 | Modelo base y autenticación | `Usuario` con rol admin/usuario, login por sesión Django, admin crea cuentas (ADR-0005) | — | — |
| 2 | Despliegue e infraestructura | Vercel + Neon (Postgres) + Vercel Blob, HTTPS automático (ADR-0009) | #1 | — |
| 3 | Motor de definición de tipo de reporte | `TipoDeReporte` + `DefinicionDeTipo`: carga declarativa, validación al activar (secciones/campos/mapeo celda), rechazo de definición inválida (ADR-0003, ADR-0008) | #1 | — |
| 4 | Generador de Excel desde plantilla | Servicio que escribe `ValorDeReporte` sobre plantilla `.xlsx` original vía openpyxl, preserva formato/celdas combinadas/logo (ADR-0002) | #3 | — |
| 5 | Wizard de captura server-rendered | Formulario multi-paso generado en servidor leyendo `DefinicionDeTipo`, sin código por tipo de reporte, sin offline todavía (ADR-0001) | #3 | — |
| 6 | Validación de datos del formulario | Campos obligatorios, formato hora/fecha, hora término > inicio, advertencia "No cumple" sin bloqueo, pantalla S-09 con enlaces a campo | #5 | — |
| 7 | Cierre manual (visto bueno) y generación del documento | `VistoBueno` (solo el creador cierra), `Generacion`, endpoint que dispara el generador (#4), fallo limpio si plantilla/mapeo inválido (ADR-0006, ADR-0008) | #4, #6 | — |
| 8 | Colaboración por invitación y edición abierta | `ParticipacionEnReporte`, invitar usuario, acceso restringido a invitados, `CambioDeValor` con auditoría FIFO 30 (ADR-0006) | #7 | — |
| 9 | Capa offline (IndexedDB + service worker) | Persistencia local de borrador, funciona en modo avión, navegación entre pasos sin pérdida de datos (ADR-0004) | #8 | — |
| 10 | Sincronización y asignación de número de registro | Cola de subida, ID local idempotente, secuencia de BD para número de registro, reintento manual, sesión expirada no descarta borrador (ADR-0004, ADR-0005) | #9 | — |
| 11 | Adjuntos (croquis/evidencia) | `Adjunto`, compresión en dispositivo antes de subir, bloqueo solo del adjunto si formato no soportado, almacenamiento en Vercel Blob | #9 | — |
| 12 | "Mis reportes" (S-02) | Listado agrupado por estado, buscador y filtros | #10 | — |
| 13 | Administración de tipos de reporte (S-14) | CRUD de `TipoDeReporte`, subida de logo con fallback, subida de plantilla y definición | #3 | Reglas de negocio del formato de reporte específico (si se agrega un tipo nuevo con checklist propio, ej. PPI Shotcrete) |
| 14 | Observabilidad (Sentry) | Captura de errores de generación y sincronización (ADR-0008) | #7 | — |

## Cómo usar este backlog

Cada ítem es una spec independiente. Al implementarlo, arrancá un ciclo de Spec-Driven
Development (`sdd-new` o el flujo equivalente de tu harness) usando este ítem como el
"change" — no el proyecto completo. Si la columna "Contexto extra requerido" tiene algo,
compartilo como contexto al generar la spec de ese ítem.

## Nota de secuencia

El orden prioriza tener una app end-to-end funcionando (formulario → validación → visto
bueno → Excel descargable) lo antes posible, en los ítems #1 a #7, antes de abordar la
parte técnicamente más difícil del proyecto (offline, ítems #9-#10). El TDD señala la capa
offline como el riesgo #1 de cronograma y sugiere construirla temprano; se pospuso aquí
deliberadamente porque quien implementa tiene poca experiencia en programación — depurar
service worker / IndexedDB / sincronización sin haber visto antes ningún ciclo SDD completo
aumenta el riesgo de bloquearse sin nada funcionando para mostrar. Con #1-#7 ya construidos,
hay una base probada sobre la cual aislar el riesgo offline.

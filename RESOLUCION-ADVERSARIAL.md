---
title: "Resolución de hallazgos — Revisión adversarial"
fecha: "2026-08-25"
origen: "REVISION-ADVERSARIAL.md"
metodo: "Decisiones tomadas en conversación con el autor del proyecto, campo por campo"
---

# Resolución de hallazgos

Este documento registra qué se decidió para cada hallazgo de `REVISION-ADVERSARIAL.md`.
Falta trasladar estas decisiones a `TECH-DESIGN.md` y las ADR correspondientes.

## Críticos

| # | Hallazgo | Decisión |
|---|---|---|
| 1 | Wizard cliente/servidor duplicado | El servidor arma el formulario ya renderizado en HTML (no una definición que el celular interprete). Se cachea esa página para uso offline. La validación fuerte ocurre al sincronizar, no offline; el celular solo avisa errores después de reconectar. |
| 2 | `ValorDeReporte` sin `rol` | No aplica. No hay roles de usuario ni permisos por sección — cualquier usuario con acceso edita cualquier campo, como un Excel compartido. Un valor por celda, se pisa al último que edita. Modelo actual se mantiene sin cambios. |
| 3 | Conflictos de edición concurrente | Un invitado NO puede editar offline un reporte ajeno (colaboración es online-only). Para el caso online-simultáneo: bloqueo de edición — al abrir el reporte queda marcado "en edición por X"; otros ven solo lectura hasta que libere manual (botón "dejar de editar") o por inactividad (10 min). |
| 4 | Logo contradictorio entre ADR-0002 y TECH-DESIGN | Se mantiene el logo dinámico (admin lo sube desde pantalla, con fallback al ya cargado si existe). Se corrige el texto de ADR-0002, que decía "sin tocar código" — sí requiere código (reemplazar imagen vía openpyxl). |
| 5 | Validación empírica insuficiente | Corrida sobre la plantilla real (`REPORTE DE INSTALACION DE RESINAS`, hoja `JME.PC-0001.F1`, 64 rangos combinados). Escritura en anclas: 20/20 OK. Escritura en no-ancla: falla como se predijo (`MergedCell` read-only) — se agrega a ADR-0008 la validación obligatoria "toda celda destino debe ser ancla de su rango combinado". Fórmulas: la hoja del reporte no tiene, no aplica riesgo de fórmula descartada. Exportar solo la hoja + guardar: funciona, logo (PNG) sobrevive. Premisa de ADR-0002 confirmada. |

## Advertencias

| # | Hallazgo | Decisión |
|---|---|---|
| 6 | Dexie/Workbox no evaluadas | Se suman ambas al proyecto (offline con Dexie.js sobre IndexedDB, service worker con Workbox). No violan restricción de "sin frameworks" de ADR-0001. |
| 7 | JSONField no evaluado | No se cambia. Se mantiene el modelo actual (una fila por campo) porque necesita autoría/fecha por campo, que JSONField no da gratis. |
| 8 | Sin ADR de despliegue/infraestructura/respaldo | Vercel (hosting + HTTPS automático) + Neon (PostgreSQL + respaldo automático) + Vercel Blob (logos y Excel generados). Proyecto es académico, sin fines comerciales — plan gratis (Hobby) de Vercel aplica sin restricción. |
| 9 | Correlativo oficial sin garantía de colisión | Usar secuencia de base de datos (no `max()+1` a mano) + restricción `unique` en `Reporte.id_local`. Detalle técnico de implementación, sin decisión pendiente del usuario. |
| 10 | Expiración de sesión offline contradictoria | Sesión dura 7 días, sin PIN local. Prioriza no bloquear al usuario en campo sobre seguridad extra (riesgo de robo de dispositivo considerado bajo para este uso). |
| 11 | Visto bueno sin responsable definido | Solo el creador del reporte (`reporte.creado_por == usuario_actual`) puede marcar como terminado. Sin intervención de admin por ahora si el creador no cierra. |
| 12 | Δ calculado en dos lenguajes | Por ahora, el Δ (tiempo transcurrido) se ingresa manual, como un campo más — no se calcula automático. Hora inicio y hora término siguen siendo manuales (ya lo eran). Se revisa con el cliente (papá) si más adelante debe automatizarse. |
| 13 | Adjuntos sin transporte/límite/almacén | Compresión automática de imágenes en el celular antes de subir (sin acción del usuario). Sin límite de tamaño explícito — la compresión ya lo acota indirectamente. Almacén: Vercel Blob (decidido en #8). |
| 14 | Contradicciones con el PRD | Se corrige el PRD en ambos puntos: sí existe pantalla de historial/búsqueda de reportes ("Mis reportes" con estado: borrador/en proceso/terminado, con buscador y filtros — S-02 queda como está); y el ciclo de vida del reporte arranca en borrador local, no en el servidor (el supuesto viejo del PRD queda obsoleto). |
| 15 | Falta prueba automática del generador de Excel | Se suma: prueba de "archivo dorado". Reporte de datos fijos, se genera, se compara automático contra un `.xlsx` esperado guardado en el repositorio. Reemplaza la revisión manual celda por celda como red de seguridad. |

## Sugerencias

| # | Hallazgo | Decisión |
|---|---|---|
| 16 | Residuo de vista previa en DESIGN.md §6 | Se borra la línea que menciona el placeholder de vista previa (ADR-0007 ya la eliminó). Limpieza de texto, sin impacto funcional. |
| 17 | `CambioDeValor` sin límite de crecimiento | Cola FIFO: se guardan los últimos 30 cambios **por reporte completo** (no por campo). Al entrar el cambio 31, se borra el más antiguo. |
| 18 | Borrador local sin versión de plantilla | El borrador local guarda la versión de la plantilla/definición que usaba al crearse. Si la plantilla cambió antes de sincronizar, se avisa al usuario en vez de guardar datos mal ubicados en silencio. |

## Pendiente

- Trasladar estas decisiones a `TECH-DESIGN.md` (modelo de datos, criterios de aceptación) y a las ADR
  afectadas: 0001, 0002, 0003, 0004, 0006, 0008. Ninguna ADR fue reescrita todavía — este documento
  solo registra la decisión tomada, no reemplaza la actualización formal.
- Correr la prueba de archivo dorado una vez armado el primer generador real (hallazgo 15).

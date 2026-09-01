# ADR 0008: Fallo limpio en generación, validación anticipada de configuración y observabilidad con Sentry

## Estado

Aceptado

## Contexto

El PRD registra como riesgo que el modo offline "añade complejidad real (conflictos, reintentos,
estado pendiente de subir visible al usuario)" y el DESIGN establece como principio "bloquear solo
lo que es error". Los fallos y reintentos de **sincronización** ya quedaron resueltos en la
ADR-0004 mediante cola, reintento manual e idempotencia por ID local.

**Corrección (decisión #3 de RESOLUCION-ADVERSARIAL.md):** los "conflictos" que menciona el PRD no
quedaron resueltos únicamente por eso — la idempotencia de la ADR-0004 evita duplicar un reporte
por un reintento, pero no dice nada sobre dos personas editando el **mismo** reporte a la vez. Ese
caso se resuelve con el bloqueo de edición "en edición por `<usuario>`" descrito en la ADR-0006
(liberación manual o por 10 minutos de inactividad), no en la ADR-0004. **(Nota 2026-09-01: ese
bloqueo nunca se implementó — ver la corrección en ADR-0006. Este caso de dos ediciones
simultáneas sigue sin resolverse en el código, solo queda `CambioDeValor` como registro.)**

Restan tres modos de fallo sin cubrir:

1. **Fallo al generar el `.xlsx`** — plantilla ausente o movida, mapeo campo → celda inválido,
   plantilla corrupta. Es un riesgo directo de la ADR-0002, que ata la generación a un archivo
   físico y a coordenadas de celda.
2. **Configuración de tipo de reporte inválida** — riesgo asumido en la ADR-0003, donde un error
   en la definición declarativa no lo detecta el compilador y se manifiesta en ejecución.
3. **Ausencia de visibilidad de los errores en producción** — el proyecto lo mantiene una sola
   persona, que no está mirando los registros del servidor.

Este último punto se agrava tras la ADR-0007: al eliminarse la vista previa, el usuario no dispone
de ningún control dentro de la aplicación antes de descargar el documento.

## Decisión

**Fallo limpio en la generación.** Si la generación del `.xlsx` falla, no se entrega un archivo
parcial ni corrupto: la operación se aborta, el reporte permanece intacto y reintentable, y se
muestra al usuario un mensaje que indica qué ocurrió y qué hacer (avisar al administrador).

**Validación anticipada de la configuración.** La definición de un tipo de reporte se valida al
activarla, no al usarla: campos obligatorios presentes, tipos conocidos, referencias de celda con
formato válido y sin colisiones, y existencia de la plantilla. Así el error lo detecta el
administrador al publicar el tipo de reporte, y no el usuario en el frente de trabajo sin señal.

**Regla obligatoria adicional (decisión #5 de RESOLUCION-ADVERSARIAL.md):** toda celda destino del
mapeo campo → celda debe ser la **celda ancla** (la esquina superior-izquierda) de su rango
combinado, si pertenece a uno. La validación empírica de la ADR-0002 confirmó que escribir en una
celda no-ancla de un rango combinado falla con `AttributeError: 'MergedCell' object attribute
'value' is read-only`; esta regla evita que ese error llegue a producción y lo detecta al activar
el tipo de reporte, no al generar un reporte real en campo.

**Observabilidad con Sentry.** Integrar `sentry-sdk` en Django para capturar excepciones en
producción, con traza, usuario afectado, vista implicada y agrupación de errores repetidos.

## Alternativas consideradas

- **Notificación de errores por correo mediante `ADMINS` y `mail_admins` de Django** — fue la
  opción recomendada inicialmente por no requerir servicios externos, y se descartó tras
  reconsiderarla: no sólo es peor sino también **más costosa de poner en marcha**. Exige
  credenciales SMTP (proveedor, contraseña de aplicación, puerto, TLS), los mensajes tienden a
  clasificarse como spam, y genera un correo por cada ocurrencia, de modo que un error repetido
  inunda el buzón. Aporta menos información que Sentry a cambio de más configuración.

- **Únicamente registros (logs) en el servidor** — la opción de menor esfuerzo inmediato. Se
  descartó porque exige que el desarrollador revise los registros por iniciativa propia: en la
  práctica, los errores se descubren cuando un usuario los reporta, no cuando ocurren.

- **Reintento automático de la generación del `.xlsx` ante un fallo** — se descartó porque los
  fallos previstos (plantilla ausente, mapeo inválido) son deterministas: reintentar produce el
  mismo error y sólo retrasa el diagnóstico.

## Consecuencias

- Nunca se entrega al usuario un documento parcial o corrupto que pudiera confundirse con un
  reporte válido.
- Los errores de configuración se detectan en el momento de publicar el tipo de reporte, momento
  en el que hay un administrador con contexto para corregirlos, y no en campo.
- El desarrollador se entera de los fallos en producción sin depender de que un usuario los
  reporte, y con información suficiente para diagnosticarlos (traza, usuario, vista).
- La integración de Sentry son unas pocas líneas en `settings.py` y una dependencia; su plan
  gratuito cubre holgadamente el volumen de este proyecto.
- **Costo real:** se incorpora una dependencia de un servicio externo. Los datos de las
  excepciones salen de la infraestructura propia, algo a considerar si el cliente impone
  restricciones sobre información del proyecto. `send_default_pii` debe evaluarse antes de
  activarse.
- **Costo real:** la validación anticipada de la configuración es desarrollo adicional que no
  existiría si se confiara en que los archivos están bien escritos, y debe mantenerse actualizada
  cada vez que la definición admita un tipo de campo nuevo.
- **Costo real:** el fallo limpio deja al usuario sin documento hasta que un administrador
  interviene. Es preferible a entregar un archivo incorrecto, pero implica que exista alguien
  disponible para atenderlo.
- **Nota operativa:** el envío de correo seguirá siendo necesario más adelante para el reseteo de
  contraseña de Django (ADR-0005), pero es una necesidad independiente de la observabilidad y no
  bloquea el arranque del proyecto.
